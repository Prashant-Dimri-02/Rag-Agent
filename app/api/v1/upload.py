# app/api/routes/upload.py

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.core.dependencies import get_db
from app.services.build_service import BuildService

router = APIRouter()


@router.post("/upload-file")
def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    service = BuildService(db)
    saved_file = service.upload_file(file)

    return {
        "message": "File uploaded successfully",
        "file_id": saved_file.id,
        "original_filename": saved_file.original_filename,
        "stored_filename": saved_file.stored_filename,
        "file_path": saved_file.file_path,
        "content_type": saved_file.content_type,
        "uploaded_at": saved_file.uploaded_at,
    }
