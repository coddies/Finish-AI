from __future__ import annotations

import asyncio
import time


class BudgetExceeded(TimeoutError):
    pass


class RequestBudget:
    """Monotonic wall-clock deadline shared by every model call in one operation."""
    def __init__(self, seconds: float):
        self.started = time.monotonic()
        self.deadline = self.started + max(0.0, seconds)

    def remaining(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    def check(self, minimum: float = 0.05) -> float:
        left = self.remaining()
        if left < minimum:
            raise BudgetExceeded("AI request budget exhausted")
        return left

    async def wait_for(self, awaitable, timeout_cap: float):
        timeout = min(self.check(), timeout_cap)
        try:
            return await asyncio.wait_for(awaitable, timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise BudgetExceeded("AI call timed out within the request budget") from exc
