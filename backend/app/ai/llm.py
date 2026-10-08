from __future__ import annotations

import json
import logging
import re
import time
from html import escape
from dataclasses import dataclass
from typing import Any

import httpx
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.ai.budget import BudgetExceeded, RequestBudget
from app.ai.prompts import REPAIR_PROMPT, VERIFY_PROMPT
from app.core.config import get_settings
from app.core.errors import APIError
from app.core.rate_limit import enforce_global_llm_call_budget
from app.db.models import LlmCallLog

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str
    tool_calls: list[dict[str, Any]]
    tokens_in: int = 0
    tokens_out: int = 0
    providers_attempted: list[str] | None = None


@dataclass
class VerificationResult:
    verified: bool
    decision: dict[str, Any] | None = None


class LLMUnavailable(RuntimeError):
    pass


class InvalidLLMOutput(RuntimeError):
    pass


class ProviderCallTimeout(TimeoutError):
    pass


def deterministic_json_repair(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def parse_json(raw: str) -> Any:
    return json.loads(deterministic_json_repair(raw))


class LLM:
    """One gateway for the two preserved text profiles and Jev decisions."""
    def __init__(self):
        self.settings = get_settings()

    def _career_chain(self) -> list[tuple[str, str, str, str]]:
        # Import the existing configuration (copied without model/order changes).
        from app.ai.brain.career_agent.config import FALLBACK_CASCADE
        chain = []
        for tier in FALLBACK_CASCADE:
            if tier.provider == "gemini":
                chain.append(("gemini", tier.model_id, self.settings.gemini_api_key, "https://generativelanguage.googleapis.com/v1beta/openai"))
            elif tier.provider == "groq":
                chain.append(("groq", tier.model_id, self.settings.groq_api_key, ""))
            elif tier.provider == "huggingface":
                chain.append(("huggingface", tier.model_id, self.settings.hf_token, "https://api-inference.huggingface.co/v1"))
            elif tier.provider == "ollama":
                chain.append(("ollama", tier.model_id, "ollama", self.settings.ollama_base_url.rstrip("/") + "/v1"))
        return chain

    def _finishai_chain(self) -> list[tuple[str, str, str, str]]:
        groq_models = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "qwen/qwen3.6-27b", "openai/gpt-oss-20b", "groq/compound-mini"]
        openai_models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        groq = [("groq", model, self.settings.groq_api_key, "") for model in groq_models]
        openai = [("openai", model, self.settings.openai_api_key, "") for model in openai_models]
        return groq + openai if self.settings.use_groq else openai

    def _chain(self, profile: str) -> list[tuple[str, str, str, str]]:
        if profile == "finishai_text":
            return self._finishai_chain()
        if profile == "career_agent_text":
            return self._career_chain()
        raise ValueError("Unknown text-generation profile")

    async def _request_one(self, provider: str, model: str, key: str, base_url: str,
                           messages: list[dict], tools: list[dict] | None, budget: RequestBudget) -> LLMResult:
        timeout = min(budget.check(), self.settings.ai_call_timeout_seconds)
        client: AsyncOpenAI
        if provider == "groq":
            from groq import AsyncGroq
            client = AsyncGroq(api_key=key, timeout=timeout)
        elif provider == "ollama":
            client = AsyncOpenAI(api_key=key, base_url=base_url, timeout=timeout)
        elif provider in ("gemini", "huggingface"):
            client = AsyncOpenAI(api_key=key, base_url=base_url, timeout=timeout)
            if provider == "gemini" and model.startswith("models/"):
                model = model.removeprefix("models/")
        else:
            client = AsyncOpenAI(api_key=key, timeout=timeout)
        kwargs: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.3, "max_tokens": 4096, "timeout": timeout}
        if tools:
            kwargs.update(tools=tools, tool_choice="auto")
        try:
            try:
                response = await budget.wait_for(client.chat.completions.create(**kwargs), timeout)
            except BudgetExceeded as exc:
                if budget.remaining() <= 0.05:
                    raise
                raise ProviderCallTimeout("Provider call timed out; switching to the next configured tier") from exc
        finally:
            await client.close()
        choice = response.choices[0].message
        tool_calls = []
        for call in (choice.tool_calls or []):
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append({"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": args}})
        usage = getattr(response, "usage", None)
        return LLMResult(choice.content or "", provider, model, tool_calls,
                         int(getattr(usage, "prompt_tokens", 0) or 0), int(getattr(usage, "completion_tokens", 0) or 0))

    async def invoke(self, profile: str, messages: list[dict], budget: RequestBudget,
                     tools: list[dict] | None = None, db: Session | None = None,
                     capability: str = "unspecified") -> LLMResult:
        last_error: Exception | None = None
        chain = self._chain(profile)
        attempted: list[str] = []
        for provider, model, key, base_url in chain:
            if not key and provider != "ollama":
                continue
            if budget.remaining() <= 0:
                raise BudgetExceeded("AI request budget exhausted")
            if db is not None:
                enforce_global_llm_call_budget(db)
            started = time.monotonic()
            try:
                attempted.append(f"{provider}/{model}")
                result = await self._request_one(provider, model, key, base_url, messages, tools, budget)
                result.providers_attempted = list(attempted)
                logger.info("ai_call profile=%s provider=%s model=%s success=true", profile, provider, result.model)
                self._record(db, capability, profile, f"{provider}/{result.model}", started, True, None,
                             result.tokens_in, result.tokens_out)
                return result
            except BudgetExceeded as exc:
                self._record(db, capability, profile, f"{provider}/{model}", started, False, "timeout", 0, 0)
                raise
            except Exception as exc:
                last_error = exc
                category = "timeout" if isinstance(exc, (TimeoutError,)) or "timeout" in type(exc).__name__.lower() else "provider_error"
                logger.warning("ai_failover profile=%s provider=%s model=%s error_type=%s", profile, provider, model, type(exc).__name__)
                self._record(db, capability, profile, f"{provider}/{model}", started, False, category, 0, 0)
                continue
        raise LLMUnavailable("All configured model tiers are unavailable") from last_error

    @staticmethod
    def _record(db: Session | None, capability: str, profile: str, provider_model: str,
                started: float, success: bool, error: str | None, tokens_in: int, tokens_out: int):
        if db is None:
            return
        db.add(LlmCallLog(capability=capability, profile=profile, provider_model=provider_model,
                          latency_ms=int((time.monotonic() - started) * 1000), success=success,
                          error_category=error, tokens_in=tokens_in, tokens_out=tokens_out))
        db.commit()

    async def generate_json(self, profile: str, messages: list[dict], schema, budget: RequestBudget,
                            db: Session | None = None, capability: str = "structured"):
        result = await self.invoke(profile, messages, budget, db=db, capability=capability)
        try:
            parsed = parse_json(result.content)
        except (json.JSONDecodeError, TypeError, ValueError) as parse_error:
            budget.check()
            repair = [{"role": "system", "content": "Return only JSON conforming to the supplied schema. Do not add facts."},
                      {"role": "user", "content": REPAIR_PROMPT.format(schema=json.dumps(schema.model_json_schema()), content=result.content[:12000])}]
            repaired = await self.invoke(profile, repair, budget, db=db, capability=f"{capability}_repair")
            try:
                parsed = parse_json(repaired.content)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise InvalidLLMOutput("The model response did not match the required schema") from parse_error
            try:
                return schema.model_validate(parsed), repaired
            except Exception as exc:
                raise InvalidLLMOutput("The model response did not match the required schema") from exc
        try:
            return schema.model_validate(parsed), result
        except Exception as exc:
            raise InvalidLLMOutput("The model response did not match the required schema") from exc

    def jev_enabled(self) -> bool:
        cfg = self.settings
        return bool(cfg.jev_provider and cfg.jev_model_id and cfg.jev_api_key and cfg.jev_base_url)

    async def decide(self, candidate: dict, rules: dict, budget: RequestBudget,
                     db: Session | None = None, capability: str = "verification") -> VerificationResult:
        if not self.jev_enabled() or budget.remaining() < 0.5:
            return VerificationResult(False)
        cfg = self.settings
        if cfg.jev_provider not in {"openai_compatible", "openai-compatible", "openai"}:
            return VerificationResult(False)
        timeout = min(budget.remaining(), cfg.ai_call_timeout_seconds)
        if timeout < 0.2:
            return VerificationResult(False)
        if db is not None:
            try:
                enforce_global_llm_call_budget(db)
            except APIError as exc:
                if exc.code == "AI_BUSY":
                    return VerificationResult(False)
                raise
        endpoint = cfg.jev_base_url
        if not endpoint.endswith("/chat/completions"):
            endpoint = endpoint.rstrip("/") + "/chat/completions"
        prompt = VERIFY_PROMPT.replace("{rules}", escape(json.dumps(rules, ensure_ascii=False), quote=False))
        prompt = prompt.replace("{candidate}", escape(json.dumps(candidate, ensure_ascii=False), quote=False))
        headers = {"Authorization": f"Bearer {cfg.jev_api_key}", "Content-Type": "application/json"}
        payload = {"model": cfg.jev_model_id, "temperature": 0, "messages": [
            {"role": "system", "content": "You are a decision classifier. Do not rewrite input."},
            {"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}
        try:
            started = time.monotonic()
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                response = await budget.wait_for(client.post(endpoint, headers=headers, json=payload), timeout)
                response.raise_for_status()
                data = response.json()["choices"][0]["message"]["content"]
                from app.ai.schemas import DecisionOutput
                decision = DecisionOutput.model_validate(parse_json(data)).model_dump()
                logger.info("ai_call profile=jev_decision provider=%s model=%s success=true", cfg.jev_provider, cfg.jev_model_id)
                self._record(db, capability, "jev_decision", f"{cfg.jev_provider}/{cfg.jev_model_id}",
                             started, True, None, 0, 0)
                return VerificationResult(True, decision)
        except Exception as exc:
            logger.warning("jev_unavailable error_type=%s", type(exc).__name__)
            if "started" in locals():
                self._record(db, capability, "jev_decision", f"{cfg.jev_provider}/{cfg.jev_model_id}",
                             started, False, "provider_error", 0, 0)
            return VerificationResult(False)


llm = LLM()
