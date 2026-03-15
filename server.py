"""
Main server implementation for Project Auricle.
Provides agentic API for contextual briefings.
"""
import os
from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.adapters.config import get_providers
from src.core.graph import AuricleGraph
from src.services.gemini import GeminiService
from src.services.elevenlabs import ElevenLabsService
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


class BriefingRequest(BaseModel):
    """Request model for /api/v1/briefings/generate"""
    user_email: str
    env: str = "dev"
    profile_path: str = "scripts/system_profile_sample.txt"


@app.post("/api/v1/briefings/generate")
async def generate_briefing(req: BriefingRequest,
                            background_tasks: BackgroundTasks):
    """Generate a contextual briefing for a user."""
    # pylint: disable=too-many-locals,too-many-statements
    print("Generating briefing for user: ", req.user_email)

    # Inject dynamic persona from UI
    if req.profile_path:
        os.environ["USER_PROFILE_PATH"] = req.profile_path

    os.environ["USER_EMAIL"] = req.user_email

    providers = get_providers(env=req.env)

    initial_state = {
        "messages": [],
        "email_summaries": [],
        "calendar_events": [],
        "briefing": "",
        "spoken_briefing": "",
        "safety_check_passed": False,
        "revision_count": 0,
        "critic_feedback": ""
    }

    db_url = os.environ.get("DATABASE_URL")
    final_state = initial_state

    try:
        if db_url:
            # pylint: disable=import-outside-toplevel
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
                await checkpointer.setup()
                print("✅ AsyncPostgresSaver initialized successfully.")
                graph = AuricleGraph(
                    mail_provider=providers["mail_provider"],
                    cal_provider=providers["cal_provider"],
                    checkpointer=checkpointer
                )

                timing_metrics = {}
                import time
                start_time = time.time()

                config = {"configurable": {"thread_id": "default",
                                           "mail_provider": providers["mail_provider"],
                                           "cal_provider": providers["cal_provider"]}}
                async for event in graph.app.astream(initial_state, config=config):
                    if isinstance(event, dict):
                        for node_name, state_update in event.items():
                            if isinstance(state_update, dict):
                                current_time = time.time()
                                elapsed = (current_time - start_time) * 1000
                                timing_metrics[node_name] = round(elapsed)
                                start_time = current_time  # Reset cursor for next node
                                final_state.update(state_update)
                                print(
                                    f"[{node_name}] finished in {timing_metrics[node_name]}ms")
                # Add overall TTFT after stream finishes
                timing_metrics["Total"] = sum(timing_metrics.values())

        else:
            raise ValueError("DATABASE_URL not set.")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"⚠️ DB/Streaming fallback triggered ({e}). Using MemorySaver.")
        graph = AuricleGraph(
            mail_provider=providers["mail_provider"],
            cal_provider=providers["cal_provider"],
            checkpointer=MemorySaver()
        )
        final_state = await graph.ainvoke(initial_state)
        timing_metrics = {"fallback": 0}

    # Extract cache_id from the DB as a fallback or fetch it from UserSettings.
    # pylint: disable=import-outside-toplevel
    from src.db.session import SessionLocal
    from src.db.models.base import UserSettings

    db = SessionLocal()
    cache_id = None
    try:
        user_settings = db.query(UserSettings).filter(
            UserSettings.user_email == req.user_email).first()
        if user_settings:
            cache_id = user_settings.cache_id
    finally:
        db.close()

    print("✅ Briefing generated successfully.")
    print(f"✅ Cache ID established: {cache_id}")

    async def generate_audio_background(briefing_text: str, safety_passed: bool):
        """Background task to synthesize audio asynchronously."""
        if not briefing_text:
            return

        try:
            if safety_passed:
                gemini_svc = GeminiService()
                prompt = (
                    "You are an expert voice scriptwriter. Take the following daily briefing "
                    "and rewrite it to be read out loud naturally by a text-to-speech engine. "
                    "Remove all markdown formatting, bullet points, asterisks, "
                    "and special characters.\n"
                    "Ensure the flow is conversational, warm, and professional, "
                    "as if spoken by a human assistant.\n"
                    "Write out numbers plainly (e.g., 'three thirty PM' instead of '3:30').\n\n"
                    f"Original Briefing:\n{briefing_text}"
                )
                spoken_text = gemini_svc.generate_content(prompt)
            else:
                spoken_text = briefing_text

            eleven = ElevenLabsService()
            audio_bytes = eleven.generate_audio_stream(spoken_text)
            with open("frontend/audio.mp3", "wb") as f:
                f.write(audio_bytes)
            print("✅ Background Task: Audio synthesis completed.")
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"⚠️ Background Task: Audio synthesis failed: {e}")

    # Kick off TTS concurrently so TTFT resolves instantly
    background_tasks.add_task(
        generate_audio_background,
        final_state.get("briefing"),
        final_state.get("safety_check_passed"))

    return {
        "status": "success",
        "briefing": final_state.get("briefing"),
        "safety_passed": final_state.get("safety_check_passed"),
        "cache_id": cache_id,
        "audio_path": "audio.mp3",
        "timing_metrics": timing_metrics
    }


class ChatRequest(BaseModel):
    """Request model for /api/v1/briefings/chat"""
    cache_id: str
    message: str


@app.post("/api/v1/briefings/chat")
async def chat_briefing(req: ChatRequest):
    """Deep Dive Query against a cached context."""
    if not req.cache_id:
        raise HTTPException(
            status_code=400,
            detail="cache_id is required for deep-dive chat.")

    print(f"💬 Deep dive chat requested with cache: {req.cache_id}")
    print(f"User Message: {req.message}")

    gemini = GeminiService()
    response = gemini.chat_with_context(req.cache_id, req.message)

    print("✅ Deep dive chat response generated successfully.")

    return {
        "status": "success",
        "answer": response
    }


# Mount React Frontend to Root
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
