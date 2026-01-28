import os
import uuid
import shutil
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.uploaded_file import UploadedFile
from app.models.file_embedding import FileEmbedding
from app.services.embedding_service import EmbeddingService
from app.services.file_text_extractor import extract_text_from_file
from app.services.website_kb_service import WebsiteKBService

UPLOAD_DIR = "uploads"


class BuildService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.wks=WebsiteKBService(db)

    def upload_file(self, file: UploadFile):
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        ext = os.path.splitext(file.filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        # save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # extract text
        text_content = extract_text_from_file(file_path, file.content_type)

        # save file metadata
        db_file = UploadedFile(
            original_filename=file.filename,
            stored_filename=unique_name,
            file_path=file_path,
            content_type=file.content_type,
            text_content=text_content,
            source_type="file",
        )

        self.db.add(db_file)
        self.db.commit()
        self.db.refresh(db_file)

        # create embeddings (CHUNKED)
        chunks = self.wks._chunk_text(text_content)

        for chunk in chunks:
            embedding_vector = self.embedding_service.create_embedding(chunk)

            if not embedding_vector:
                continue

            db_embedding = FileEmbedding(
                file_id=db_file.id,
                embedding=embedding_vector,
                raw_text=chunk,
                source_type="file",
            )

            self.db.add(db_embedding)

        self.db.commit()

        return db_file
