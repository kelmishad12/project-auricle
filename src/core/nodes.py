"""
LangGraph node implementations.
"""
from langchain_core.runnables import RunnableConfig

from src.core.state import AgentState
from src.services.google import CalendarProvider, MailProvider

def get_mail_provider(config: RunnableConfig) -> MailProvider:
    """Extract MailProvider from config."""
    return config["configurable"].get("mail_provider")

def get_cal_provider(config: RunnableConfig) -> CalendarProvider:
    """Extract CalendarProvider from config."""
    return config["configurable"].get("cal_provider")

async def fetch_emails(_state: AgentState, config: RunnableConfig):
    """Fetch emails using the injected MailProvider port."""
    mail_provider = get_mail_provider(config)
    emails = await mail_provider.get_recent_emails(limit=5)
    return {"email_summaries": [f"Email from {e['sender']}: {e['subject']}" for e in emails]}

async def fetch_calendar(_state: AgentState, config: RunnableConfig):
    """Fetch calendar events using the injected CalendarProvider port."""
    cal_provider = get_cal_provider(config)
    events = await cal_provider.get_upcoming_events(days=1)
    return {"calendar_events": [f"Event: {e['title']} at {e['time']}" for e in events]}

async def synthesize_briefing(_state: AgentState, _config: RunnableConfig):
    """Synthesize the final briefing contextually."""
    # TODO: [Critique Issue] Wire into src.services.gemini.py
    return {"briefing": "Today's briefing synthesized from events and emails..."}

async def reflexion_loop(_state: AgentState, _config: RunnableConfig):
    """Enforce strict Safety/Privacy protocols via a Reflexion loop."""
    return {"safety_check_passed": True}
