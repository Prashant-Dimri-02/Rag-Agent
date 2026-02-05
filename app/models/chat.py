# app/models/chat.py
from sqlalchemy import Column, Integer, Text, DateTime, Boolean, Enum as SAEnum, BigInteger
from sqlalchemy.sql import func
from app.db.base import Base




class Chat(Base):
    __tablename__ = "chats"


    id = Column(Integer, primary_key=True)


    # the owner of the conversation (user who started the chat)
    sess_id = Column(BigInteger, nullable=True, index=True)


    # who sent this message: 'user' | 'bot' | 'agent'
    sender = Column(
    SAEnum("user", "bot", "agent", name="chat_sender"),
    nullable=False,
    server_default="user",
    )


    # message content
    message = Column(Text, nullable=False)


    # takeover state for the conversation (set on messages rows as well)
    needs_human = Column(Boolean, default=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())