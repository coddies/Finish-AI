from __future__ import annotations

import unittest
from datetime import date, timedelta

from app.domain.feasibility import replan_feasibility
from app.domain.scheduler import ScheduleError, schedule_tasks
from app.integrations.safe_fetch import verify_url


class SchedulerTests(unittest.TestCase):
    def test_schedules_capacity_and_dependencies(self):
        today = date.today()
        result = schedule_tasks([
            {"est_hours": 2, "depends_on": []},
            {"est_hours": 1, "depends_on": [0]},
        ], today, today + timedelta(days=2), 2)
        self.assertEqual(result[0]["scheduled_date"], today)
        self.assertEqual(result[1]["scheduled_date"], today + timedelta(days=1))

    def test_rejects_dependency_forward_reference(self):
        with self.assertRaises(ScheduleError):
            schedule_tasks([{"est_hours": 1, "depends_on": [0]}], date.today(),
                           date.today() + timedelta(days=1), 2)

    def test_infeasible_returns_options(self):
        today = date.today()
        result = replan_feasibility([{"id": "a", "est_hours": 8, "priority": "must"}],
                                    today, today, 2)
        self.assertFalse(result["feasible"])
        self.assertTrue(result["options"])


class SafeFetchTests(unittest.TestCase):
    @staticmethod
    def resolve_without_network(coro):
        try:
            coro.send(None)
        except StopIteration as result:
            return result.value
        coro.close()
        raise AssertionError("Unexpected network/DNS await in offline safety test")

    def test_rejects_unsafe_urls_without_network_access(self):
        for url in ("file:///etc/passwd", "http://127.0.0.1", "http://localhost",
                    "http://169.254.169.254", "http://[::1]/"):
            self.assertFalse(self.resolve_without_network(verify_url(url)), url)

    def test_accepts_curated_resource(self):
        self.assertTrue(self.resolve_without_network(verify_url("https://docs.python.org/3/tutorial/")))


if __name__ == "__main__":
    unittest.main()
