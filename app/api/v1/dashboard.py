from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    service = DashboardService(db)
    return service.get_all_info()
