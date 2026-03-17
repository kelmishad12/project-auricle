"""
LangGraph node implementations.
"""
import os
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
async def synthesize_briefing(state: AgentState, config: RunnableConfig):
    """Synthesize the final briefing contextually using Memory Tiering."""
    gemini = GeminiService()

    revision_count = state.get('revision_count', 0)
    critic_feedback = state.get('critic_feedback', '')

    # 1. Ephemeral Memory: Read System Instruction (User Profile)
    profile_path = "/Users/kelmishad/project-auricle/scripts/system_profile_sample.txt"
    with open(profile_path, "r", encoding="utf-8") as f:
        user_profile_text = f.read()

    # The Gemini Caching API strictly requires >= 1024 tokens.
    # We apply "Semantic Padding" (ADRs, schemas, Knowledge Base) as requested,
    # repeating a core architectural philosophy to ensure we breach the threshold securely.
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

    # Extract version for observability
    # Extract version for observability
    version_line = next(
        (line for line in user_profile_text.splitlines() if "[ID:" in line),
        ""
    )
    if "[ID:" in version_line:
        user_profile_version = version_line.split(
            "[ID:")[1].split("]")[0].strip()
    else:
        user_profile_version = "UNKNOWN"

    # 2. Working Memory: Active Gmail/Calendar Data
    emails = chr(10).join(state.get('email_summaries', []))
    calendar = chr(10).join(state.get('calendar_events', []))
    dynamic_data = f"Emails:\n{emails}\n\nCalendar:\n{calendar}"

    # 3. Permanent Memory: Postgres cache_id mapping
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

        cache_id = settings.cache_id

        if cache_id and not gemini.validate_cache(cache_id):
            print(f"DEBUG nodes.py: Cache {cache_id} is invalid/expired. Creating a new one.")
            cache_id = None

        # If we have no cache_id, we MUST create one and save it permanently.
        if not cache_id:
            system_instruction = (
                "You are an AI Executive Assistant. Create a concise, professional "
                "daily briefing using the following data. Keep it under 5 minutes "
                "when spoken."
            )

            # Create a new cache that will expire based on TTL, but we save the id permanently
            new_cache_id = gemini.create_cached_context(
                system_instruction=system_instruction,
                user_profile_text=user_profile_text,
                dynamic_data=dynamic_data
            )

            if new_cache_id:
                print(f"DEBUG nodes.py: Created new_cache_id={new_cache_id}")
                settings.cache_id = new_cache_id
                db.commit()
                cache_id = new_cache_id
            else:
                print("DEBUG nodes.py: create_cached_context returned None")

    finally:
        db.close()

    # Query the cache
    prompt = "Please draft today's briefing."
    if revision_count > 0 and critic_feedback:
        prompt += (
            f"\n\nCRITIC FEEDBACK FROM PREVIOUS DRAFT:\n{critic_feedback}\n\n"
            "Please revise your briefing to explicitly address and fix the issues mentioned above."
        )

    if cache_id:
        briefing = gemini.chat_with_context(cache_id, prompt)
    else:
        fallback_prompt = (
            f"{system_instruction}\n\n{user_profile_text}\n\n"
            f"{dynamic_data}\n\n{prompt}"
        )
        briefing = gemini.generate_content(fallback_prompt)

    return {
        "briefing": briefing,
        "user_profile_version": user_profile_version
    }

# pylint: disable=unused-argument


async def reflexion_loop(state: AgentState, config: RunnableConfig):
    """Enforce strict Safety/Privacy protocols via a Reflexion loop."""
    gemini = GeminiService()

    revision_count = state.get('revision_count', 0)
    analysis = gemini.analyze_context(state)

    safety_passed = analysis.get("safety_passed", False)
    reasoning = analysis.get("reasoning", "")

    if not safety_passed:
        print(
            f"[Reflexion] Safety Warning [{revision_count + 1}/3]: {reasoning}")
        return {
            "safety_check_passed": False,
            "revision_count": revision_count + 1,
            "critic_feedback": reasoning
        }

    return {
        "safety_check_passed": True,
        "critic_feedback": ""
    }

# pylint: disable=unused-argument


async def safe_mode_fallback(_state: AgentState, config: RunnableConfig):
    """Fallback node if the reflexion loop fails 3 times."""
    print("[Safe Mode] Agent failed safety checks too many times. Falling back to safe output.")
    safe_briefing = (
        "Good morning. I encountered multiple safety or formatting errors while generating "
        "your briefing today. Please check your email and calendar manually for updates."
    )
    return {"briefing": safe_briefing, "safety_check_passed": False}
