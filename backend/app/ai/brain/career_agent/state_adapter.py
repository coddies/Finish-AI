"""
state_adapter.py — Universal Provider-Agnostic Message History.

Neutral schema:
    [{"role": "user"|"assistant"|"tool", "content": "...", "tool_calls": [...]}]

Converters for every provider are implemented here.
"""
from __future__ import annotations

from typing import Any

# Type aliases
NeutralMessage = dict[str, Any]
NeutralHistory = list[NeutralMessage]


# ---------------------------------------------------------------------------
# HISTORY MUTATION HELPERS
# ---------------------------------------------------------------------------

def append_user(history: NeutralHistory, content: str) -> None:
    """Append a user message to the neutral history."""
    history.append({"role": "user", "content": content})


def append_assistant(
    history: NeutralHistory,
    content: str,
    tool_calls: list | None = None,
) -> None:
    """Append an assistant message, optionally with tool calls."""
    msg: NeutralMessage = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    history.append(msg)


def append_tool_result(
    history: NeutralHistory,
    tool_name: str,
    result: str,
    tool_call_id: str = "call_0",
) -> None:
    """Append a tool result observation to the neutral history."""
    history.append({
        "role": "tool",
        "tool_name": tool_name,
        "tool_call_id": tool_call_id,
        "content": result,
    })


# ---------------------------------------------------------------------------
# CONVERTERS — GEMINI
# ---------------------------------------------------------------------------

def to_gemini_history(history: NeutralHistory) -> list[dict]:
    """
    Convert neutral history to Gemini SDK `contents` format.

    Gemini uses:
        role: "user" | "model"
        parts: [{"text": ...}] | [{"functionCall": ...}] | [{"functionResponse": ...}]

    Tool results from role="tool" are re-wrapped as user messages with
    functionResponse parts, as required by the Gemini spec.
    """
    result: list[dict] = []

    for msg in history:
        role = msg["role"]
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])

        if role == "user":
            result.append({
                "role": "user",
                "parts": [{"text": content}],
            })

        elif role == "assistant":
            parts: list[dict] = []
            if content:
                parts.append({"text": content})
            for tc in tool_calls:
                parts.append({
                    "functionCall": {
                        "name": tc["function"]["name"],
                        "args": tc["function"].get("arguments", {}),
                    }
                })
            if parts:
                result.append({"role": "model", "parts": parts})

        elif role == "tool":
            # Gemini expects tool results as user-turn functionResponse
            result.append({
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": msg.get("tool_name", "tool"),
                        "response": {"result": content},
                    }
                }],
            })

    return result


# ---------------------------------------------------------------------------
# CONVERTERS — OPENAI / GROQ / NVIDIA (identical wire format)
# ---------------------------------------------------------------------------

def to_openai_history(history: NeutralHistory) -> list[dict]:
    """
    Convert neutral history to OpenAI-compatible messages format.
    Works for Groq and NVIDIA NIM as they share the same wire format.
    """
    result: list[dict] = []

    for msg in history:
        role = msg["role"]
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])

        if role == "user":
            result.append({"role": "user", "content": content})

        elif role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.get("id", "call_0"),
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": _serialize_args(tc["function"].get("arguments", {})),
                        },
                    }
                    for tc in tool_calls
                ]
            result.append(entry)

        elif role == "tool":
            result.append({
                "role": "tool",
                "tool_call_id": msg.get("tool_call_id", "call_0"),
                "content": content,
            })

    return result


# ---------------------------------------------------------------------------
# CONVERTERS — OLLAMA (text-only; strip all tool metadata)
# ---------------------------------------------------------------------------

def to_ollama_history(history: NeutralHistory) -> list[dict]:
    """
    Convert neutral history to Ollama-compatible format.
    Tool calling is disabled for Ollama (Tier 4), so all tool results
    are surfaced as inline assistant notes.
    """
    result: list[dict] = []

    for msg in history:
        role = msg["role"]
        content = msg.get("content", "")

        if role == "user":
            result.append({"role": "user", "content": content})
        elif role == "assistant":
            result.append({"role": "assistant", "content": content})
        elif role == "tool":
            # Flatten tool results into the conversation as assistant notes
            result.append({
                "role": "assistant",
                "content": f"[Tool Result — {msg.get('tool_name', 'tool')}]: {content}",
            })

    return result


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------

def _serialize_args(arguments: dict | str) -> str:
    """Ensure tool call arguments are JSON-serialized strings."""
    import json
    if isinstance(arguments, str):
        return arguments
    return json.dumps(arguments)
