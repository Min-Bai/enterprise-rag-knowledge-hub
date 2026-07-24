from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    section: str
    text: str


def split_markdown_document(path: Path, max_chars: int = 800) -> list[KnowledgeChunk]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive")

    sections: list[tuple[str, list[str]]] = []
    current_section = "Overview"
    current_paragraphs: list[str] = []

    for block in path.read_text(encoding="utf-8").split("\n\n"):
        block = block.strip()
        if not block:
            continue

        if block.startswith("#") and "\n" not in block:
            if current_paragraphs:
                sections.append((current_section, current_paragraphs))
            current_section = block.lstrip("#").strip() or "Overview"
            current_paragraphs = []
        else:
            current_paragraphs.append(block)

    if current_paragraphs:
        sections.append((current_section, current_paragraphs))

    chunks: list[KnowledgeChunk] = []
    for section, paragraphs in sections:
        prefix = f"Section: {section}\n\n"
        current_text = prefix

        for paragraph in paragraphs:
            candidate = f"{current_text}{paragraph}\n\n"
            if current_text != prefix and len(candidate) > max_chars:
                chunks.append(
                    KnowledgeChunk(
                        source=path.name,
                        section=section,
                        text=current_text.rstrip(),
                    )
                )
                current_text = prefix

            current_text = f"{current_text}{paragraph}\n\n"

        if current_text != prefix:
            chunks.append(
                KnowledgeChunk(
                    source=path.name,
                    section=section,
                    text=current_text.rstrip(),
                )
            )

    return chunks
