from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger
from sqlalchemy.sql import func
from app.db.base import Base

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, index=True)
    sess_id = Column(BigInteger, index=True, nullable=False)

    status = Column(String, default="bot_active")  
    # bot_active | agent_active | closed

    assigned_agent_id = Column(Integer, nullable=True)

    assigned_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
