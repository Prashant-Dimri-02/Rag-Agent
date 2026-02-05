from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.models.chat import Chat
from typing import Optional, Dict
from datetime import datetime



def get_all_chat_summaries(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    type: Optional[str] = None,
    session_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict:

    base_query = (
        select(
            Chat.sess_id,
            func.min(Chat.created_at).label("start_time"),
            func.max(Chat.created_at).label("end_time"),
            func.max(
                case(
                    (Chat.needs_human == True, 1),
                    else_=0
                )
            ).label("needs_human_flag")
        )
        .where(Chat.sess_id.isnot(None))
        .group_by(Chat.sess_id)
    )

    subquery = base_query.subquery()
    query = select(subquery)

    # ----------------------------
    # Filters
    # ----------------------------

    # ✅ Session ID filter (supports both formats)
    if session_id:
        if session_id.startswith("SESS-"):
            session_id = session_id.replace("SESS-", "")

        try:
            query = query.where(subquery.c.sess_id == int(session_id))
        except ValueError:
            # invalid session_id format
            return {
                "total": 0,
                "skip": skip,
                "limit": limit,
                "data": []
            }

    # Type filter
    if type:
        if type.lower() == "ai":
            query = query.where(subquery.c.needs_human_flag == 0)
        elif type.lower() == "human + ai":
            query = query.where(subquery.c.needs_human_flag == 1)

    # Date range filter (based on start_time)
    if start_date:
        query = query.where(subquery.c.start_time >= start_date)

    if end_date:
        query = query.where(subquery.c.start_time <= end_date)

    # ----------------------------
    # Total Count
    # ----------------------------

    count_query = select(func.count()).select_from(query.subquery())
    total_result = db.execute(count_query)
    total = total_result.scalar()

    # ----------------------------
    # Pagination
    # ----------------------------

    query = query.offset(skip).limit(limit)
    result = db.execute(query)
    rows = result.all()

    summaries = []

    for row in rows:
        duration = int((row.end_time - row.start_time).total_seconds())
        chat_type = "human + ai" if row.needs_human_flag == 1 else "ai"

        summaries.append({
            "sess_id": row.sess_id,
            "session_id": f"SESS-{row.sess_id}",
            "start_time": row.start_time,
            "duration_seconds": duration,
            "type": chat_type,
            "status": "completed"
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": summaries
    }