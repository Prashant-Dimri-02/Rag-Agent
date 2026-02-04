# app/api/v1/support_alert.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.models.session import ConversationSession

router = APIRouter()


@router.get("/support-alerts")
def get_unassigned_sessions(db: Session = Depends(get_db)):

    sessions = (
        db.query(ConversationSession)
        .filter(
            ConversationSession.assigned_agent_id.is_(None)
        )
        .order_by(ConversationSession.created_at.desc())
        .all()
    )

    return [
        {
            "session_id": session.id,
            "sess_id": session.sess_id,
            "created_at": session.created_at,
        }
        for session in sessions
    ]


