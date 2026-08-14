from pathlib import Path
from hashlib import sha256
from uuid import uuid4

from fastapi import UploadFile

from ..config import MAX_DOCUMENT_SIZE_MB


MAX_DOCUMENT_SIZE = MAX_DOCUMENT_SIZE_MB * 1024 * 1024
DOCUMENT_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "documents"


class DocumentTooLargeError(ValueError):
    pass


def get_stored_document_file(storage_path: str) -> Path:
    document_directory = DOCUMENT_DIRECTORY.resolve()
    path = Path(storage_path).resolve()
    if not path.is_relative_to(document_directory) or not path.is_file():
        raise FileNotFoundError("document file is unavailable")
    return path


async def save_document_file(file: UploadFile) -> tuple[str, str]:
    original_filename = file.filename or ""

    if Path(original_filename).suffix.lower() != ".pdf":
        raise ValueError("only PDF files are allowed")

    if file.content_type != "application/pdf":
        raise ValueError("file content type must be application/pdf")

    content = await file.read(MAX_DOCUMENT_SIZE + 1)

    if len(content) > MAX_DOCUMENT_SIZE:
        raise DocumentTooLargeError(
            f"file size must not exceed {MAX_DOCUMENT_SIZE_MB} MB"
        )

    if not content.startswith(b"%PDF-"):
        raise ValueError("invalid PDF file")

    DOCUMENT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    storage_filename = f"{uuid4().hex}.pdf"
    storage_path = DOCUMENT_DIRECTORY / storage_filename
    storage_path.write_bytes(content)

    return str(storage_path), sha256(content).hexdigest()
