# app/services/qa_service.py

from sqlalchemy.orm import Session
from openai import OpenAI
import os
import logging
from typing import List, Optional

from app.models.chat import Chat
from app.models.session import ConversationSession
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import search_similar_chunks
from app.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class QAService:
    """
    QAService (RAG + conversational memory)
    - Rewrites follow-up questions into standalone queries for retrieval.
    - Uses rewritten query for embedding + vector search.
    - Builds chat messages from a bounded window of previous chats (no duplication).
    - Keeps original behavior of saving messages and human handoff logic.
    """

    # How many previous messages we'll include in the prompt (keeps tokens bounded).
    HISTORY_WINDOW = 20

    # When rewriting the query, how many recent chats to provide as context
    REWRITE_CONTEXT_WINDOW = 10

    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    def _bot_does_not_know(self, answer: Optional[str]) -> bool:
        if not answer:
            return True
        low = answer.lower().strip()
        # include several common variants
        return low in [
            "i don't know.",
            "i dont know",
            "i'm not sure.",
            "i don't know",
            "i am not sure.",
            "i do not know.",
        ]

    def _get_failure_count(self, sess_id: int) -> int:
        return (
            self.db.query(Chat)
            .filter(Chat.sess_id == sess_id, Chat.sender == "bot", Chat.needs_human == True)
            .count()
        )

    def _fetch_recent_chats(self, sess_id: int, limit: int) -> List[Chat]:
        """
        Fetch the last `limit` chats for the session in chronological order.
        """
        chats_desc = (
            self.db.query(Chat)
            .filter(Chat.sess_id == sess_id)
            .order_by(Chat.created_at.desc())
            .limit(limit)
            .all()
        )
        chats_desc.reverse()  # to chronological
        return chats_desc

    def _rewrite_question(self, sess_id: int, question: str) -> str:
        """
        Use the LLM to turn a follow-up question into a standalone question.
        Example:
          input question: "What is the price?"
          previous messages: "...kitchen backsplashes..."
          output: "What is the price of kitchen backsplash installation?"
        Returns rewritten question (or original question on failure).
        """
        # Prepare context (recent user + assistant messages)
        recent = self._fetch_recent_chats(sess_id, self.REWRITE_CONTEXT_WINDOW)

        # Build a compact context string (only the textual content)
        convo_lines = []
        for c in recent:
            role = "User" if c.sender == "user" else "Assistant"
            convo_lines.append(f"{role}: {c.message}")

        rewrite_system = {
            "role": "system",
            "content": (
                "You are a helpful assistant that rewrites follow-up user questions into a "
                "single, standalone question suitable for retrieval/embedding. Only output the "
                "rewritten standalone question (no extra commentary). If the question is already "
                "standalone, return it unchanged."
            ),
        }

        rewrite_user = {
            "role": "user",
            "content": (
                "Conversation context (most recent first):\n\n"
                + ("\n".join(convo_lines) if convo_lines else "(no prior conversation)\n")
                + "\n\n"
                + f"User's new question: {question}\n\n"
                + "Return a single sentence: a rewritten, standalone question that preserves "
                + "the user's intent and is clear about the subject/topic."
            ),
        }

        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[rewrite_system, rewrite_user],
                # keep response short
                max_tokens=128,
            )
            rewritten = resp.choices[0].message.content.strip()
            # safety: if model returns nothing or an obviously unsafe rewrite, fallback
            if not rewritten:
                return question
            return rewritten
        except Exception as e:
            logger.exception("Query rewrite failed, falling back to original question: %s", e)
            # fallback: simple heuristic — prepend last user message if available
            if recent:
                # find last user message
                last_user = None
                for c in reversed(recent):
                    if c.sender == "user":
                        last_user = c.message
                        break
                if last_user:
                    # quick heuristic
                    return f"{last_user.strip()} {question.strip()}"
            return question

    async def ask(self, question: str, sess_id: int) -> str:
        if sess_id is None:
            raise ValueError("sess_id must not be None")

        if self._is_taken_over(sess_id):
            return "A human support agent is handling your chat now."

        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty")

        # 1️⃣ Save the raw user message to DB (keeps an auditable log)
        self._save_message(sess_id, "user", question)

        # 2️⃣ Rewrite follow-up question into standalone query for retrieval
        rewritten_query = self._rewrite_question(sess_id, question)

        # 3️⃣ Embedding + KB Search (use rewritten_query)
        query_embedding, embedding_tokens = self.embedding_service.create_embedding(rewritten_query)
        kb_chunks = search_similar_chunks(db=self.db, query_embedding=query_embedding, top_k=5)

        # 4️⃣ Build LLM messages
        messages = [
    {
        "role": "system",
        "content": (
            "You are a helpful assistant.\n"
            "Use only the provided knowledge base to answer the question.\n"
            "Do NOT mention knowledge base, chunks, sources, or internal data.\n"
            "Answer naturally like a human expert. but dont include any extra commentary.\n"
            "If the answer is not present, say: I don't know."
        ),
        }
    ]

        if kb_chunks:
            messages.append(
                {"role": "system", "content": "Knowledge Base:\n" + "\n\n".join(kb_chunks)}
            )

        # 5️⃣ Load recent conversation history (bounded window) and avoid duplicating the just-saved question
        recent_chats = self._fetch_recent_chats(sess_id, self.HISTORY_WINDOW)

        # If the last saved chat equals the current raw question, exclude it from previous_chats,
        # because we'll append the rewritten query as the active user input below.
        if recent_chats:
            last_chat = recent_chats[-1]
            if last_chat.sender == "user" and last_chat.message.strip() == question:
                # exclude the last item
                recent_chats = recent_chats[:-1]

        # Convert chat rows to messages (chronological)
        for chat in recent_chats:
            role = "user" if chat.sender == "user" else "assistant"
            messages.append({"role": role, "content": chat.message})

        # Append the rewritten standalone query as the current user prompt for the model.
        messages.append({"role": "user", "content": rewritten_query})

        # 6️⃣ Call OpenAI chat completion
        try:
            response = self.client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        except Exception as e:
            logger.exception("OpenAI chat completion failed: %s", e)
            # Best-effort fallback answer
            fallback = "Sorry, I'm unable to contact the language model right now."
            self._save_message(sess_id, "bot", fallback)
            return fallback

        usage = getattr(response, "usage", None)
        answer = response.choices[0].message.content.strip()

        # 7️⃣ Handle bot failure logic
        if self._bot_does_not_know(answer):
            failure_count = self._get_failure_count(sess_id)

            # Save failure message with usage if available
            self._save_message(
                sess_id,
                "bot",
                answer,
                needs_human=True,
                prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
                total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
            )

            # If failures < 5 -> return the "I don't know."
            if failure_count < 5:
                return answer

            # 6th failure -> create ConversationSession and notify agents & user
            session_exists = (
                self.db.query(ConversationSession).filter(ConversationSession.sess_id == sess_id).first()
            )

            if not session_exists:
                session = ConversationSession(sess_id=sess_id, status="pending_agent")
                self.db.add(session)
                self.db.commit()

                # Notify agents
                await WebSocketManager.broadcast_to_agents(
                    {"type": "NEW_ALERT", "sess_id": sess_id, "session_id": session.id}
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

        # 8️⃣ Save normal bot answer (with usage if available)
        self._save_message(
            sess_id,
            "bot",
            answer,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
        )

        return answer