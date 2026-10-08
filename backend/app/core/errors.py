from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        self.status_code, self.code, self.message, self.details = status_code, code, message, details or {}


async def api_error_handler(request: Request, exc: APIError):
    headers = {"Retry-After": str(exc.details["retry_after"])} if exc.status_code == 429 and "retry_after" in exc.details else None
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}}, headers=headers)


async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": {"fields": details}}})
