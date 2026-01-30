from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.models.chat import Chat

router = APIRouter()


@router.get("/messages{user_id}")
def get_messages(user_id: int, db: Session = Depends(get_db)):
    chats = (
        db.query(Chat)
        .filter(Chat.user_id == user_id)
        .order_by(Chat.created_at.asc())
        .all()
    )

    return [
        {"role": "user", "content": chat.question}
        for chat in chats
        for _ in (0,)
    ] + [
        {"role": "assistant", "content": chat.answer}
        for chat in chats
        for _ in (0,)
    ]
