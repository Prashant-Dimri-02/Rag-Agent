# app/services/support_service.py
from sqlalchemy.orm import Session
from typing import List
from app.models.chat import Chat
from app.models.support_alert import SupportAlert
from app.services.websocket_manager import WebSocketManager




def list_pending_alerts(db: Session) -> List[SupportAlert]:
    return db.query(SupportAlert).filter(SupportAlert.resolved == False).all()




def create_alert_for_chat(db: Session, chat_id: int, user_id: int) -> SupportAlert:
    alert = SupportAlert(chat_id=chat_id, user_id=user_id)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    # notify agents in real-time
    WebSocketManager.broadcast_to_agents({"type": "NEW_ALERT", "user_id": user_id, "chat_id": chat_id})
    return alert




def take_over_chat(db: Session, user_id: int, agent_id: int):
    # mark all chat rows for this user as taken_over
    db.query(Chat).filter(Chat.user_id == user_id).update({
    "taken_over": True,
    "taken_over_by": agent_id,
    "needs_human": False,
    })
    # resolve any alerts
    db.query(SupportAlert).filter(SupportAlert.user_id == user_id, SupportAlert.resolved == False).update({"resolved": True})
    db.commit()




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