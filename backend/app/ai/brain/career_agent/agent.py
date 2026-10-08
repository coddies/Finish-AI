"""
agent.py — ReAct (Thought -> Action -> Observation) Loop Engine.

Executes up to MAX_TURNS iterations per request:
  1. Model emits a Thought + optional Action (tool call).
  2. Agent executes the tool and collects the Observation.
  3. Observation is appended to history and the loop continues.
  4. When the model emits no tool calls, the response is final.
"""
from __future__ import annotations

import json
import logging
import asyncio
from typing import Any

from career_agent.config import MAX_TURNS
from career_agent.llm_cascade import call_with_cascade
from career_agent.state_adapter import (
    NeutralHistory,
    append_assistant,
    append_tool_result,
)
from career_agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TOOL EXECUTOR
# ---------------------------------------------------------------------------

def _execute_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    """
    Dispatch a tool call from the registry with full error handling.

    Args:
        tool_name: Name of the tool to execute.
        arguments: Keyword arguments to pass to the tool function.

    Returns:
        Plain string observation — either the tool result or an error message.
    """
    if tool_name not in TOOL_REGISTRY:
        available = list(TOOL_REGISTRY.keys())
        logger.error("[Tool] Unknown tool requested; available_count=%s", len(available))
        return (
            f"Observation: Error — Unknown tool '{tool_name}'. "
            f"Available tools: {available}. Please retry with a valid tool name."
        )

    try:
        func = TOOL_REGISTRY[tool_name]

        # arguments may arrive as a JSON string from some providers
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}

        result = func(**arguments)
        return str(result)

    except TypeError as exc:
        logger.error("[Tool] %s argument error type=%s", tool_name, type(exc).__name__)
        return f"Observation: Error in {tool_name} — Invalid arguments: {exc}"
    except Exception as exc:
        logger.error("[Tool] %s execution error type=%s", tool_name, type(exc).__name__)
        return f"Observation: Error in {tool_name} — {exc}"


# ---------------------------------------------------------------------------
# REACT LOOP ENGINE
# ---------------------------------------------------------------------------

async def run_react_loop(history: NeutralHistory, llm_call=None, max_turns: int = MAX_TURNS,
                        enable_tools: bool = True, traces: list[str] | None = None) -> str:
    """
    Execute the ReAct (Thought -> Action -> Observation) loop.

    The loop continues until:
      - The model returns a response with no tool calls (final answer).
      - MAX_TURNS iterations are reached (hard cap to prevent infinite loops).
      - The LLM cascade is fully exhausted (RuntimeError).

    Args:
        history: Provider-agnostic conversation history. Modified in-place
                 as the loop appends assistant and tool messages.

    Returns:
        Final assistant response text string.
    """
    last_content: str = ""
    turn: int = 0

    max_turns = min(5, max(1, max_turns))
    while turn < max_turns:
        turn += 1
        logger.info("[ReAct] turn=%s/%s", turn, max_turns)

        # ── THOUGHT + ACTION PHASE ────────────────────────────────────────
        try:
            if llm_call is None:
                response = await asyncio.to_thread(call_with_cascade, history, enable_tools=enable_tools)
            else:
                response = await llm_call(history, enable_tools)
        except RuntimeError as exc:
            logger.warning("[ReAct] model cascade unavailable at turn=%s", turn)
            return "I'm temporarily unable to respond. Please try again in a moment."

        content: str = response.get("content", "")
        tool_calls: list[dict] = response.get("tool_calls", [])
        provider: str = response.get("provider", "Unknown")
        last_content = content

        logger.info(
            "[ReAct] provider=%s tool_calls=%s content_len=%s",
            provider, len(tool_calls), len(content)
        )
        if traces is not None:
            traces.append(f"[TURN {turn}] Provider: {provider}")

        # ── FINAL RESPONSE (no tool calls) ───────────────────────────────
        if not tool_calls or not enable_tools:
            append_assistant(history, content)
            logger.info("[ReAct] final answer turn=%s", turn)
            return content

        # ── OBSERVATION PHASE — execute each tool call ────────────────────
        append_assistant(history, content, tool_calls=tool_calls)

        for tc in tool_calls:
            fn = tc.get("function", {})
            tool_name: str = fn.get("name", "")
            arguments: Any = fn.get("arguments", {})
            tool_call_id: str = tc.get("id", "call_0")

            logger.info("[ReAct] executing allow-listed tool=%s", tool_name)
            if traces is not None:
                traces.append(f"[ACTION] {tool_name}")

            observation: str = _execute_tool(tool_name, arguments)
            logger.info("[ReAct] observation tool=%s chars=%s", tool_name, len(observation))
            if traces is not None:
                traces.append(f"[OBSERVATION] {tool_name}: result received")

            append_tool_result(
                history,
                tool_name=tool_name,
                result=observation,
                tool_call_id=tool_call_id,
            )

    # ── MAX TURNS REACHED ─────────────────────────────────────────────────
    logger.warning("[ReAct] max turns reached; returning last content")
    return last_content or "Analysis complete. Please see the observations in the conversation above."
