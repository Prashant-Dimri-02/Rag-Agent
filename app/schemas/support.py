# app/schemas/support.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime




class SupportAlertOut(BaseModel):
    id: int
    chat_id: Optional[int]
    user_id: int
    resolved: bool
    created_at: datetime


    class Config:
        orm_mode = True