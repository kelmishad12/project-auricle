"""
Main server implementation for Project Auricle.
Provides agentic API for contextual briefings.
"""
import os
from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from src.adapters.config import get_providers
from src.core.graph import AuricleGraph

load_dotenv()


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


class BriefingRequest(BaseModel):
    """Request model for /api/v1/briefings/generate"""
    user_email: str
    env: str = "dev"


@app.post("/api/v1/briefings/generate")
async def generate_briefing(req: BriefingRequest):
    """Generate a contextual briefing for a user."""
    print("Generating briefing for user: ", req.user_email)
    providers = get_providers(env=req.env)

    initial_state = {
        "messages": [],
        "email_summaries": [],
        "calendar_events": [],
        "briefing": "",
        "safety_check_passed": False
    }

    db_url = os.environ.get("DATABASE_URL")

    try:
        if db_url:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
                await checkpointer.asetup()
                print("✅ AsyncPostgresSaver initialized successfully.")
                graph = AuricleGraph(
                    mail_provider=providers["mail_provider"],
                    cal_provider=providers["cal_provider"],
                    checkpointer=checkpointer
                )
                
                # ==============================================================================
                # 🕰️ TIME TRAVEL DEBUGGING (State Persistence)
                # To verify state persists to Postgres, check the `checkpoints` tables in your DB.
                # To rewinde/retry, you can fetch an existing state via `checkpointer.aget(config)`
                # and pass a specific `thread_id` to override the "default" execution thread.
                # Example:
                # config = {"configurable": {"thread_id": "test_thread_123"}}
                # state = await checkpointer.aget(config)
                # final_state = await graph.ainvoke(state, thread_id="test_thread_123")
                # ==============================================================================
                final_state = await graph.ainvoke(initial_state)
        else:
            raise ValueError("DATABASE_URL not set.")
    except Exception as e:
        print(f"⚠️ DB fallback triggered ({e}). Using MemorySaver.")
        graph = AuricleGraph(
            mail_provider=providers["mail_provider"],
            cal_provider=providers["cal_provider"],
            checkpointer=MemorySaver()
        )
        final_state = await graph.ainvoke(initial_state)

    return {
        "status": "success",
        "briefing": final_state.get("briefing"),
        "safety_passed": final_state.get("safety_check_passed")
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
