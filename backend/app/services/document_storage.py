from pathlib import Path
from hashlib import sha256
from io import BytesIO
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import UploadFile

from ..config import MAX_DOCUMENT_SIZE_MB


MAX_DOCUMENT_SIZE = MAX_DOCUMENT_SIZE_MB * 1024 * 1024
DOCUMENT_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "documents"
SUPPORTED_DOCUMENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".markdown": {"text/markdown", "text/plain", "application/octet-stream"},
    ".csv": {"text/csv", "application/csv", "application/vnd.ms-excel", "application/octet-stream"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel", "application/octet-stream"},
    ".doc": {"application/msword", "application/octet-stream"},
    ".xls": {"application/vnd.ms-excel", "application/octet-stream"},
    ".png": {"image/png", "application/octet-stream"},
    ".jpg": {"image/jpeg", "image/jpg", "application/octet-stream"},
    ".jpeg": {"image/jpeg", "image/jpg", "application/octet-stream"},
    ".tiff": {"image/tiff", "application/octet-stream"},
    ".bmp": {"image/bmp", "application/octet-stream"},
    ".mp3": {"audio/mpeg", "application/octet-stream"},
    ".wav": {"audio/wav", "audio/x-wav", "application/octet-stream"},
    ".m4a": {"audio/mp4", "audio/x-m4a", "application/octet-stream"},
    ".ogg": {"audio/ogg", "application/ogg", "application/octet-stream"},
}


class DocumentTooLargeError(ValueError):
    pass


def validate_office_document(content: bytes, suffix: str) -> None:
    if not content.startswith(b"PK\x03\x04"):
        raise ValueError("invalid Office document")
    required_member = "word/document.xml" if suffix == ".docx" else "xl/workbook.xml"
    try:
        with ZipFile(BytesIO(content)) as archive:
            if required_member not in archive.namelist():
                raise ValueError("invalid Office document")
    except BadZipFile as error:
        raise ValueError("invalid Office document") from error


def get_stored_document_file(storage_path: str) -> Path:
    document_directory = DOCUMENT_DIRECTORY.resolve()
    path = Path(storage_path).resolve()
    if not path.is_relative_to(document_directory) or not path.is_file():
        raise FileNotFoundError("document file is unavailable")
    return path


async def save_document_file(file: UploadFile) -> tuple[str, str]:
    original_filename = file.filename or ""
    suffix = Path(original_filename).suffix.lower()

    if suffix not in SUPPORTED_DOCUMENT_TYPES:
        raise ValueError("unsupported document type")

    if file.content_type not in SUPPORTED_DOCUMENT_TYPES[suffix]:
        raise ValueError("file content type does not match document type")

    content = await file.read(MAX_DOCUMENT_SIZE + 1)

    if len(content) > MAX_DOCUMENT_SIZE:
        raise DocumentTooLargeError(
            f"file size must not exceed {MAX_DOCUMENT_SIZE_MB} MB"
        )

    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("invalid PDF file")

    if suffix in {".docx", ".xlsx"}:
        validate_office_document(content, suffix)

    if suffix not in {".pdf", ".docx", ".xlsx", ".doc", ".xls", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".mp3", ".wav", ".m4a", ".ogg"}:
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError("text document must use UTF-8 encoding") from error

    DOCUMENT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    storage_filename = f"{uuid4().hex}{suffix}"
    storage_path = DOCUMENT_DIRECTORY / storage_filename
    storage_path.write_bytes(content)

    return str(storage_path), sha256(content).hexdigest()
