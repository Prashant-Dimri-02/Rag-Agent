# app/schemas/chat.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime




class MessageCreate(BaseModel):
    user_id: int
    message: str




class MessageOut(BaseModel):
    id: int
    user_id: int
    sender: str
    message: str
    needs_human: bool
    taken_over: bool
    taken_over_by: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True