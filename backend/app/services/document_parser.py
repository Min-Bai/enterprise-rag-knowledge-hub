from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    page: int


def extract_pdf_pages(storage_path: str) -> list[tuple[int, str]]:
    reader = PdfReader(Path(storage_path))
    pages = [
        (page_number, (page.extract_text() or "").strip())
        for page_number, page in enumerate(reader.pages, start=1)
    ]
    pages = [page for page in pages if page[1]]
    if not pages:
        raise ValueError("PDF does not contain extractable text")
    return pages


def extract_pdf_text(storage_path: str) -> str:
    return "\n".join(text for _, text in extract_pdf_pages(storage_path))

    return text

def create_text_splitter(
    *,
    chunk_size: int,
    overlap: int,
) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],
    )


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

    return create_text_splitter(
        chunk_size=chunk_size,
        overlap=overlap,
    ).split_text(cleaned_text)


def split_pdf_into_chunks(
    storage_path: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[DocumentChunk]:
    splitter = create_text_splitter(
        chunk_size=chunk_size,
        overlap=overlap,
    )
    return [
        DocumentChunk(text=chunk, page=page_number)
        for page_number, page_text in extract_pdf_pages(storage_path)
        for chunk in splitter.split_text(page_text)
    ]
