"""
LangGraph orchestration for the Project Auricle.
"""


from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from src.core.nodes import (
    supervisor,
    fetch_calendar,
    fetch_emails,
    reflexion_loop,
    synthesize_briefing,
    safe_mode_fallback
)
from src.core.state import AgentState
from src.services.google import CalendarProvider, MailProvider


class AuricleGraph:
    """Supervisor and Node definitions. Pure LangGraph logic."""

    def __init__(self, mail_provider: MailProvider,
                 cal_provider: CalendarProvider, checkpointer=None):
        # TODO: [Critique Issue] Add overarching ApplicationContext/Dependency
        # Injector
        self.mail_provider = mail_provider
        self.cal_provider = cal_provider

        # Build the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("supervisor", supervisor)
        workflow.add_node("fetch_emails", fetch_emails)
        workflow.add_node("fetch_calendar", fetch_calendar)
        workflow.add_node("synthesize_briefing", synthesize_briefing)
        workflow.add_node("reflexion_loop", reflexion_loop)
        workflow.add_node("safe_mode_fallback", safe_mode_fallback)

        # Add edges Flow
        workflow.set_entry_point("supervisor")

        # Fan-out: supervisor branches to both in parallel
        workflow.add_conditional_edges(
            "supervisor",
            lambda state: ["fetch_emails", "fetch_calendar"],
            ["fetch_emails", "fetch_calendar"]
        )

        # Fan-in: wait for both before synthesis
        workflow.add_edge("fetch_emails", "synthesize_briefing")
        workflow.add_edge("fetch_calendar", "synthesize_briefing")
        workflow.add_edge("synthesize_briefing", "reflexion_loop")
        # Self-correction loop conditional edge

        def route_reflexion(state):
            if state.get("safety_check_passed"):
                return END
            if state.get("revision_count", 0) < 3:
                return "synthesize_briefing"
            return "safe_mode_fallback"

        workflow.add_conditional_edges(
            "reflexion_loop",
            route_reflexion,
            {
                END: END,
                "synthesize_briefing": "synthesize_briefing",
                "safe_mode_fallback": "safe_mode_fallback"
            }
        )
        workflow.add_edge("safe_mode_fallback", END)

        if checkpointer is None:
            checkpointer = MemorySaver()

        self.app = workflow.compile(checkpointer=checkpointer)

    async def ainvoke(self, input_state: dict, thread_id: str = "default"):
        """Run the orchestrated graph asynchronously with injected dependencies."""
        config = RunnableConfig(
            configurable={
                "mail_provider": self.mail_provider,
                "cal_provider": self.cal_provider,
                "thread_id": thread_id
            }
        )
        return await self.app.ainvoke(input_state, config=config)
