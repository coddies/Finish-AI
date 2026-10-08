from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import enforce_ip_limit
from app.api.routers import career, coach, goals, health, session, tasks
from app.core.config import get_settings
from app.core.errors import APIError, api_error_handler, validation_error_handler
from app.core.logging import RequestContextMiddleware, SecurityHeadersMiddleware

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
for noisy in ("httpx", "httpcore", "openai", "groq", "google"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


class RequestBodyLimitMiddleware:
    def __init__(self, app, max_bytes: int, pdf_max_bytes: int):
        self.app, self.max_bytes, self.pdf_max_bytes = app, max_bytes, pdf_max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        is_pdf_upload = scope.get("path") == "/career/resume"
        body_limit = self.pdf_max_bytes + 65536 if is_pdf_upload else self.max_bytes
        content_length = next((v.decode() for k, v in scope.get("headers", []) if k.lower() == b"content-length"), None)
        if content_length and content_length.isdigit() and int(content_length) > body_limit:
            response = JSONResponse(status_code=413, content={"error": {"code": "VALIDATION_ERROR", "message": "Request body is too large", "details": {}}})
            return await response(scope, receive, send)
        received = 0
        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > body_limit:
                    raise APIError(413, "VALIDATION_ERROR", "Request body is too large")
            return message
        try:
            await self.app(scope, limited_receive, send)
        except APIError as exc:
            response = JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}})
            await response(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="FinishAI API", version="2.0.0",
              docs_url=None if settings.env == "production" else "/docs",
              redoc_url=None if settings.env == "production" else "/redoc",
              openapi_url=None if settings.env == "production" else "/openapi.json",
              lifespan=lifespan, dependencies=[Depends(enforce_ip_limit)])
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    code = {401: "UNAUTHORIZED", 404: "NOT_FOUND", 409: "CONFLICT", 429: "RATE_LIMITED"}.get(exc.status_code, "INTERNAL")
    headers = dict(exc.headers or {})
    if exc.status_code == 429 and "Retry-After" not in headers:
        headers["Retry-After"] = "60"
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": str(exc.detail), "details": {}}},
                        headers=headers)


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logging.getLogger("finishai.error").error("unhandled request error request_id=%s type=%s",
        getattr(request.state, "request_id", None), type(exc).__name__)
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL", "message": "An internal error occurred",
                                         "details": {"request_id": getattr(request.state, "request_id", None)}}})


app.add_middleware(RequestBodyLimitMiddleware, max_bytes=settings.request_body_max_bytes,
                   pdf_max_bytes=settings.max_pdf_size_mb * 1024 * 1024)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=False,
                   allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                   allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"])
app.include_router(session.router)
app.include_router(health.router)
app.include_router(goals.router)
app.include_router(tasks.router)
app.include_router(career.router)
app.include_router(coach.router)
