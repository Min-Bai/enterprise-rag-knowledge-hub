from pathlib import Path
from io import BytesIO

import pytest
from fastapi import UploadFile

from python_practice.day57.services import document_storage


@pytest.mark.anyio
async def test_save_document_file_saves_valid_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(document_storage, "DOCUMENT_DIRECTORY", tmp_path)

    file = UploadFile(
        filename="resume.pdf",
        file=BytesIO(b"%PDF-1.4 test content"),
        headers={"content-type": "application/pdf"},
    )

    storage_path = await document_storage.save_document_file(file)

    saved_file = tmp_path / Path(storage_path).name
    assert saved_file.exists()
    assert saved_file.read_bytes() == b"%PDF-1.4 test content"

@pytest.mark.anyio
@pytest.mark.parametrize(
    ("filename", "content_type", "content", "message"),
    [
        (
            "resume.txt",
            "application/pdf",
            b"%PDF-1.4 content",
            "only PDF files are allowed",
        ),
        (
            "resume.pdf",
            "text/plain",
            b"%PDF-1.4 content",
            "file content type must be application/pdf",
        ),
        (
            "resume.pdf",
            "application/pdf",
            b"not a PDF",
            "invalid PDF file",
        ),
    ],
)
async def test_save_document_file_rejects_invalid_uploads(
    filename,
    content_type,
    content,
    message,
):
    file = UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers={"content-type": content_type},
    )

    with pytest.raises(ValueError, match=message):
        await document_storage.save_document_file(file)

@pytest.mark.anyio
async def test_save_document_file_rejects_oversized_pdf():
    content = b"%PDF-" + b"x" * document_storage.MAX_DOCUMENT_SIZE

    file = UploadFile(
        filename="large.pdf",
        file=BytesIO(content),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(ValueError, match="file size must not exceed 10 MB"):
        await document_storage.save_document_file(file)