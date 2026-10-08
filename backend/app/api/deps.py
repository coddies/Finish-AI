from __future__ import annotations

import ipaddress

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import enforce_rate_limits
from app.db.session import get_db


def client_ip(request: Request) -> str:
    # Railway documents X-Real-IP at its public HTTP edge. Only trust it when
    # this service is deployed behind that edge; never trust arbitrary XFF chains.
    if get_settings().trust_railway_proxy:
        forwarded = request.headers.get("x-real-ip", "").strip()
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


def enforce_ip_limit(request: Request, db: Session = Depends(get_db)):
    if request.url.path == "/health":
        return
    enforce_rate_limits(db, client_ip(request))
