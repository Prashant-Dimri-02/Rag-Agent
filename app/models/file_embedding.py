from sqlalchemy import Column, Float, Integer, ForeignKey, DateTime, String, Text
from pgvector.sqlalchemy import Vector
from sqlalchemy.sql import func
from app.db.base import Base


class FileEmbedding(Base):
    __tablename__ = "file_embeddings"

    id = Column(Integer, primary_key=True, index=True)

    file_id = Column(Integer, ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=True)
    text_content = Column(Text, nullable=True)

    # OpenAI embedding vector (e.g. 1536 dims for text-embedding-3-small)
    
    embedding = Column(Vector(1536), nullable=False)
    source_type = Column(String(50), nullable=True, default="file")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
