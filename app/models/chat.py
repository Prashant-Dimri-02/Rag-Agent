# app/models/chat.py

from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())