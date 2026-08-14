import pytest

from backend.app.services import document_parser
from backend.app.services.document_parser import split_pdf_into_chunks, split_text_into_chunks


def test_split_text_into_chunks_prefers_paragraph_boundaries():
    text = "First paragraph explains the policy.\n\nSecond paragraph explains exceptions."

    chunks = split_text_into_chunks(text, chunk_size=45, overlap=5)

    assert chunks == [
        "First paragraph explains the policy.",
        "Second paragraph explains exceptions.",
    ]


@pytest.mark.parametrize(
    ("chunk_size", "overlap", "message"),
    [
        (0, 0, "chunk_size must be greater than zero"),
        (10, -1, "overlap must be between zero and chunk_size"),
        (10, 10, "overlap must be between zero and chunk_size"),
    ],
)
def test_split_text_into_chunks_rejects_invalid_sizes(
    chunk_size,
    overlap,
    message,
):
    with pytest.raises(ValueError, match=message):
        split_text_into_chunks("document text", chunk_size, overlap)


def test_split_text_into_chunks_returns_empty_list_for_blank_text():
    assert split_text_into_chunks("  \n\t ") == []


def test_split_pdf_into_chunks_preserves_one_based_page_numbers(monkeypatch):
    class Page:
        def __init__(self, text):
            self.text = text

        def extract_text(self):
            return self.text

    class Reader:
        pages = [Page("First page policy."), Page("Second page exception.")]

    monkeypatch.setattr(document_parser, "PdfReader", lambda _: Reader())

    chunks = split_pdf_into_chunks("document.pdf", chunk_size=100, overlap=10)

    assert [(chunk.text, chunk.page) for chunk in chunks] == [
        ("First page policy.", 1),
        ("Second page exception.", 2),
    ]


def test_split_pdf_into_chunks_rejects_pdf_without_extractable_text(monkeypatch):
    class Page:
        def extract_text(self):
            return ""

    class Reader:
        pages = [Page()]

    monkeypatch.setattr(document_parser, "PdfReader", lambda _: Reader())

    with pytest.raises(ValueError, match="PDF does not contain extractable text"):
        split_pdf_into_chunks("document.pdf")
