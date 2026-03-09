"""
Database models for Project Auricle.

NOTE ON STATE PERSISTENCE:
These SQLAlchemy models are used for long-term application data (e.g., user preferences
and historical logs of generated briefings). 
They do NOT store the LangGraph AgentState. LangGraph's state persistence (which tracks
the mid-execution memory of the underlying agent) is handled automatically by 
`langgraph.checkpoint.postgres` using its own hidden Postgres tables managed in `src/core/graph.py`.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserSettings(Base):
    """Model representing user settings."""
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, unique=True, index=True)
    briefing_time = Column(String, default="08:00")
    timezone = Column(String, default="UTC")

class BriefingLog(Base):
    """Model representing a generated briefing log."""
    __tablename__ = "briefing_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    safety_passed = Column(Boolean, default=True)
