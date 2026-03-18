"""
LangGraph node implementations.
"""
import os
import concurrent.futures
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

from src.core.state import AgentState
from src.db.session import SessionLocal
from src.db.models.base import UserSettings
from src.services.google import CalendarProvider, MailProvider
from src.services.gemini import GeminiService


def get_mail_provider(config: RunnableConfig) -> MailProvider:
    """Extract MailProvider from config."""
    return config["configurable"].get("mail_provider")


def get_cal_provider(config: RunnableConfig) -> CalendarProvider:
    """Extract CalendarProvider from config."""
    return config["configurable"].get("cal_provider")

# pylint: disable=unused-argument


async def supervisor(_state: AgentState, config: RunnableConfig):
    """Supervisor node that routes to fetchers in parallel."""
    return {}


async def fetch_emails(_state: AgentState, config: RunnableConfig):
    """Fetch emails using the injected MailProvider port."""
    mail_provider = get_mail_provider(config)
    emails = await mail_provider.get_recent_emails(limit=5)
    return {"email_summaries": [
        f"Email from {e['sender']}: {e['subject']}" for e in emails]}


async def fetch_calendar(_state: AgentState, config: RunnableConfig):
    """Fetch calendar events using the injected CalendarProvider port."""
    cal_provider = get_cal_provider(config)
    events = await cal_provider.get_upcoming_events(days=1)
    return {"calendar_events": [
        f"Event: {e['title']} at {e['time']}" for e in events]}

# pylint: disable=unused-argument


# pylint: disable=too-many-locals
def build_profile_text() -> tuple[str, str]:
    """Reads system instructions and builds semantic padding."""
    profile_path = "/Users/kelmishad/project-auricle/scripts/system_profile_sample.txt"
    with open(profile_path, "r", encoding="utf-8") as f:
        user_profile_text = f.read()

    semantic_padding = (
        "\n\n--- ARCHITECTURAL KNOWLEDGE BASE (SEMANTIC PADDING) ---\n"
        "Design Decision 1: This AI operates inside Project Auricle, a cutting-edge "
        "LangGraph architecture using asynchronous PostgresSaver checkpointing. "
        "Design Decision 2: The UI is decoupled via a React frontend and interacts "
        "solely via REST API. "
        "Design Decision 3: Safety is enforced via a Reflexion Loop that recursively "
        "critiques output for PII leakage or hallucinations before audio synthesis is permitted.\n"
    ) * 30  # Roughly 30 * 50 = ~1500 words -> ~2000 tokens

    user_profile_text += semantic_padding

    version_line = next(
        (line for line in user_profile_text.splitlines() if "[ID:" in line),
        ""
    )
    version = "UNKNOWN"
    if "[ID:" in version_line:
        version = version_line.split("[ID:")[1].split("]")[0].strip()

    return user_profile_text, version


def synthesize_briefing(state: AgentState, config: RunnableConfig):
    """Synthesize the final briefing contextually using Memory Tiering."""
    gemini = GeminiService()

    # Extract DB settings before disk I/O so we can shortcut
    user_email = os.environ.get("USER_EMAIL", "SHAWN_KELMI_VP_ENG")
    db: Session = SessionLocal()

    try:
        settings = db.query(UserSettings).filter(
            UserSettings.user_email == user_email).first()
        if not settings:
            settings = UserSettings(user_email=user_email)
            db.add(settings)
            db.commit()
            db.refresh(settings)

        user_profile_text, user_profile_version = build_profile_text()

        emails = chr(10).join(state.get('email_summaries', []))
        calendar = chr(10).join(state.get('calendar_events', []))
        dynamic_data = f"Emails:\n{emails}\n\nCalendar:\n{calendar}"

        system_instruction = (
            "You are an AI Executive Assistant. Create a concise, professional "
            "daily briefing using the following data. Keep it under 5 minutes "
            "when spoken. Do not include conversational greetings like 'Good morning'. "
            "Jump straight into summarizing the data."
        )

        prompt = "Please draft today's briefing."
        fallback_prompt = (
            f"SYSTEM INSTRUCTION: {system_instruction}\n"
            "CRITICAL constraints:\n"
            "- Do NOT output or summarize the AI architectural padding.\n"
            "- Do NOT output my user profile, role, title, or OKRs.\n"
            "- ONLY summarize the Emails and Calendar data below.\n\n"
            f"<BACKGROUND_PROFILE>\n{user_profile_text}\n</BACKGROUND_PROFILE>\n\n"
            f"<DATA_TO_SUMMARIZE>\n{dynamic_data}\n</DATA_TO_SUMMARIZE>\n\n"
            f"USER REQUEST: {prompt}"
        )

        def ensure_cache():
            cid = settings.cache_id
            if cid and gemini.validate_cache(cid):
                return cid
            print("DEBUG nodes.py: Cache is invalid/missing. Creating a new one.")
            new_cid = gemini.create_cached_context(
                system_instruction=system_instruction,
                user_profile_text=user_profile_text,
                dynamic_data=dynamic_data
            )
            return new_cid

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_cache = executor.submit(ensure_cache)
            future_briefing = executor.submit(gemini.generate_content, fallback_prompt)

            final_cache_id = future_cache.result()
            briefing = future_briefing.result()

        if final_cache_id and final_cache_id != settings.cache_id:
            settings.cache_id = final_cache_id
            db.commit()

    finally:
        db.close()

    return {
        "briefing": briefing,
        "user_profile_version": user_profile_version
    }

# pylint: disable=unused-argument


def reflexion_loop(state: AgentState, config: RunnableConfig):
    """Enforce strict Safety/Privacy protocols via a Reflexion loop."""
    gemini = GeminiService()
    analysis = gemini.analyze_context(state)

    safety_passed = analysis.get("safety_passed", False)
    reasoning = analysis.get("reasoning", "")

    if not safety_passed:
        print(f"[Reflexion] Safety Warning: {reasoning}")
        return {
            "safety_check_passed": False,
            "critic_feedback": reasoning
        }

    return {
        "safety_check_passed": True,
        "critic_feedback": ""
    }

# pylint: disable=unused-argument


def safe_mode_fallback(_state: AgentState, config: RunnableConfig):
    """Fallback node if the reflexion loop fails 3 times."""
    print("[Safe Mode] Agent failed safety checks too many times. Falling back to safe output.")
    safe_briefing = (
        "Good morning. I encountered multiple safety or formatting errors while generating "
        "your briefing today. Please check your email and calendar manually for updates."
    )
    return {"briefing": safe_briefing, "safety_check_passed": False}
