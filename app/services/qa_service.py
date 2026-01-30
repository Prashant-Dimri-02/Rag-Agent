# app/services/qa_service.py
from sqlalchemy.orm import Session
from openai import OpenAI
import os
import asyncio


from app.models.chat import Chat
from app.models.support_alert import SupportAlert
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import search_similar_chunks
from app.services.websocket_manager import WebSocketManager
from app.services.support_service import create_alert_for_chat




class QAService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


    def _is_taken_over(self, user_id: int) -> bool:
        return self.db.query(Chat).filter(Chat.user_id == user_id, Chat.taken_over == True).first() is not None
    
    def _save_message(self, user_id: int, sender: str, message: str):
        chat = Chat(user_id=user_id, sender=sender, message=message)
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)
        return chat


    def _bot_does_not_know(self, answer: str) -> bool:
        if answer is None:
            return True
        low = answer.lower().strip()
        return low in ["i don't know.", "i dont know", "i'm not sure."]


    async def ask(self, question: str, user_id: int) -> str:
        if user_id is None:
            raise ValueError("user_id must not be None")


        # 1) stop if agent already took over
        if self._is_taken_over(user_id):
            return "A human support agent is handling your chat now."


        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty")


        # save user message
        self._save_message(user_id, "user", question)


        # embeddings + KB search
        query_embedding = self.embedding_service.create_embedding(question)
        kb_chunks = search_similar_chunks(db=self.db, query_embedding=query_embedding, top_k=5)


        # build messages for LLM
        messages = [{"role": "system", "content": "You are a knowledge-based assistant. Answer ONLY using the provided knowledge base and conversation history. If the answer is not present, say: 'I don't know.'"}]
        if kb_chunks:
            messages.append({"role": "system", "content": "Knowledge Base:\n" + "\n\n".join(kb_chunks)})


        # previous conversation (only this user's history)
        previous_chats = self.db.query(Chat).filter(Chat.user_id == user_id).order_by(Chat.created_at.asc()).all()
        for chat in previous_chats:
            role = "user" if chat.sender == "user" else "assistant"
            messages.append({"role": role, "content": chat.message})


        messages.append({"role": "user", "content": question})


        # 5) call OpenAI
        response = self.client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        answer = response.choices[0].message.content.strip()


        # 6) detect inability and trigger human alert
        if self._bot_does_not_know(answer):
            # mark conversation rows as needs_human
            self.db.query(Chat).filter(Chat.user_id == user_id).update({"needs_human": True})
            self.db.commit()
            # create support alert row and broadcast
            alert = create_alert_for_chat(self.db, None, user_id)


            # notify user via websocket that a human has been alerted
            await WebSocketManager.send_to_user(
                user_id,
                {
                    "type": "human_alert",
                    "message": "A human agent has been notified."
                }
            )


            return "I’m not sure about this. I’ve notified a human agent 👨‍💻"


        # 7) save bot answer and return
        self._save_message(user_id, "bot", answer)
        return answer