"""
Tests for LangGraph logic.
"""
# pylint: disable=duplicate-code
from unittest.mock import MagicMock, patch

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
@patch("src.core.nodes.GeminiService")
async def test_graph_invoke_with_mocks(mock_gemini_class):
    """Verify AuricleGraph execution with mock providers."""
    mock_gemini = MagicMock()
    mock_gemini.generate_content.return_value = "Safe mocked briefing"
    mock_gemini.chat_with_context.return_value = "Safe mocked briefing"
    mock_gemini.create_cached_context.return_value = "mock-cache-id"
    mock_gemini.analyze_context.return_value = {
        "safety_passed": True,
        "reasoning": "Looks good"
    }
    mock_gemini_class.return_value = mock_gemini

    mail = MockMailAdapter()
    cal = MockCalendarAdapter()
    graph = AuricleGraph(mail_provider=mail, cal_provider=cal)

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

    result = await graph.ainvoke(initial_state)

    assert "email_summaries" in result
    assert "calendar_events" in result
    assert result["safety_check_passed"] is True


@pytest.mark.asyncio
@patch("src.core.nodes.GeminiService")
async def test_reflexion_loop_safe_mode_fallback(mock_gemini_class):
    """Verify that failing safety checks 3 times triggers Safe Mode fallback."""
    mock_gemini = MagicMock()
    mock_gemini.generate_content.return_value = "Unsafe briefing"
    mock_gemini.chat_with_context.return_value = "Unsafe briefing"
    mock_gemini.create_cached_context.return_value = "mock-cache-id"
    mock_gemini.analyze_context.return_value = {
        "safety_passed": False,
        "reasoning": "Contains PII"
    }
    mock_gemini_class.return_value = mock_gemini

    mail = MockMailAdapter()
    cal = MockCalendarAdapter()
    graph = AuricleGraph(mail_provider=mail, cal_provider=cal)

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

    result = await graph.ainvoke(initial_state)

    assert result["safety_check_passed"] is False
    assert "Good morning. I encountered multiple safety" in result["briefing"]
