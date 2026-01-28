from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.services.qa_service import QAService

router = APIRouter()


@router.post("/qa")
def ask_question(payload: dict, db: Session = Depends(get_db)):
    try:
        service = QAService(db)
        answer = service.ask(payload["question"])
        return {"answer": answer}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
