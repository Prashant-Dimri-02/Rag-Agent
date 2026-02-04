# app/services/support_service.py
from sqlalchemy.orm import Session
from typing import List
from app.models.chat import Chat
from app.services.websocket_manager import WebSocketManager
from app.models.session import ConversationSession
from datetime import datetime



def take_over_conversation(db: Session, sess_id: int, agent_id: int):

    session = db.query(ConversationSession)\
        .filter(ConversationSession.sess_id == sess_id)\
        .with_for_update()\
        .first()

    if not session:
        raise Exception("Conversation session not found")

    if session.status == "agent_active":
        raise Exception("Conversation already assigned to another agent")

    session.status = "agent_active"
    session.assigned_agent_id = agent_id
    session.assigned_at = datetime.utcnow()

    db.commit()
    db.refresh(session)

    return session

def agent_reply(db: Session, user_id: int, agent_id: int, message: str):
    # create agent message row
    chat = Chat(user_id=user_id, sender="agent", message=message, taken_over=True, taken_over_by=agent_id)
    db.add(chat)
    db.commit()
    db.refresh(chat)


    # send to user (async but fire-and-forget)
    payload = {"type": "agent_message", "message": message, "sender": "agent", "user_id": user_id}
    # call async manager
    import asyncio
    asyncio.create_task(WebSocketManager.send_to_user(user_id, payload))


    return chat