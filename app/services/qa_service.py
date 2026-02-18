# app/services/qa_service.py

from sqlalchemy.orm import Session
from openai import OpenAI
import os

from app.models.chat import Chat
from app.models.session import ConversationSession
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import search_similar_chunks
from app.services.websocket_manager import WebSocketManager


class QAService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Check if human already handling
    def _is_taken_over(self, sess_id: int) -> bool:
        return (
            self.db.query(ConversationSession)
            .filter(
                ConversationSession.sess_id == sess_id,
                ConversationSession.status == "pending_agent",
            )
            .first()
            is not None
        )

    # Save chat message
    def _save_message(
        self,
        sess_id: int,
        sender: str,
        message: str,
        needs_human: bool = False,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
    ) -> Chat:
        chat = Chat(
            sess_id=sess_id,
            sender=sender,
            message=message,
            needs_human=needs_human,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)
        return chat

    # Detect failure response
    def _bot_does_not_know(self, answer: str) -> bool:
        if not answer:
            return True
        low = answer.lower().strip()
        return low in ["i don't know.", "i dont know", "i'm not sure.", "i don't know"]

    # Count previous failures
    def _get_failure_count(self, sess_id: int) -> int:
        return (
            self.db.query(Chat)
            .filter(
                Chat.sess_id == sess_id,
                Chat.sender == "bot",
                Chat.needs_human == True,
            )
            .count()
        )

    async def ask(self, question: str, sess_id: int) -> str:
        if sess_id is None:
            raise ValueError("sess_id must not be None")

        # 1️⃣ Stop if already taken over
        if self._is_taken_over(sess_id):
            return "A human support agent is handling your chat now."

        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty")

        # 2️⃣ Save user message
        self._save_message(sess_id, "user", question)

        # 3️⃣ Embedding + KB Search
        query_embedding, embedding_tokens = self.embedding_service.create_embedding(
            question
        )
        kb_chunks = search_similar_chunks(
            db=self.db, query_embedding=query_embedding, top_k=5
        )

        # 4️⃣ Build LLM messages
        messages = [
            {
                "role": "system",
                "content": "You are a knowledge-based assistant. Answer ONLY using the provided knowledge base and conversation history. If the answer is not present, say: 'I don't know.'",
            }
        ]

        if kb_chunks:
            messages.append(
                {
                    "role": "system",
                    "content": "Knowledge Base:\n"
                    + "\n\n".join(kb_chunks),
                }
            )

        previous_chats = (
            self.db.query(Chat)
            .filter(Chat.sess_id == sess_id)
            .order_by(Chat.created_at.asc())
            .all()
        )

        for chat in previous_chats:
            role = "user" if chat.sender == "user" else "assistant"
            messages.append({"role": role, "content": chat.message})

        messages.append({"role": "user", "content": question})

        # 5️⃣ Call OpenAI
        response = self.client.chat.completions.create(
            model="gpt-4o-mini", messages=messages
        )

        usage = response.usage
        answer = response.choices[0].message.content.strip()

        # 6️⃣ Handle bot failure logic
        if self._bot_does_not_know(answer):

            failure_count = self._get_failure_count(sess_id)

            # Save failure message
            self._save_message(
                sess_id,
                "bot",
                answer,
                needs_human=True,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )

            # ✅ If failures < 5 → DO NOT transfer yet
            if failure_count < 5:
                return answer

            # 🔥 6th failure → Transfer to human
            session_exists = (
                self.db.query(ConversationSession)
                .filter(ConversationSession.sess_id == sess_id)
                .first()
            )

            if not session_exists:
                session = ConversationSession(
                    sess_id=sess_id,
                    status="pending_agent",
                )
                self.db.add(session)
                self.db.commit()

                # Notify agents
                await WebSocketManager.broadcast_to_agents(
                    {
                        "type": "NEW_ALERT",
                        "sess_id": sess_id,
                        "session_id": session.id,
                    }
                )

                # Notify user
                await WebSocketManager.send_to_user(
                    sess_id,
                    {
                        "type": "human_alert",
                        "message": "I was unable to answer multiple times. A human agent has now been notified.",
                    },
                )

            return "I was unable to answer multiple times. A human agent has now been notified."

        # 7️⃣ Save normal bot answer
        self._save_message(
            sess_id,
            "bot",
            answer,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

        return answer
