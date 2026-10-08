"""ASGI entrypoint; legacy route modules remain available for source reference."""
from app.main import app

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
