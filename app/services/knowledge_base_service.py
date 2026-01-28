from sqlalchemy.orm import Session
from app.models.file_embedding import FileEmbedding
from app.services.embedding_service import EmbeddingService


class KnowledgeBaseService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()

    def add_qa(self, question: str, answer: str) -> dict:
        question = question.strip()
        answer = answer.strip()

        if not question or not answer:
            raise ValueError("Both question and answer are required")

        # Combine for embedding (IMPORTANT)
        combined_text = f"Question: {question}\nAnswer: {answer}"

        # 1) Create embedding
        embedding_vector = self.embedding_service.create_embedding(combined_text)

        if not embedding_vector:
            raise RuntimeError("Failed to create embedding")

        # 2) Store in embeddings table (file_id = NULL)
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
