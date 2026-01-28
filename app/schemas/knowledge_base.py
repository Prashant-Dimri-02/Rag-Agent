from pydantic import BaseModel


class KnowledgeBaseQARequest(BaseModel):
    question: str
    answer: str


class KnowledgeBaseQAResponse(BaseModel):
    id: int
    question: str
    answer: str
