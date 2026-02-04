from pydantic import BaseModel
from typing import Optional, List

class KnowledgeBaseQARequest(BaseModel):
    question: str
    answer: str


class KnowledgeBaseQAResponse(BaseModel):
    id: int
    question: str
    answer: str


class KnowledgeBaseItem(BaseModel):
    id: int
    source_type: Optional[str]

    # File fields
    file_id: Optional[int] = None
    original_filename: Optional[str] = None
    stored_filename: Optional[str] = None
    file_path: Optional[str] = None
    content_type: Optional[str] = None

    # Text fields
    text_content: Optional[str] = None
    source_url: Optional[str] = None

    class Config:
        orm_mode = True


class KnowledgeBaseResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[KnowledgeBaseItem]