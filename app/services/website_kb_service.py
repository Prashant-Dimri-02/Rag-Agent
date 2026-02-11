import random
import requests
import tiktoken
import cloudscraper

from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from app.models.file_embedding import FileEmbedding
from app.services.embedding_service import EmbeddingService


class WebsiteKBService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()

    # =========================================================
    # ADD WEBSITE TO KNOWLEDGE BASE
    # =========================================================
    def add_website(self, url: str):
        url = url.strip()
        if not url:
            raise ValueError("URL is required")

        # 1️⃣ Scrape website
        text_content = self._scrape_website_text(url)

        if not text_content.strip():
            raise RuntimeError("No content extracted from website")

        # 2️⃣ Chunk text
        chunks = self._chunk_text(text_content)

        if not chunks:
            raise RuntimeError("Failed to chunk website content")

        inserted_rows = 0
        generated_url_id = random.getrandbits(63)

        for idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            embedding_vector, tokens_used = self.embedding_service.create_embedding(chunk)

            if not embedding_vector:
                continue

            db_embedding = FileEmbedding(
                embedding=embedding_vector,
                text_content=chunk,
                source_type="kb_url",
                url_id=generated_url_id,
                source_url=url if idx == 0 else None,  # ✅ only first row stores actual URL
                embedding_tokens=tokens_used,
            )

            self.db.add(db_embedding)
            inserted_rows += 1

        self.db.commit()

        return {
            "url": url,
            "url_id": generated_url_id,
            "chunks_created": len(chunks),
            "rows_inserted": inserted_rows,
            "total_text_length": len(text_content),
        }

    # =========================================================
    # SCRAPING STRATEGY
    # =========================================================
    def _scrape_website_text(self, url: str) -> str:
        try:
            return self._scrape_with_requests(url)
        except Exception:
            try:
                return self._scrape_with_cloudscraper(url)
            except Exception:
                return self._scrape_with_playwright(url)

    def _scrape_with_requests(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return self._extract_text(response.text)

    def _scrape_with_cloudscraper(self, url: str) -> str:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=20)
        response.raise_for_status()
        return self._extract_text(response.text)

    def _scrape_with_playwright(self, url: str) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000)
            content = page.content()
            browser.close()

        return self._extract_text(content)

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())

    # =========================================================
    # TOKEN CHUNKING
    # =========================================================
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
            chunk_text = encoder.decode(chunk_tokens)

            if chunk_text.strip():
                chunks.append(chunk_text)

            start += max_tokens - overlap

        return chunks
