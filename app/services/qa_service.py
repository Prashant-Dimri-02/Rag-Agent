from sqlalchemy.orm import Session
from openai import OpenAI
import os

from app.models.chat import Chat
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import search_similar_chunks


class QAService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def ask(self, question: str) -> str:
        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty")

        # 1️⃣ Embed question
        query_embedding = self.embedding_service.create_embedding(question)

        # 2️⃣ Search knowledge base
        kb_chunks = search_similar_chunks(
            self.db,
            query_embedding,
            top_k=5,
        )

        # 3️⃣ Load previous chats (memory)
        previous_chats = (
            self.db.query(Chat)
            .order_by(Chat.created_at.asc())
            .all()
        )

        # 4️⃣ Build prompt
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a knowledge-based assistant. "
                    "Answer only using the provided context and conversation history. "
                    "If the answer is not known, say you don't know."
                ),
            },
            {
                "role": "system",
                "content": "Knowledge Base:\n" + "\n\n".join(kb_chunks),
            },
        ]

        # memory
        for chat in previous_chats:
            messages.append({"role": "user", "content": chat.question})
            messages.append({"role": "assistant", "content": chat.answer})

        # current question
        messages.append({"role": "user", "content": question})

        # 5️⃣ Generate answer
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

        answer = response.choices[0].message.content.strip()

        # 6️⃣ Save chat
        self.db.add(Chat(question=question, answer=answer))
        self.db.commit()

        return answer
