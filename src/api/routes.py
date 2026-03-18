"""
Briefings API route definitions.
"""
import os
import time

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver

from src.adapters.config import get_providers
from src.core.graph import AuricleGraph
from src.services.gemini import GeminiService
from src.services.elevenlabs import ElevenLabsService
from src.services.evals import EvalService

router = APIRouter(prefix="/v1/briefings", tags=["briefings"])


class BriefingRequest(BaseModel):
    """Request model for /api/v1/briefings/generate"""
    user_email: str
    env: str = "dev"
    profile_path: str = "scripts/system_profile_sample.txt"


@router.post("/generate")
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

    # We no longer block on Audio Generation! The client UI will invoke
    # the Streaming API to hear it instantly.

    # Also kick off the DeepEval background evaluation
    context_list = final_state.get("email_summaries", []) + final_state.get("calendar_events", [])
    if not context_list:
        context_list = ["No context found."]

    if cache_id:
        background_tasks.add_task(
            EvalService.run_live_eval,
            cache_id=cache_id,
            input_text="Summarize my day and prioritize critical items.",
            actual_output=final_state.get("briefing", ""),
            retrieval_context=context_list
        )

    return {
        "status": "success",
        "briefing": final_state.get("briefing"),
        "safety_passed": final_state.get("safety_check_passed"),
        "cache_id": cache_id,
        "audio_path": f"/api/v1/briefings/audio/stream?cache_id={cache_id}" if cache_id else None,
        "timing_metrics": timing_metrics
    }


class ChatRequest(BaseModel):
    """Request model for /api/v1/briefings/chat"""
    cache_id: str
    message: str


@router.post("/chat")
def chat_briefing(req: ChatRequest):
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


@router.get("/audio/stream")
def stream_audio(cache_id: str):
    """Streams TTFT audio instantly to the client via chunk generation."""
    gemini = GeminiService()
    eleven = ElevenLabsService()

    # Generate the TTS script using the cached context directly!
    prompt = (
        "You are an expert voice scriptwriter. Take the existing daily briefing context "
        "and rewrite it to be read out loud naturally by a text-to-speech engine. "
        "Remove all markdown formatting, bullet points, asterisks, "
        "and special characters.\n"
        "Ensure the flow is conversational, warm, and professional, "
        "as if spoken by a human assistant.\n"
        "Write out numbers plainly (e.g., 'three thirty PM' instead of '3:30').\n"
        "Only output the transcribed voice lines, do not acknowledge these instructions."
    )

    try:
        spoken_text = gemini.chat_with_context(cache_id, prompt)
    except Exception as e:  # pylint: disable=broad-exception-caught
        spoken_text = f"Warning: Memory extraction failed. Error: {e}"

    return StreamingResponse(
        eleven.generate_audio_stream(spoken_text),
        media_type="audio/mpeg"
    )

@router.get("/evals/{cache_id:path}")
async def get_evals(cache_id: str):
    """Retrieve DeepEval metrics for a specific briefing cache."""
    # pylint: disable=import-outside-toplevel
    from src.db.session import SessionLocal
    from src.db.models.base import EvalMetrics
    db = SessionLocal()
    try:
        record = db.query(EvalMetrics).filter(EvalMetrics.cache_id == cache_id).first()
        if not record:
            return {"status": "pending", "message": "Evaluation not started or missing."}

        return {
            "status": record.status,
            "metrics": {
                "faithfulness": {
                    "score": record.faithfulness_score,
                    "reasoning": record.faithfulness_reasoning
                },
                "answer_relevance": {
                    "score": record.answer_relevance_score,
                    "reasoning": record.answer_relevance_reasoning
                },
                "hallucination": {
                    "score": record.hallucination_score,
                    "reasoning": record.hallucination_reasoning
                }
            }
        }
    finally:
        db.close()
