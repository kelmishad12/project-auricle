"""
Main server implementation for Project Auricle.
Provides agentic API for contextual briefings.
"""
import warnings

# Suppress annoying library warnings for a cleaner console
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="deepeval")
warnings.filterwarnings("ignore", module="urllib3")

# pylint: disable=wrong-import-position
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.db.models.base import Base
from src.db.session import engine

load_dotenv()

# Auto-create tables (including our new UserSettings column)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifecycle manager for the FastAPI app."""
    print("🚀 Project Auricle Server starting...")
    yield
    print("🛑 Project Auricle Server shutting down...")

app = FastAPI(
    title="Project Auricle Server",
    description="Agentic API for Contextual Briefings",
    lifespan=lifespan
)


from src.api.routes import router as briefings_router

app.include_router(briefings_router, prefix="/api")


# Mount React Frontend to Root
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
