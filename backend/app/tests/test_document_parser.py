import pytest

from backend.app.services.document_parser import split_text_into_chunks


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
