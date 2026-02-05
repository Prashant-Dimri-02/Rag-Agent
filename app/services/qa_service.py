# app/services/qa_service.py
from sqlalchemy.orm import Session
from openai import OpenAI
import os
import asyncio


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


    def _is_taken_over(self, sess_id: int) -> bool:
        return self.db.query(Chat).filter(Chat.sess_id == sess_id, Chat.needs_human == True).first() is not None
    
    def _save_message(self, sess_id: int, sender: str, message: str,needs_human: bool = False,prompt_tokens: int = 0,
    completion_tokens: int = 0,total_tokens: int = 0,) -> Chat:
        chat = Chat(sess_id=sess_id, sender=sender, message=message, needs_human=needs_human, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens)
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)
        return chat


    def _bot_does_not_know(self, answer: str) -> bool:
        if answer is None:
            return True
        low = answer.lower().strip()
        return low in ["i don't know.", "i dont know", "i'm not sure."]


    async def ask(self, question: str, sess_id: int) -> str:
        if sess_id is None:
            raise ValueError("sess_id must not be None")
    

        # 1) stop if agent already took over
        if self._is_taken_over(sess_id):
            return "A human support agent is handling your chat now."


        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty")


        # save user message
        self._save_message(sess_id, "user", question)


        # embeddings + KB search
        query_embedding, embedding_tokens = self.embedding_service.create_embedding(question)
        kb_chunks = search_similar_chunks(db=self.db, query_embedding=query_embedding, top_k=5)


        # build messages for LLM
        messages = [{"role": "system", "content": "You are a knowledge-based assistant. Answer ONLY using the provided knowledge base and conversation history. If the answer is not present, say: 'I don't know.'"}]
        if kb_chunks:
            messages.append({"role": "system", "content": "Knowledge Base:\n" + "\n\n".join(kb_chunks)})


        # previous conversation (only this user's history)
        previous_chats = self.db.query(Chat).filter(Chat.sess_id == sess_id).order_by(Chat.created_at.asc()).all()
        for chat in previous_chats:
            role = "user" if chat.sender == "user" else "assistant"
            messages.append({"role": role, "content": chat.message})


        messages.append({"role": "user", "content": question})


        # 5) call OpenAI
        response = self.client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens
        answer = response.choices[0].message.content.strip()


        # 6) detect inability and trigger human alert
        if self._bot_does_not_know(answer):
            
            # save chats needs human flag
            self._save_message(sess_id, "bot", answer, needs_human=True, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens)
             # Create Session
            session = ConversationSession(
                    sess_id=sess_id,
                    status="pending_agent"
                )
            self.db.add(session)
            self.db.commit()

            # 3️⃣ Notify agents in real-time
            await WebSocketManager.broadcast_to_agents({
                "type": "NEW_ALERT",
                "sess_id": sess_id,
                "session_id": session.id
            })

            # 4️⃣ Notify user
            await WebSocketManager.send_to_user(
                sess_id,
                {
                    "type": "human_alert",
                    "message": "Unfortunately I don't know the answer to this question. A human agent has been notified."
                }
            )
            return "Unfortunately I don't know the answer to this question. A human agent has been notified."
            


        # 7) save bot answer and return
        self._save_message(sess_id, "bot", answer, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens)
        return answer