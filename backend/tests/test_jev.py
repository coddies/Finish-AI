from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.ai.budget import RequestBudget
from app.ai.llm import LLM, VerificationResult
from tests.fakes import FakeJevClient


class JevAdapterTests(unittest.TestCase):
    def run_decision(self, outcome: str):
        FakeJevClient.outcome = outcome
        gateway = object.__new__(LLM)
        gateway.settings = SimpleNamespace(
            jev_provider="openai_compatible", jev_model_id="fake-decision-model",
            jev_api_key="fake-test-key", jev_base_url="https://fake.invalid/v1",
            ai_call_timeout_seconds=1.0,
        )
        with patch("app.ai.llm.httpx.AsyncClient", FakeJevClient):
            return asyncio.run(gateway.decide({"candidate": "example"}, {"valid": True},
                                              RequestBudget(3), db=None))

    def test_valid_decision(self):
        result = self.run_decision("valid")
        self.assertTrue(result.verified)
        self.assertTrue(result.decision["ok"])

    def test_rejected_decision(self):
        result = self.run_decision("rejected")
        self.assertTrue(result.verified)
        self.assertFalse(result.decision["ok"])

    def test_timeout_skips_verification(self):
        self.assertFalse(self.run_decision("timeout").verified)

    def test_unreachable_skips_verification(self):
        self.assertFalse(self.run_decision("unreachable").verified)

    def test_disabled_jev_skips_single_verification(self):
        from app.ai.capabilities import create_plan
        from app.ai.schemas import MilestoneOutput, PlanOutput, TaskOutput
        from unittest.mock import AsyncMock
        from datetime import date, timedelta

        output = PlanOutput(milestones=[MilestoneOutput(title="Milestone", checkpoint="Checkpoint",
            tasks=[TaskOutput(title="Task", est_hours=1, priority="must")])])
        with patch("app.ai.capabilities._brain_json", new=AsyncMock(return_value=(output, []))), \
             patch("app.ai.capabilities.llm.decide", new=AsyncMock(return_value=VerificationResult(False))) as decide:
            asyncio.run(create_plan("Build a useful project", (date.today() + timedelta(days=10)).isoformat(),
                                    1, "en", [], RequestBudget(5), None))
        self.assertEqual(decide.await_count, 1)


if __name__ == "__main__":
    unittest.main()
