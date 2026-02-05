import random
from sqlalchemy.orm import Session
from app.models.file_embedding import FileEmbedding
from app.services.embedding_service import EmbeddingService
from app.services.web_scraper import scrape_website_text
import tiktoken


class WebsiteKBService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()

    def add_website(self, url: str):
        url = url.strip()
        if not url:
            raise ValueError("URL is required")

        # 1) Scrape website
        text_content = scrape_website_text(url)

        if not text_content.strip():
            raise RuntimeError("No content extracted from website")

        combined_text = f"Source URL: {url}\n\n{text_content}"

        # 2) Chunk text (IMPORTANT)
        chunks = self._chunk_text(combined_text)

        if not chunks:
            raise RuntimeError("Failed to chunk website content")

        inserted_rows = 0

        generated_url_id = random.getrandbits(63)
        # 3) Embed + store EACH chunk
        for idx, chunk in enumerate(chunks):
            embedding_vector, tokens_used = self.embedding_service.create_embedding(chunk)

            if not embedding_vector:
                continue  # skip failed chunks safely

            db_embedding = FileEmbedding(
                embedding=embedding_vector,
                text_content=chunk,
                source_type="kb_url",
                url_id=generated_url_id if idx == 0 else None,  # ✅ only first chunk
                embedding_tokens=tokens_used,
            )

            self.db.add(db_embedding)
            inserted_rows += 1

        self.db.commit()

        return {
            "url": url,
            "chunks_created": len(chunks),
            "rows_inserted": inserted_rows,
            "total_text_length": len(text_content),
        }

    def _chunk_text(
        self,
        text: str,
        max_tokens: int = 800,
        overlap: int = 100,
        model: str = "text-embedding-3-small",
    ):
        encoder = tiktoken.encoding_for_model(model)
        tokens = encoder.encode(text)

        chunks = []
        start = 0

        while start < len(tokens):
            end = start + max_tokens
            chunk_tokens = tokens[start:end]
            chunks.append(encoder.decode(chunk_tokens))
            start += max_tokens - overlap

        return chunks
