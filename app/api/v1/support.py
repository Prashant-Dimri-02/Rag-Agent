# app/api/v1/support.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.dependencies import get_db
from app.services.support_service import list_pending_alerts, take_over_chat, agent_reply
from app.schemas.support import SupportAlertOut


router = APIRouter()




@router.get("/pending", response_model=List[SupportAlertOut])
def pending_alerts(db: Session = Depends(get_db)):
    alerts = list_pending_alerts(db)
    return alerts




@router.post("/takeover/{user_id}")
def takeover(user_id: int, agent_id: int, db: Session = Depends(get_db)):
    take_over_chat(db, user_id, agent_id)
    return {"ok": True}




@router.post("/reply/{user_id}")
def reply(user_id: int, agent_id: int, message: str, db: Session = Depends(get_db)):
    chat = agent_reply(db, user_id, agent_id, message)
    return {"id": chat.id, "ok": True}