#website_scraper.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def scrape_website_text(url: str) -> str:
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; RAGBot/1.0)"
        })
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch URL: {str(e)}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # remove scripts/styles/nav/footer
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # clean lines
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if len(line) > 30]  # drop noise

    final_text = "\n".join(lines)

    if not final_text.strip():
        raise RuntimeError("No meaningful text extracted from webpage")

    return final_text
