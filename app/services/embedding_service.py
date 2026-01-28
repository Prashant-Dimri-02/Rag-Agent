from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class EmbeddingService:
    def create_embedding(self, text: str) -> list[float]:
        if not text.strip():
            return []

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )

        return response.data[0].embedding
