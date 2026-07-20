"""
FinishAI — FastAPI entry point.
Run with: uvicorn main:app --reload --port 8000
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from services.gpt import gpt_service
from routes.projects import router as projects_router
from routes.tasks import router as tasks_router
from routes.ai import router as ai_router
from routes.replan import router as replan_router

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Create FastAPI app
app = FastAPI(
    title="FinishAI API",
    description="AI-powered project execution coach — Plan Less, Finish More.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": str(exc.body)
        }
    )

# CORS — allow all origins for hackathon (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(ai_router)
app.include_router(replan_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    provider = f"Groq ({gpt_service.model})" if gpt_service.use_groq else f"OpenAI ({gpt_service.model})"
    return {
        "status": "ok",
        "service": "FinishAI API",
        "version": "1.0.0",
        "ai_provider": provider,
        "use_groq": gpt_service.use_groq,
        "hackathon": "OpenAI Build Week 2026",
    }


@app.get("/")
async def root():
    return {"message": "FinishAI API is running. Visit /docs for API documentation."}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
