from python_practice.day57.services.knowledge import split_markdown_document


def test_split_markdown_document_keeps_source_and_section(tmp_path):
    document = tmp_path / "guide.md"
    document.write_text(
        "# Health Check\n\nGET /health confirms the API is running.\n\n"
        "# Authentication\n\nPOST /auth/login returns a JWT token.",
        encoding="utf-8",
    )

    chunks = split_markdown_document(document)

    assert len(chunks) == 2
    assert chunks[0].source == "guide.md"
    assert chunks[0].section == "Health Check"
    assert "GET /health" in chunks[0].text
    assert chunks[1].section == "Authentication"
