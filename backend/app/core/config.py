from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be numeric") from exc


@dataclass(frozen=True)
class Settings:
    env: str
    database_url: str
    session_token_pepper: str
    cors_origins: tuple[str, ...]
    trust_railway_proxy: bool
    use_groq: bool
    openai_api_key: str
    groq_api_key: str
    career_agent_groq_api_key: str
    gemini_api_key: str
    nvidia_api_key: str
    hf_token: str
    ollama_base_url: str
    ai_budget_plan_seconds: float
    ai_budget_replan_seconds: float
    ai_call_timeout_seconds: float
    react_max_steps: int
    jev_provider: str
    jev_model_id: str
    jev_api_key: str
    jev_base_url: str
    request_body_max_bytes: int
    max_pdf_size_mb: int
    rate_limit_any_per_minute: int
    rate_limit_session_per_hour: int
    rate_limit_session_per_day: int
    rate_limit_llm_ip_per_hour: int
    rate_limit_replans_per_goal_per_day: int
    llm_global_calls_per_day: int
    llm_global_calls_per_month: int
    session_token_ttl_days: int
    log_level: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    pepper = os.getenv("SESSION_TOKEN_PEPPER", "").strip()
    if not pepper:
        raise RuntimeError("SESSION_TOKEN_PEPPER is required")
    origins = tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip())
    if not origins or "*" in origins:
        raise RuntimeError("CORS_ORIGINS must contain exact origins and cannot include '*'")
    if os.getenv("ENV", "development").lower() == "production" and "CORS_ORIGINS" not in os.environ:
        raise RuntimeError("CORS_ORIGINS must be explicitly set in production")
    react_steps = _int("REACT_MAX_STEPS", 4)
    if not 3 <= react_steps <= 5:
        raise RuntimeError("REACT_MAX_STEPS must be between 3 and 5")
    plan_budget = _float("AI_BUDGET_PLAN_SECONDS", 20)
    replan_budget = _float("AI_BUDGET_REPLAN_SECONDS", 10)
    call_timeout = _float("AI_CALL_TIMEOUT_SECONDS", 8)
    if not 0.5 <= plan_budget <= 30 or not 0.5 <= replan_budget <= 15:
        raise RuntimeError("AI budgets must remain below the 60-second Vercel function ceiling")
    if not 0.1 <= call_timeout <= 20:
        raise RuntimeError("AI_CALL_TIMEOUT_SECONDS must be between 0.1 and 20")
    return Settings(
        env=os.getenv("ENV", "development").lower(), database_url=database_url,
        session_token_pepper=pepper, cors_origins=origins,
        trust_railway_proxy=os.getenv("TRUST_RAILWAY_PROXY", "false").lower() == "true",
        use_groq=os.getenv("USE_GROQ", "false").lower() == "true",
        openai_api_key=os.getenv("OPENAI_API_KEY", ""), groq_api_key=os.getenv("GROQ_API_KEY", ""),
        career_agent_groq_api_key=os.getenv("CAREER_AGENT_GROQ_API_KEY", os.getenv("GROQ_API_KEY", "")),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""), nvidia_api_key=os.getenv("NVIDIA_API_KEY", ""),
        hf_token=os.getenv("HF_TOKEN", ""), ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ai_budget_plan_seconds=plan_budget,
        ai_budget_replan_seconds=replan_budget,
        ai_call_timeout_seconds=call_timeout,
        react_max_steps=react_steps, jev_provider=os.getenv("JEV_PROVIDER", "").strip().lower(),
        jev_model_id=os.getenv("JEV_MODEL_ID", "").strip(), jev_api_key=os.getenv("JEV_API_KEY", ""),
        jev_base_url=os.getenv("JEV_BASE_URL", "").rstrip("/"),
        request_body_max_bytes=_int("REQUEST_BODY_MAX_BYTES", 32768),
        max_pdf_size_mb=_int("MAX_PDF_SIZE_MB", 5),
        rate_limit_any_per_minute=_int("RATE_LIMIT_ANY_PER_MINUTE", 120),
        rate_limit_session_per_hour=_int("RATE_LIMIT_SESSION_PER_HOUR", 10),
        rate_limit_session_per_day=_int("RATE_LIMIT_SESSION_PER_DAY", 40),
        rate_limit_llm_ip_per_hour=_int("RATE_LIMIT_LLM_IP_PER_HOUR", 30),
        rate_limit_replans_per_goal_per_day=_int("RATE_LIMIT_REPLANS_PER_GOAL_PER_DAY", 10),
        llm_global_calls_per_day=_int("LLM_GLOBAL_CALLS_PER_DAY", 10000),
        llm_global_calls_per_month=_int("LLM_GLOBAL_CALLS_PER_MONTH", 200000),
        session_token_ttl_days=_int("SESSION_TOKEN_TTL_DAYS", 90),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
