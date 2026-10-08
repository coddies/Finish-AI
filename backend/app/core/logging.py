from __future__ import annotations

import logging
import re
import uuid
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import get_settings


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        requested_id = request.headers.get("x-request-id", "")
        request_id = requested_id if len(requested_id) <= 80 and re.fullmatch(r"[A-Za-z0-9._:-]+", requested_id) else str(uuid.uuid4())
        request.state.request_id = request_id
        start = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        logging.getLogger("finishai.http").info("request_id=%s method=%s path=%s status=%s latency_ms=%d",
            request_id, request.method, request.url.path, response.status_code, int((perf_counter() - start) * 1000))
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
        is_https = request.url.scheme == "https" or (
            get_settings().trust_railway_proxy and forwarded_proto == "https")
        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
