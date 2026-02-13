# app/services/embedding_service.py

import os
import time
import logging
from typing import Tuple, List
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class EmbeddingService:
    def create_embedding(self, text: str) -> Tuple[List[float], int]:
        """
        Creates embedding for given text.
        Returns (embedding_vector, tokens_used)
        """

        if not text or not text.strip():
            return [], 0

        max_retries = 3
        backoff = 1

        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )

                tokens = getattr(response.usage, "total_tokens", 0)

                return response.data[0].embedding, tokens

            except Exception as e:
                logger.warning(
                    f"Embedding failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                )
                time.sleep(backoff)
                backoff *= 2

        logger.error("Embedding failed after max retries.")
        return [], 0
