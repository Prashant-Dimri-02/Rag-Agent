from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db
from typing import Optional
from datetime import datetime
from app.services.chat_service import get_all_chat_summaries
from app.schemas.chat import ChatSummaryListResponse
router = APIRouter()


@router.get(
    "/chat/summary",
    response_model=ChatSummaryListResponse
)
def chat_summary(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return get_all_chat_summaries(
        db,
        skip=skip,
        limit=limit,
        type=type,
        session_id=session_id,
        start_date=start_date,
        end_date=end_date,
    )
