from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_db
from app.schemas.knowledge_base import (
    KnowledgeBaseQARequest,
    KnowledgeBaseQAResponse,
)
from app.services.knowledge_base_service import KnowledgeBaseService

router = APIRouter()


# =========================================================
# ADD QA
# =========================================================
@router.post("/knowledge-base/qa", response_model=KnowledgeBaseQAResponse)
def add_qa_to_knowledge_base(
    payload: KnowledgeBaseQARequest,
    db: Session = Depends(get_db),
):
    try:
        service = KnowledgeBaseService(db)
        result = service.add_qa(
            question=payload.question,
            answer=payload.answer,
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# GET KNOWLEDGE BASE (PAGINATION + FILTER)
# =========================================================
@router.get("/knowledge-base")
def get_knowledge_base(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    source_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        service = KnowledgeBaseService(db)

        return service.get_knowledge_base(
            page=page,
            page_size=page_size,
            source_type=source_type,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
