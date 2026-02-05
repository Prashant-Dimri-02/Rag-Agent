from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.models.chat import Chat
from app.models.file_embedding import FileEmbedding


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_info(self):
        # ============================
        # 1️⃣ Total Distinct Sessions
        # ============================
        total_sessions = (
            self.db.query(func.count(distinct(Chat.sess_id)))
            .scalar()
        )

        # ============================
        # 2️⃣ Sessions With Human Intervention
        # ============================
        human_intervention_sessions = (
            self.db.query(func.count(distinct(Chat.sess_id)))
            .filter(Chat.needs_human == True)
            .scalar()
        )

        # ============================
        # 3️⃣ Chat Token Usage (LLM)
        # ============================
        total_chat_tokens = (
            self.db.query(func.sum(Chat.total_tokens))
            .scalar()
        )

        total_prompt_tokens = (
            self.db.query(func.sum(Chat.prompt_tokens))
            .scalar()
        )

        total_completion_tokens = (
            self.db.query(func.sum(Chat.completion_tokens))
            .scalar()
        )

        # ============================
        # 4️⃣ Embedding Token Usage
        # ============================
        total_embedding_tokens = (
            self.db.query(func.sum(FileEmbedding.embedding_tokens))
            .scalar()
        )

        # ============================
        # 5️⃣ Combined Total Tokens
        # ============================
        total_tokens_used = (
            (total_chat_tokens or 0) +
            (total_embedding_tokens or 0)
        )

        # ============================
        # Final Dashboard Response
        # ============================
        return {
            "total_sessions": total_sessions or 0,
            "human_intervention_sessions": human_intervention_sessions or 0,
            "chat_tokens": {
                "prompt_tokens": total_prompt_tokens or 0,
                "completion_tokens": total_completion_tokens or 0,
                "total_tokens": total_chat_tokens or 0,
            },
            "embedding_tokens_used": total_embedding_tokens or 0,
            "total_tokens_used": total_tokens_used,
        }
