# app/services/website_kb_service.py

import random
import tiktoken
from urllib.parse import urljoin, urlparse
from collections import deque

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
    # ADD WEBSITE (WITH INTERNAL CRAWLING)
    # =========================================================
    def add_website(self, url: str, max_pages: int = 50, max_depth: int = 3):
        url = url.strip()
        if not url:
            raise ValueError("URL is required")

        crawled_text = self._crawl_website(
            base_url=url,
            max_pages=max_pages,
            max_depth=max_depth,
        )

        if not crawled_text.strip():
            raise RuntimeError("No content extracted from website")

        chunks = self._chunk_text(crawled_text)

        if not chunks:
            raise RuntimeError("Failed to chunk website content")

        inserted_rows = 0
        generated_url_id = random.getrandbits(63)

        for idx, chunk in enumerate(chunks):
            embedding_vector, tokens_used = self.embedding_service.create_embedding(chunk)

            if not embedding_vector:
                continue

            db_embedding = FileEmbedding(
                embedding=embedding_vector,
                text_content=chunk,
                source_type="kb_url",
                url_id=generated_url_id,
                source_url=url if idx == 0 else None,
                embedding_tokens=tokens_used,
            )

            self.db.add(db_embedding)
            inserted_rows += 1

        self.db.commit()

        return {
            "url": url,
            "url_id": generated_url_id,
            "pages_crawled": len(chunks),
            "chunks_created": len(chunks),
            "rows_inserted": inserted_rows,
            "total_text_length": len(crawled_text),
        }

    # =========================================================
    # REAL INTERNAL CRAWLER
    # =========================================================
    def _crawl_website(self, base_url: str, max_pages: int, max_depth: int) -> str:
        visited = set()
        queue = deque()
        queue.append((base_url, 0))

        base_domain = urlparse(base_url).netloc

        collected_text = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            page = context.new_page()

            while queue and len(visited) < max_pages:
                current_url, depth = queue.popleft()

                if current_url in visited:
                    continue

                if depth > max_depth:
                    continue

                try:
                    page.goto(current_url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(2000)

                    html = page.content()
                    text = self._extract_text(html)

                    if text.strip():
                        collected_text.append(text)

                    visited.add(current_url)

                    # extract internal links
                    soup = BeautifulSoup(html, "html.parser")
                    for link in soup.find_all("a", href=True):
                        href = link["href"]

                        full_url = urljoin(current_url, href)
                        parsed = urlparse(full_url)

                        if parsed.netloc == base_domain:
                            clean_url = parsed.scheme + "://" + parsed.netloc + parsed.path
                            if clean_url not in visited:
                                queue.append((clean_url, depth + 1))

                except Exception:
                    continue

            context.close()
            browser.close()

        return "\n\n".join(collected_text)

    # =========================================================
    # TEXT CLEANER
    # =========================================================
    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if len(line) > 25]

        return "\n".join(lines)

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
