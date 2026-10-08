from __future__ import annotations

from datetime import timedelta
import hashlib

from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import APIError
from app.db.models import RateLimitCounter, utcnow


def _hit(db: Session, key: str, limit: int, seconds: int) -> tuple[bool, int]:
    now = utcnow()
    reset = now + timedelta(seconds=seconds)
    db.execute(delete(RateLimitCounter).where(RateLimitCounter.reset_at <= now))
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        stmt = pg_insert(RateLimitCounter).values(bucket_key=key, count=1, reset_at=reset)
        stmt = stmt.on_conflict_do_update(index_elements=[RateLimitCounter.bucket_key],
            set_={"count": case((RateLimitCounter.reset_at <= now, 1), else_=RateLimitCounter.count + 1),
                  "reset_at": case((RateLimitCounter.reset_at <= now, reset), else_=RateLimitCounter.reset_at)}
        ).returning(RateLimitCounter.count, RateLimitCounter.reset_at)
        row = db.execute(stmt).first()
        db.commit()
        row_reset = row.reset_at
        if row_reset.tzinfo is None:
            row_reset = row_reset.replace(tzinfo=now.tzinfo)
        return row.count <= limit, max(1, int((row_reset - now).total_seconds()))
    if dialect == "sqlite":
        stmt = sqlite_insert(RateLimitCounter).values(bucket_key=key, count=1, reset_at=reset)
        stmt = stmt.on_conflict_do_update(index_elements=[RateLimitCounter.bucket_key],
            set_={"count": case((RateLimitCounter.reset_at <= now, 1), else_=RateLimitCounter.count + 1),
                  "reset_at": case((RateLimitCounter.reset_at <= now, reset), else_=RateLimitCounter.reset_at)}
        ).returning(RateLimitCounter.count, RateLimitCounter.reset_at)
        row = db.execute(stmt).first()
        db.commit()
        row_reset = row.reset_at
        if row_reset.tzinfo is None:
            row_reset = row_reset.replace(tzinfo=now.tzinfo)
        return row.count <= limit, max(1, int((row_reset - now).total_seconds()))
    # Only used by an explicitly single-instance local database.
    row = db.get(RateLimitCounter, key)
    if row is None or row.reset_at <= now:
        row = RateLimitCounter(bucket_key=key, count=1, reset_at=reset)
        db.merge(row)
    else:
        row.count += 1
    db.commit()
    return row.count <= limit, max(1, int((row.reset_at - now).total_seconds()))


def enforce_rate_limits(db: Session, ip: str, session_id: str | None = None, llm: bool = False,
                        session_create: bool = False, any_endpoint: bool = True,
                        replan_goal_id: str | None = None):
    cfg = get_settings()
    ip = hashlib.sha256(ip.encode()).hexdigest()
    checks = [(f"ip:{ip}:minute", cfg.rate_limit_any_per_minute, 60)] if any_endpoint else []
    if session_create:
        checks.append((f"ip:{ip}:session-hour", 10, 3600))
    if llm:
        checks.append((f"ip:{ip}:llm-hour", cfg.rate_limit_llm_ip_per_hour, 3600))
        if session_id:
            checks.extend([(f"session:{session_id}:llm-hour", cfg.rate_limit_session_per_hour, 3600),
                           (f"session:{session_id}:llm-day", cfg.rate_limit_session_per_day, 86400)])
        if replan_goal_id:
            checks.append((f"session:{session_id}:goal:{replan_goal_id}:replan-day",
                           cfg.rate_limit_replans_per_goal_per_day, 86400))
    for key, limit, seconds in checks:
        allowed, retry = _hit(db, key, limit, seconds)
        if not allowed:
            if key.startswith("llm:global:"):
                raise APIError(503, "AI_BUSY", "The service AI usage budget is temporarily exhausted",
                               {"retry_after": retry})
            raise APIError(429, "RATE_LIMITED", "Request limit exceeded", {"retry_after": retry})


def enforce_global_llm_call_budget(db: Session) -> None:
    cfg = get_settings()
    for key, limit, seconds in (("llm:global:day", cfg.llm_global_calls_per_day, 86400),
                                ("llm:global:month", cfg.llm_global_calls_per_month, 30 * 86400)):
        allowed, retry = _hit(db, key, limit, seconds)
        if not allowed:
            raise APIError(503, "AI_BUSY", "The service AI call budget is temporarily exhausted",
                           {"retry_after": retry})
