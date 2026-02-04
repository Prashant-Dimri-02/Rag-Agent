# app/schemas/chat.py
from pydantic import BaseModel
from typing import List, Optional
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
        
        
        
class ChatSummaryResponse(BaseModel):
    sess_id: int
    session_id: str
    start_time: datetime
    duration_seconds: int
    type: str
    status: str

    class Config:
        from_attributes = True
        

class ChatSummaryListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: List[ChatSummaryResponse]