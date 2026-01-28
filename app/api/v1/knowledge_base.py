from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.knowledge_base import (
    KnowledgeBaseQARequest,
    KnowledgeBaseQAResponse,
)
from app.services.knowledge_base_service import KnowledgeBaseService

router = APIRouter()


@router.post("/knowledge-base/qa", response_model=KnowledgeBaseQAResponse)
def add_qa_to_knowledge_base(
    payload: KnowledgeBaseQARequest,
    db: Session = Depends(get_db),
):
    try:
        service = KnowledgeBaseService(db)
        result = service.add_qa(payload.question, payload.answer)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
