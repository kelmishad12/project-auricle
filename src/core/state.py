"""
State definition for LangGraph.
"""
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """The state of the agent."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    email_summaries: list[str]
    calendar_events: list[str]
    briefing: str
    spoken_briefing: str
    safety_check_passed: bool
    revision_count: int
    critic_feedback: str
