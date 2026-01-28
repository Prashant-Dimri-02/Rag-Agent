from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.website_kb import WebsiteKBRequest, WebsiteKBResponse
from app.services.website_kb_service import WebsiteKBService

router = APIRouter()


@router.post("/knowledge-base/url", response_model=WebsiteKBResponse)
def add_website_to_knowledge_base(
    payload: WebsiteKBRequest,
    db: Session = Depends(get_db),
):
    try:
        service = WebsiteKBService(db)
        result = service.add_website(str(payload.url))
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
