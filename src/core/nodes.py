"""
LangGraph node implementations.
"""
from langchain_core.runnables import RunnableConfig

from src.core.state import AgentState
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


async def synthesize_briefing(state: AgentState, config: RunnableConfig):
    """Synthesize the final briefing contextually."""
    gemini = GeminiService()

    revision_count = state.get('revision_count', 0)
    critic_feedback = state.get('critic_feedback', '')

    prompt = (
        "You are an AI Executive Assistant. Create a concise, professional daily briefing "
        "using the following data. Keep it under 5 minutes when spoken.\n\n"
        f"Emails:\n{chr(10).join(state.get('email_summaries', []))}\n\n"
        f"Calendar:\n{chr(10).join(state.get('calendar_events', []))}\n"
    )

    if revision_count > 0 and critic_feedback:
        prompt += (
            f"\n\nCRITIC FEEDBACK FROM PREVIOUS DRAFT:\n{critic_feedback}\n\n"
            "Please revise your briefing to explicitly address and fix the issues mentioned above."
        )

    briefing = gemini.generate_content(prompt)
    return {"briefing": briefing}

# pylint: disable=unused-argument


async def reflexion_loop(state: AgentState, config: RunnableConfig):
    """Enforce strict Safety/Privacy protocols via a Reflexion loop."""
    gemini = GeminiService()

    revision_count = state.get('revision_count', 0)
    analysis = gemini.analyze_context(state.get('briefing', ''))

    safety_passed = analysis.get("safety_passed", False)
    reasoning = analysis.get("reasoning", "")

    if not safety_passed:
        print(f"[Reflexion] Safety Warning [{revision_count + 1}/3]: {reasoning}")
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

# pylint: disable=unused-argument


async def generate_audio_script(state: AgentState, config: RunnableConfig):
    """Rewrite the final briefing into a natural, spoken script for TTS."""
    gemini = GeminiService()

    prompt = (
        "You are an expert voice scriptwriter. Take the following daily briefing "
        "and rewrite it to be read out loud naturally by a text-to-speech engine. "
        "Remove all markdown formatting, bullet points, asterisks, and special characters.\n"
        "Ensure the flow is conversational, warm, and professional, "
        "as if spoken by a human assistant.\n"
        "Write out numbers or times plainly (e.g., 'three thirty PM' instead of '3:30').\n\n"
        f"Original Briefing:\n{state.get('briefing', '')}"
    )

    spoken = gemini.generate_content(prompt)
    return {"spoken_briefing": spoken}
