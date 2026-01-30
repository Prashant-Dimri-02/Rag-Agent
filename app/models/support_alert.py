# app/models/support_alert.py
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.sql import func
from app.db.base import Base




class SupportAlert(Base):
    __tablename__ = "support_alerts"


    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=True)
    user_id = Column(BigInteger, nullable=True)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())