import os
from pypdf import PdfReader
from docx import Document


def extract_text_from_file(file_path: str, content_type: str) -> str:
    text_parts: list[str] = []

    # TXT
    if content_type == "text/plain" or file_path.lower().endswith(".txt"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    # PDF
    if content_type == "application/pdf" or file_path.lower().endswith(".pdf"):
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)

    # DOCX
    if (
        content_type
        in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]
        or file_path.lower().endswith(".docx")
    ):
        doc = Document(file_path)
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        return "\n".join(text_parts)

    # fallback
    return ""
