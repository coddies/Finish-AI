from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.ai.budget import BudgetExceeded, RequestBudget
from app.ai.capabilities import coach_chat
from app.ai.llm import InvalidLLMOutput, LLMUnavailable
from app.api.deps import client_ip
from app.core.config import get_settings
from app.core.errors import APIError
from app.core.rate_limit import enforce_rate_limits
from app.core.security import current_session
from app.db.session import get_db
from app.schemas.api import CoachChatRequest

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/chat")
async def chat(body: CoachChatRequest, request: Request,
               session=Depends(current_session), db: Session = Depends(get_db)):
    enforce_rate_limits(db, client_ip(request), str(session.id), llm=True)
    history = [message.model_dump() for message in body.messages]
    budget = RequestBudget(get_settings().ai_budget_plan_seconds)
    try:
        response, verification, traces = await coach_chat(history, budget, db)
    except BudgetExceeded as exc:
        raise APIError(503, "AI_BUSY", "Coach response exceeded its time budget") from exc
    except LLMUnavailable as exc:
        raise APIError(503, "AI_BUSY", "Coach providers are unavailable") from exc
    except InvalidLLMOutput as exc:
        raise APIError(502, "AI_INVALID_OUTPUT", "Coach could not produce a valid response") from exc
    return {"message": response,
            "verified": bool(verification.verified and verification.decision and verification.decision.get("ok")),
            "verification": verification.decision, "agent_traces": traces}
