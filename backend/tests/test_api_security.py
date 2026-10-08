from __future__ import annotations

import os
import unittest
from unittest.mock import patch
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SESSION_TOKEN_PEPPER"] = "unit-test-only-pepper-not-a-secret"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

from fastapi.testclient import TestClient
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_session
from app.ai.llm import VerificationResult
from app.ai.schemas import MilestoneOutput, PlanOutput, TaskOutput
from app.db.models import Goal, RateLimitCounter, SessionRecord, Task
from app.db.session import Base, get_db
from app.main import app


class ApiSecurityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

        def override_db():
            db = self.sessions()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        with self.sessions() as db:
            self.token_a, self.session_a = create_session(db)
            self.token_b, self.session_b = create_session(db)
            self.goal = Goal(session_id=self.session_b.id, title="Private goal",
                goal_text="Keep this goal private", deadline=date.today() + timedelta(days=30),
                daily_hours=1, language="en", goal_type="general")
            db.add(self.goal)
            db.flush()
            self.foreign_task = Task(goal_id=self.goal.id, title="Hidden task", description="",
                est_hours=1, scheduled_date=date.today(), priority="must", status="pending", depends_on=[])
            db.add(self.foreign_task)
            db.commit()
            self.goal_id = self.goal.id
            self.task_id = self.foreign_task.id

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_missing_token_is_unauthorized(self):
        response = self.client.get("/goals")
        self.assertEqual(response.status_code, 401)

    def test_other_session_goal_is_hidden(self):
        response = self.client.get(f"/goals/{self.goal_id}",
                                   headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(response.status_code, 404)

    def test_other_session_goal_cannot_be_deleted_or_replanned(self):
        headers = {"Authorization": f"Bearer {self.token_a}"}
        deleted = self.client.delete(f"/goals/{self.goal_id}", headers=headers)
        replanned = self.client.post(f"/goals/{self.goal_id}/replan", json={}, headers=headers)
        self.assertEqual(deleted.status_code, 404)
        self.assertEqual(replanned.status_code, 404)

    def test_other_session_task_cannot_be_modified(self):
        response = self.client.post(f"/tasks/{self.task_id}/status", json={"status": "done"},
            headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(response.status_code, 404)

    def test_session_token_is_only_stored_as_hash(self):
        with self.sessions() as db:
            row = db.get(SessionRecord, self.session_a.id)
            self.assertNotEqual(row.token_hash, self.token_a)
            self.assertEqual(len(row.token_hash), 64)

    def test_session_deletion_removes_its_goals(self):
        response = self.client.delete("/session", headers={"Authorization": f"Bearer {self.token_b}"})
        self.assertEqual(response.status_code, 204)
        response = self.client.get(f"/goals/{self.goal_id}",
                                   headers={"Authorization": f"Bearer {self.token_b}"})
        self.assertEqual(response.status_code, 401)

    def test_health_and_goal_validation(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        response = self.client.post("/goals", json={"goal_text": "x", "deadline": "2030-01-01",
            "daily_hours": 1}, headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(response.status_code, 422)

    def test_cors_allows_configured_origin_and_rejects_other_origin(self):
        allowed = self.client.get("/health", headers={"Origin": "http://localhost:3000"})
        denied = self.client.get("/health", headers={"Origin": "https://attacker.example"})
        self.assertEqual(allowed.headers.get("access-control-allow-origin"), "http://localhost:3000")
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_rate_limit_returns_429_and_retry_after(self):
        from app.core import rate_limit
        from app.core.config import get_settings

        original = get_settings()
        with patch.object(rate_limit, "get_settings", return_value=type(original)(
            **{**original.__dict__, "rate_limit_any_per_minute": 1}
        )):
            self.assertEqual(self.client.get("/health").status_code, 200)  # health is excluded
            from app.core.rate_limit import enforce_rate_limits
            with self.sessions() as db:
                enforce_rate_limits(db, "192.0.2.10")
                with self.assertRaises(Exception) as caught:
                    enforce_rate_limits(db, "192.0.2.10")
                self.assertEqual(getattr(caught.exception, "status_code", None), 429)

    def test_client_ip_uses_railway_real_ip_only_when_enabled(self):
        from app.api.deps import client_ip
        from app.core.config import get_settings

        request = Request({"type": "http", "method": "GET", "path": "/", "headers": [
            (b"x-real-ip", b"203.0.113.7"), (b"x-forwarded-for", b"198.51.100.4")],
            "client": ("10.0.0.8", 1234), "scheme": "http", "server": ("test", 80),
            "query_string": b""})
        original = get_settings()
        with patch("app.api.deps.get_settings", return_value=type(original)(
            **{**original.__dict__, "trust_railway_proxy": False}
        )):
            self.assertEqual(client_ip(request), "10.0.0.8")
        with patch("app.api.deps.get_settings", return_value=type(original)(
            **{**original.__dict__, "trust_railway_proxy": True}
        )):
            self.assertEqual(client_ip(request), "203.0.113.7")

    def test_llm_failover_logs_do_not_include_provider_error_secrets(self):
        import logging
        from app.ai.llm import LLM
        from app.ai.budget import RequestBudget

        gateway = object.__new__(LLM)
        gateway.settings = type("Settings", (), {"ai_call_timeout_seconds": 2})()
        gateway._chain = lambda profile: [("provider", "model", "never-log-this-key", "")]

        async def raises(*args, **kwargs):
            raise RuntimeError("never-log-this-key leaked with prompt content")

        gateway._request_one = raises
        with self.assertLogs("app.ai.llm", level=logging.WARNING) as captured:
            import asyncio
            with self.assertRaises(Exception):
                asyncio.run(gateway.invoke("finishai_text", [], RequestBudget(2)))
        self.assertNotIn("never-log-this-key", "\n".join(captured.output))
        self.assertNotIn("prompt content", "\n".join(captured.output))

    def test_create_goal_happy_path_with_fake_ai(self):
        from app.domain.progress import utc_today
        from app.services import goals as goal_service

        async def fake_plan(goal_text, deadline, daily_hours, language, answers, budget, db):
            output = PlanOutput(tools_needed=["Editor"], total_resources=["Official guide"],
                motivation="Keep going", success_tips=["Practice daily"], risks=["Time pressure"],
                milestones=[MilestoneOutput(title="Start", checkpoint="Build a working version",
                    tips=["Test each step"], warnings=["Allow setup time"], tasks=[
                    TaskOutput(title="Do first step", est_hours=1, priority="must")])])
            return output, [{"scheduled_date": utc_today()}], VerificationResult(False), []

        with patch.object(goal_service, "create_plan", side_effect=fake_plan):
            response = self.client.post("/goals", json={"goal_text": "Learn backend APIs",
                "deadline": (utc_today() + timedelta(days=30)).isoformat(), "daily_hours": 1},
                headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "created")
        self.assertFalse(response.json()["verified"])
        goal = response.json()["goal"]
        self.assertEqual(goal["metadata"]["tools_needed"], ["Editor"])
        self.assertEqual(goal["metadata"]["success_tips"], ["Practice daily"])
        self.assertEqual(goal["milestones"][0]["checkpoint"], "Build a working version")
        self.assertEqual(goal["milestones"][0]["warnings"], ["Allow setup time"])

    def test_career_chat_exposes_execution_metadata_and_persists_session_chat(self):
        async def fake_chat(messages, budget, db):
            return ("Career advice", VerificationResult(False),
                    ["[TURN 1] Provider: fake/model"],
                    {"active_provider": "fake/model", "failover_occurred": True,
                     "providers_attempted": ["first/model", "fake/model"]})

        with patch("app.api.routers.career.career_chat", side_effect=fake_chat):
            response = self.client.post("/career/agent-chat", json={"message": "How can I improve my CV?"},
                headers={"Authorization": f"Bearer {self.token_a}"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["execution_metadata"]["active_provider"], "fake/model")
        self.assertTrue(response.json()["execution_metadata"]["failover_occurred"])
        self.assertEqual(response.json()["execution_metadata"]["turns_taken"], 1)


if __name__ == "__main__":
    unittest.main()
