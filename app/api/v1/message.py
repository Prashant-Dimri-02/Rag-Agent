from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.models.chat import Chat

router = APIRouter()


@router.get("/messages/{sess_id}")
def get_messages(sess_id: int, db: Session = Depends(get_db)):
    chats = (
        db.query(Chat)
        .filter(Chat.sess_id == sess_id)
        .order_by(Chat.created_at.asc())
        .all()
    )

    return [
        {
            "role": chat.sender,   # user / bot / agent
            "content": chat.message,
            "needs_human": chat.needs_human
        }
        for chat in chats
    ]

