"""
llm_cascade.py — Multi-Tier LLM Failover Engine.

4-Tier Cascade:
  Tier 1  : Gemini 2.5 Flash          (google-genai)
  Tier 2A : Llama 3.3 70B Versatile   (Groq)
  Tier 2B : Llama 3.1 8B Instant      (Groq — rate-limit backup)
  Tier 3  : NVIDIA NIM Llama 3.3 70B  (OpenAI-compatible)
  Tier 4  : Ollama Gemma 4B           (Emergency, no tool calling)

Failover triggers: HTTP 429, HTTP 503, Timeout > REQUEST_TIMEOUT seconds.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from career_agent.config import (
    FALLBACK_CASCADE,
    ModelConfig,
    REQUEST_TIMEOUT,
    SYSTEM_PROMPT,
)
from career_agent.state_adapter import NeutralHistory, to_gemini_history, to_openai_history, to_ollama_history
from career_agent.tools import TOOL_DEFINITIONS

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LAZY CLIENT SINGLETONS
# ---------------------------------------------------------------------------
_gemini_client = None
_groq_client = None
_nvidia_client = None
_huggingface_client = None
_ollama_client = None


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _gemini_client


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _groq_client


def _get_nvidia():
    global _nvidia_client
    if _nvidia_client is None:
        from openai import OpenAI
        _nvidia_client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.environ.get("NVIDIA_API_KEY", ""),
        )
    return _nvidia_client


def _get_huggingface():
    global _huggingface_client
    if _huggingface_client is None:
        from openai import OpenAI
        _huggingface_client = OpenAI(
            base_url="https://api-inference.huggingface.co/v1/",
            api_key=os.environ.get("HF_TOKEN", ""),
        )
    return _huggingface_client


def _get_ollama():
    global _ollama_client
    if _ollama_client is None:
        from openai import OpenAI
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        _ollama_client = OpenAI(base_url=f"{base}/v1", api_key="ollama")
    return _ollama_client


# ---------------------------------------------------------------------------
# PROVIDER CALL IMPLEMENTATIONS
# ---------------------------------------------------------------------------

def _call_gemini(model: ModelConfig, history: NeutralHistory, use_tools: bool) -> dict[str, Any]:
    """Call Gemini 2.5 Flash via google-genai SDK."""
    from google import genai as _genai
    from google.genai import types as genai_types

    client = _get_gemini()
    contents = to_gemini_history(history)

    # Build function declarations if tools are enabled
    gemini_tools = None
    if use_tools and model.supports_tools and TOOL_DEFINITIONS:
        fn_decls = []
        for t in TOOL_DEFINITIONS:
            fn_decls.append(
                genai_types.FunctionDeclaration(
                    name=t["function"]["name"],
                    description=t["function"]["description"],
                    parameters=t["function"]["parameters"],
                )
            )
        gemini_tools = [genai_types.Tool(function_declarations=fn_decls)]

    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=model.temperature,
        tools=gemini_tools,
    )

    response = client.models.generate_content(
        model=model.model_id,
        contents=contents,
        config=config,
    )

    content_text = ""
    tool_calls: list[dict] = []
    candidate = response.candidates[0]

    for part in candidate.content.parts:
        if hasattr(part, "text") and part.text:
            content_text += part.text
        if hasattr(part, "function_call") and part.function_call:
            fc = part.function_call
            tool_calls.append({
                "id": f"call_{fc.name}_{len(tool_calls)}",
                "type": "function",
                "function": {
                    "name": fc.name,
                    "arguments": dict(fc.args) if fc.args else {},
                },
            })

    return {"content": content_text, "tool_calls": tool_calls}


def _call_openai_compat(
    client: Any,
    model: ModelConfig,
    history: NeutralHistory,
    use_tools: bool,
) -> dict[str, Any]:
    """
    Generic caller for OpenAI-wire-compatible providers:
    Groq, NVIDIA NIM, and Ollama (when using OpenAI client).
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + to_openai_history(history)

    kwargs: dict[str, Any] = {
        "model": model.model_id,
        "messages": messages,
        "temperature": model.temperature,
        "max_tokens": model.max_tokens,
        "timeout": REQUEST_TIMEOUT,
    }

    if use_tools and model.supports_tools and TOOL_DEFINITIONS:
        kwargs["tools"] = TOOL_DEFINITIONS
        kwargs["tool_choice"] = "auto"

    response = client.chat.completions.create(**kwargs)
    msg = response.choices[0].message

    tool_calls: list[dict] = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": args},
            })

    return {"content": msg.content or "", "tool_calls": tool_calls}


