from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, unique=True, index=True)
    briefing_time = Column(String, default="08:00")
    timezone = Column(String, default="UTC")

class BriefingLog(Base):
    __tablename__ = "briefing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    safety_passed = Column(Boolean, default=True)
