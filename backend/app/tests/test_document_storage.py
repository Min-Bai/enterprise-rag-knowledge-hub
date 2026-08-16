from pathlib import Path
from io import BytesIO

import pytest
from fastapi import UploadFile

from backend.app.services import document_storage


def test_document_directory_matches_application_data_volume():
    assert document_storage.DOCUMENT_DIRECTORY == (
        Path(document_storage.__file__).resolve().parents[1]
        / "data"
        / "documents"
    )


@pytest.mark.anyio
async def test_save_document_file_saves_valid_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(document_storage, "DOCUMENT_DIRECTORY", tmp_path)

    file = UploadFile(
        filename="resume.pdf",
        file=BytesIO(b"%PDF-1.4 test content"),
        headers={"content-type": "application/pdf"},
    )

    storage_path, content_sha256 = await document_storage.save_document_file(file)

    saved_file = tmp_path / Path(storage_path).name
    assert saved_file.exists()
    assert saved_file.read_bytes() == b"%PDF-1.4 test content"
    assert content_sha256 == "73caebc6e2aa8f9a7b950993208eb7ac8c380a5d8064d055735d899e8d730ec3"

@pytest.mark.anyio
@pytest.mark.parametrize(
    ("filename", "content_type", "content", "message"),
    [
        (
            "resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"not a supported document",
            "unsupported document type",
        ),
        (
            "resume.txt",
            "application/pdf",
            b"%PDF-1.4 content",
            "file content type does not match document type",
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

    with pytest.raises(
        document_storage.DocumentTooLargeError,
        match="file size must not exceed 10 MB",
    ):
        await document_storage.save_document_file(file)


@pytest.mark.anyio
async def test_save_document_file_saves_utf8_text_document(monkeypatch, tmp_path):
    monkeypatch.setattr(document_storage, "DOCUMENT_DIRECTORY", tmp_path)
    file = UploadFile(
        filename="policy.md",
        file=BytesIO("# 差旅制度\n报销需要审批。".encode()),
        headers={"content-type": "text/markdown"},
    )

    storage_path, _ = await document_storage.save_document_file(file)

    assert Path(storage_path).suffix == ".md"
    assert Path(storage_path).read_text(encoding="utf-8") == "# 差旅制度\n报销需要审批。"