def _call_ollama(model: ModelConfig, history: NeutralHistory) -> dict[str, Any]:
    """Call Ollama (Tier 4 emergency). Tool calling is disabled."""
    client = _get_ollama()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + to_ollama_history(history)

    response = client.chat.completions.create(
        model=model.model_id,
        messages=messages,
        temperature=model.temperature,
        max_tokens=model.max_tokens,
        timeout=REQUEST_TIMEOUT,
    )
    content = response.choices[0].message.content or ""
    return {"content": content, "tool_calls": []}


# ---------------------------------------------------------------------------
# FAILOVER HELPER — detect retryable errors
# ---------------------------------------------------------------------------

def _is_retryable(exc: Exception) -> bool:
    """
    Return True if the exception signals rate limiting or server overload
    (HTTP 429 or 503), meaning we should try the next tier.
    """
    # Groq-specific error types
    try:
        from groq import RateLimitError as GroqRL, APIStatusError as GroqAS
        if isinstance(exc, GroqRL):
            return True
        if isinstance(exc, GroqAS) and exc.status_code in (429, 503):
            return True
    except ImportError:
        pass

    # OpenAI-specific error types (also covers NVIDIA NIM)
    try:
        from openai import RateLimitError as OAIRL, APIStatusError as OAIAS
        if isinstance(exc, OAIRL):
            return True
        if isinstance(exc, OAIAS) and exc.status_code in (429, 503):
            return True
    except ImportError:
        pass

    # Timeout
    if isinstance(exc, httpx.TimeoutException):
        return True

    # Generic 429/503 check via exception message
    msg = str(exc).lower()
    return "429" in msg or "503" in msg or "rate limit" in msg


# ---------------------------------------------------------------------------
# MAIN CASCADE ENTRY POINT
# ---------------------------------------------------------------------------

def call_with_cascade(
    history: NeutralHistory,
    enable_tools: bool = True,
) -> dict[str, Any]:
    """
    Attempt each model tier in sequence. On rate limit (429), server overload
    (503), or timeout, log a warning and advance to the next tier.

    Args:
        history: Provider-agnostic conversation history.
        enable_tools: Whether to pass tool definitions to the model.

    Returns:
        dict with keys:
            "content"    (str)  — Model text response.
            "tool_calls" (list) — List of tool call dicts (may be empty).
            "provider"   (str)  — Display name of the model that responded.

    Raises:
        RuntimeError: If all tiers are exhausted without a successful response.
    """
    last_error: Exception | None = None

    for tier_index, model in enumerate(FALLBACK_CASCADE):
        tier_label = f"TIER {tier_index + 1} — {model.name}"

        try:
            logger.info(f"[INFO] Attempting {tier_label} ...")

            result: dict[str, Any]

            if model.provider == "gemini":
                result = _call_gemini(model, history, use_tools=enable_tools)

            elif model.provider == "groq":
                result = _call_openai_compat(
                    _get_groq(), model, history, use_tools=enable_tools
                )

            elif model.provider == "nvidia":
                result = _call_openai_compat(
                    _get_nvidia(), model, history, use_tools=enable_tools
                )

            elif model.provider == "huggingface":
                result = _call_openai_compat(
                    _get_huggingface(), model, history, use_tools=enable_tools
                )

            elif model.provider == "ollama":
                # Tool calling explicitly disabled for Tier 4
                result = _call_ollama(model, history)

            else:
                raise ValueError(f"Unknown provider: '{model.provider}'")

            result["provider"] = model.name
            logger.info(f"[OK] {tier_label} responded successfully.")
            return result

        except Exception as exc:
            last_error = exc
            if _is_retryable(exc):
                logger.warning(
                    "[WARN] %s failed error_type=%s; switching to next fallback model",
                    tier_label, type(exc).__name__
                )
                continue  # Try next tier
            else:
                # Non-retryable error — still try next tier but log as error
                logger.error(
                    "[ERROR] %s non-retryable error_type=%s; attempting next tier",
                    tier_label, type(exc).__name__
                )
                continue

    raise RuntimeError(
        f"All {len(FALLBACK_CASCADE)} model tiers exhausted. "
        f"Last error: {last_error}"
    )
