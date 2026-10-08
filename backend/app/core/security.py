from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta, timezone

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.db.models import SessionRecord, utcnow
from app.db.session import get_db


def token_hash(token: str) -> str:
    pepper = get_settings().session_token_pepper.encode()
    return hmac.new(pepper, token.encode(), hashlib.sha256).hexdigest()


def create_session(db: Session) -> tuple[str, SessionRecord]:
    raw = secrets.token_urlsafe(32)
    row = SessionRecord(token_hash=token_hash(raw))
    db.add(row)
    db.commit()
    db.refresh(row)
    return raw, row


def current_session(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> SessionRecord:
    if not authorization or not authorization.startswith("Bearer "):
        raise APIError(401, "UNAUTHORIZED", "A valid bearer session token is required")
    supplied = token_hash(authorization[7:].strip())
    row = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == supplied))
    if row is None:
        raise APIError(401, "UNAUTHORIZED", "A valid bearer session token is required")
    last_seen = row.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    if last_seen < utcnow() - timedelta(days=get_settings().session_token_ttl_days):
        db.delete(row)
        db.commit()
        raise APIError(401, "UNAUTHORIZED", "Session expired")
    # Constant-time comparison even though the indexed hash lookup already narrows the row.
    if not hmac.compare_digest(row.token_hash, supplied):
        raise APIError(401, "UNAUTHORIZED", "A valid bearer session token is required")
    row.last_seen_at = utcnow()
    db.commit()
    return row


def owned_goal(db: Session, goal_id: uuid.UUID, session_id: uuid.UUID):
    from app.db.models import Goal
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.session_id == session_id))
    if goal is None:
        raise APIError(404, "NOT_FOUND", "Goal not found")
    return goal
