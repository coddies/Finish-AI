from fastapi import APIRouter, Depends, Request
from fastapi import Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip
from app.core.config import get_settings
from app.core.rate_limit import enforce_rate_limits
from app.core.security import create_session
from app.core.security import current_session
from app.db.models import CareerMessage, CareerProfile, Goal, RateLimitCounter, ReplanProposal, PlanVersion, Resource, Task, Milestone
from app.db.session import get_db
from app.schemas.api import SessionResponse

router = APIRouter(tags=["session"])


@router.post("/session", response_model=SessionResponse, status_code=201)
def issue_session(request: Request, db: Session = Depends(get_db)):
    enforce_rate_limits(db, client_ip(request), session_create=True, any_endpoint=False)
    token, row = create_session(db)
    return SessionResponse(token=token, expires_in_days=get_settings().session_token_ttl_days)


@router.delete("/session", status_code=204)
def delete_session(session=Depends(current_session), db: Session = Depends(get_db)):
    goal_ids = select(Goal.id).where(Goal.session_id == session.id)
    profile_ids = select(CareerProfile.id).where(CareerProfile.session_id == session.id)
    task_ids = select(Task.id).where(Task.goal_id.in_(goal_ids))
    db.execute(delete(Resource).where(Resource.task_id.in_(task_ids)))
    db.execute(delete(Task).where(Task.goal_id.in_(goal_ids)))
    db.execute(delete(Milestone).where(Milestone.goal_id.in_(goal_ids)))
    db.execute(delete(ReplanProposal).where(ReplanProposal.goal_id.in_(goal_ids)))
    db.execute(delete(PlanVersion).where(PlanVersion.goal_id.in_(goal_ids)))
    db.execute(delete(CareerMessage).where(CareerMessage.profile_id.in_(profile_ids)))
    db.execute(delete(CareerProfile).where(CareerProfile.session_id == session.id))
    db.execute(delete(Goal).where(Goal.session_id == session.id))
    db.execute(delete(RateLimitCounter).where(RateLimitCounter.bucket_key.like(f"session:{session.id}:%")))
    db.delete(session)
    db.commit()
    return Response(status_code=204)
