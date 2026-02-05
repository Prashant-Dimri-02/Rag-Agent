# app/schemas/auth.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str]
    user_id: int
    user_name: Optional[str]

class TokenPayload(BaseModel):
    sub: str
