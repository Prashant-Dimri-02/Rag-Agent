# app/api/v1/support.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.dependencies import get_db
from app.services.support_service import take_over_conversation, agent_reply
from app.services.websocket_manager import WebSocketManager


router = APIRouter()



@router.post("/takeover")
async def take_over_chat(
    sess_id: int,
    agent_id: int,
    db: Session = Depends(get_db)
):
    try:
        
        session = take_over_conversation(db, sess_id, agent_id)

        # Notify user that agent joined
        await WebSocketManager.send_to_user(
            sess_id,  # assuming sess_id maps to websocket user key
            {
                "type": "agent_joined",
                "message": "A support agent has joined the chat.",
                "agent_id": agent_id
            }
        )

        return {
            "success": True,
            "message": "Conversation assigned successfully",
            "sess_id": session.sess_id,
            "assigned_agent_id": session.assigned_agent_id,
            "status": session.status
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reply/{user_id}")
def reply(user_id: int, agent_id: int, message: str, db: Session = Depends(get_db)):
    chat = agent_reply(db, user_id, agent_id, message)
    return {"id": chat.id, "ok": True}