"""Fake Jev HTTP transport used by offline tests; never contacts a provider."""
from __future__ import annotations

import httpx


class FakeJevResponse:
    def __init__(self, ok: bool):
        self.ok = ok

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": (
            '{"ok":' + str(self.ok).lower() + ',"score":0.91,"category":"valid",'
            '"confidence":0.88,"issues":[]}'
        )}}]}


class FakeJevClient:
    """Supports valid, rejected, timeout, and unreachable outcomes."""
    outcome = "valid"

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        if self.outcome == "timeout":
            raise httpx.TimeoutException("fake timeout")
        if self.outcome == "unreachable":
            raise httpx.ConnectError("fake unreachable")
        return FakeJevResponse(self.outcome != "rejected")
