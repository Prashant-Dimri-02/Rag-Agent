import re
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.file_embedding import FileEmbedding
from app.models.uploaded_file import UploadedFile
from app.services.embedding_service import EmbeddingService


class KnowledgeBaseService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()

    # =========================================================
    # ADD QA TO KNOWLEDGE BASE
    # =========================================================
    def add_qa(self, question: str, answer: str) -> dict:
        question = question.strip()
        answer = answer.strip()

        if not question or not answer:
            raise ValueError("Both question and answer are required")

        combined_text = f"Question: {question}\nAnswer: {answer}"

        # Create embedding
        embedding_vector = self.embedding_service.create_embedding(combined_text)

        if not embedding_vector:
            raise RuntimeError("Failed to create embedding")

        db_embedding = FileEmbedding(
            file_id=None,
            embedding=embedding_vector,
            text_content=combined_text,
            source_type="kb_qa",
        )

        self.db.add(db_embedding)
        self.db.commit()
        self.db.refresh(db_embedding)

        return {
            "id": db_embedding.id,
            "question": question,
            "answer": answer,
        }

    # =========================================================
    # GET KNOWLEDGE BASE WITH PAGINATION + FILTERS
    # =========================================================
    def get_knowledge_base(
        self,
        page: int = 1,
        page_size: int = 10,
        source_type: Optional[str] = None,
    ):
        query = self.db.query(FileEmbedding)

        # Optional filter
        if source_type:
            query = query.filter(FileEmbedding.source_type == source_type)

        total = query.count()

        embeddings = (
            query.order_by(desc(FileEmbedding.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        results = []

        for emb in embeddings:
            item = {
                "id": emb.id,
                "source_type": emb.source_type,
            }

            # ================= FILE =================
            if emb.source_type == "file":
                file = (
                    self.db.query(UploadedFile)
                    .filter(UploadedFile.id == emb.file_id)
                    .first()
                )

                if file:
                    item.update({
                        "file_id": file.id,
                        "original_filename": file.original_filename,
                        "stored_filename": file.stored_filename,
                        "file_path": file.file_path,
                        "content_type": file.content_type,
                        "uploaded_at": file.uploaded_at,
                    })

            # ================= KB_QA =================
            elif emb.source_type == "kb_qa":
                item.update({
                    "text_content": emb.text_content,
                    "source_type": "qa"
                })

            # ================= KB_URL =================
            elif emb.source_type == "kb_url":
                text = emb.text_content or ""

                url_match = re.search(
                    r"Source URL:\s*(https?://\S+)",
                    text
                )

                source_url = url_match.group(1) if url_match else None

                cleaned_text = re.sub(
                    r"Source URL:\s*https?://\S+\s*",
                    "",
                    text
                )

                item.update({
                    "source_url": source_url,
                    "text_content": cleaned_text.strip(),
                    "source_type": "url"
                })

            results.append(item)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": results
        }
