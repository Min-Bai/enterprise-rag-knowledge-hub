from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(storage_path: str) -> str:
    reader = PdfReader(Path(storage_path))

    pages_text = [
        page.extract_text() or ""
        for page in reader.pages
    ]
    text = "\n".join(pages_text).strip()

    if not text:
        raise ValueError("PDF does not contain extractable text")

    return text

def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between zero and chunk_size")

    cleaned_text = text.strip()
    if not cleaned_text:
        return []

    step = chunk_size - overlap
    return [
        cleaned_text[start : start + chunk_size]
        for start in range(0, len(cleaned_text), step)
    ]