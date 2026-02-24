"""
Tools definition for the LangGraph agent.
"""
from langchain_core.tools import tool

@tool
def get_unread_emails(limit: int = 5):
    """Fetch unread emails from the user's inbox."""
    # Placeholder for actual API call or injected service use
    return f"Retrieved {limit} unread emails."

def get_llm_tools():
    """Return all tools that the Agent can invoke dynamically."""
    return [get_unread_emails]
