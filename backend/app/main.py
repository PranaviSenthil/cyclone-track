import os
import sys

# Ensure root directory is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.api.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "AI-Driven Digital Twin for Multi-Source Tropical Cyclone Pattern Analysis and Prediction. "
        "Built for Smart India Hackathon 2026 (SIH26070). Team: MISSION_POSSIBLE."
    ),
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development allow all local frontend ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for benchmark satellite imagery
static_imagery_dir = settings.SAMPLE_IMAGERY_DIR
if os.path.exists(static_imagery_dir):
    app.mount("/static/imagery", StaticFiles(directory=static_imagery_dir), name="static_imagery")

# Mount API router
app.include_router(api_router, prefix=settings.API_PREFIX)

@app.get("/")
def root():
    return {
        "project": settings.PROJECT_NAME,
        "team": "MISSION_POSSIBLE",
        "problem_statement": "SIH26070",
        "documentation": "/docs",
        "api_health": f"{settings.API_PREFIX}/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
