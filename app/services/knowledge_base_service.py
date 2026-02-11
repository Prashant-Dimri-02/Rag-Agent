from typing import Optional
import random
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
    # ADD QA
    # =========================================================
    def add_qa(self, question: str, answer: str) -> dict:
        question = question.strip()
        answer = answer.strip()

        if not question or not answer:
            raise ValueError("Both question and answer are required")

        combined_text = f"Question: {question}\nAnswer: {answer}"

        embedding_vector, tokens_used = self.embedding_service.create_embedding(combined_text)

        if not embedding_vector:
            raise RuntimeError("Failed to create embedding")

        generated_qa_id = random.getrandbits(63)

        db_embedding = FileEmbedding(
            embedding=embedding_vector,
            text_content=combined_text,
            source_type="kb_qa",
            qa_id=generated_qa_id,
            embedding_tokens=tokens_used,
        )

        self.db.add(db_embedding)
        self.db.commit()
        self.db.refresh(db_embedding)

        return {
            "id": db_embedding.id,
            "qa_id": generated_qa_id,
            "question": question,
            "answer": answer,
        }

    # =========================================================
    # GET KNOWLEDGE BASE
    # =========================================================
    def get_knowledge_base(
        self,
        page: int = 1,
        page_size: int = 10,
        source_type: Optional[str] = None,
    ):
        query = self.db.query(FileEmbedding)

        if source_type:
            query = query.filter(FileEmbedding.source_type == source_type)

        # =========================================================
        # KB_QA
        # =========================================================
        if source_type == "kb_qa":

            total = (
                self.db.query(FileEmbedding.qa_id)
                .filter(FileEmbedding.qa_id != None)
                .distinct()
                .count()
            )

            embeddings = (
                self.db.query(FileEmbedding)
                .filter(FileEmbedding.qa_id != None)
                .order_by(FileEmbedding.qa_id, desc(FileEmbedding.created_at))
                .distinct(FileEmbedding.qa_id)
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            results = [
                {
                    "qa_id": emb.qa_id,
                    "text_content": emb.text_content,
                    "created_at": emb.created_at,
                    "source_type": "qa"
                }
                for emb in embeddings
            ]

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": results
            }

        # =========================================================
        # KB_URL (FIXED — no regex)
        # =========================================================
        if source_type == "kb_url":

            total = (
                self.db.query(FileEmbedding.url_id)
                .filter(FileEmbedding.url_id != None)
                .distinct()
                .count()
            )

            embeddings = (
                self.db.query(FileEmbedding)
                .filter(FileEmbedding.source_type == "kb_url")
                .filter(FileEmbedding.source_url != None)  # ✅ only first chunk rows
                .order_by(desc(FileEmbedding.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            results = [
                {
                    "url_id": emb.url_id,
                    "source_url": emb.source_url,
                    "created_at": emb.created_at,
                    "source_type": "url"
                }
                for emb in embeddings
            ]

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": results
            }

        # =========================================================
        # FILE
        # =========================================================
        if source_type == "file":

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
                    "created_at": emb.created_at
                }

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

                results.append(item)

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": results
            }
