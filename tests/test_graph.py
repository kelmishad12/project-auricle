"""
Tests for LangGraph logic.
"""
# pylint: disable=duplicate-code
import pytest

# pylint: disable=import-error,no-name-in-module
from src.adapters.localmock import MockCalendarAdapter, MockMailAdapter
from src.core.graph import AuricleGraph


@pytest.mark.asyncio
async def test_graph_initializes():
    """Verify AuricleGraph initializes correctly."""
    mail = MockMailAdapter()
    cal = MockCalendarAdapter()
    graph = AuricleGraph(mail_provider=mail, cal_provider=cal)
    assert graph is not None


@pytest.mark.asyncio
async def test_graph_invoke_with_mocks():
    """Verify AuricleGraph execution with mock providers."""
    mail = MockMailAdapter()
    cal = MockCalendarAdapter()
    graph = AuricleGraph(mail_provider=mail, cal_provider=cal)

    initial_state = {
        "messages": [],
        "email_summaries": [],
        "calendar_events": [],
        "briefing": "",
        "safety_check_passed": False
    }

    result = await graph.ainvoke(initial_state)

    assert "email_summaries" in result
    assert "calendar_events" in result
    assert result["safety_check_passed"] is True
