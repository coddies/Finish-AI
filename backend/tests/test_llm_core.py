from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.ai.budget import RequestBudget
from app.ai.budget import BudgetExceeded
from app.ai.llm import LLM, LLMResult, parse_json


class LlmCoreTests(unittest.TestCase):
    def test_pooled_psycopg_disables_prepared_statements(self):
        from sqlalchemy.pool import NullPool
        from app.db.session import _engine_options

        options = _engine_options("postgresql+psycopg://user:pass@pooler/db")
        self.assertIs(options["poolclass"], NullPool)
        self.assertIsNone(options["connect_args"]["prepare_threshold"])

    def test_time_budget_expires(self):
        budget = RequestBudget(0)
        with self.assertRaises(BudgetExceeded):
            budget.check()

    def test_deterministic_json_repair(self):
        self.assertEqual(parse_json("```json\n{\"items\":[1,2,],}\n```"), {"items": [1, 2]})

    def test_unrecoverable_json_fails(self):
        with self.assertRaises(ValueError):
            parse_json("not json")

    def test_profiles_preserve_independent_model_order(self):
        gateway = object.__new__(LLM)
        gateway.settings = SimpleNamespace(
            use_groq=True, groq_api_key="", openai_api_key="", gemini_api_key="",
            hf_token="", ollama_base_url="http://localhost:11434")
        self.assertEqual([x[1] for x in gateway._finishai_chain()], [
            "llama-3.1-8b-instant", "llama-3.3-70b-versatile", "qwen/qwen3.6-27b",
            "openai/gpt-oss-20b", "groq/compound-mini", "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"])
        self.assertEqual([x[1] for x in gateway._career_chain()], [
            "models/gemini-3.6-flash", "openai/gpt-oss-120b", "qwen/qwen3.8-27b",
            "openai/gpt-oss-20b", "meta-llama/Llama-3.3-70B-Instruct", "gemma:4b"])

    def test_empty_jev_configuration_is_disabled(self):
        gateway = object.__new__(LLM)
        gateway.settings = SimpleNamespace(jev_provider="", jev_model_id="", jev_api_key="", jev_base_url="")
        self.assertFalse(gateway.jev_enabled())


class LlmFailoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_limit_immediately_uses_next_tier(self):
        gateway = object.__new__(LLM)
        gateway.settings = SimpleNamespace()
        gateway._chain = lambda profile: [
            ("openai", "primary", "key-1", ""),
            ("groq", "backup", "key-2", ""),
        ]
        calls = []

        async def fake_request(provider, model, key, base_url, messages, tools, budget):
            calls.append(model)
            if model == "primary":
                raise RuntimeError("429 rate limit")
            return LLMResult("ok", provider, model, [])

        gateway._request_one = fake_request
        result = await gateway.invoke("finishai_text", [], RequestBudget(5))
        self.assertEqual(calls, ["primary", "backup"])
        self.assertEqual(result.content, "ok")
        self.assertEqual(result.providers_attempted, ["openai/primary", "groq/backup"])


if __name__ == "__main__":
    unittest.main()
