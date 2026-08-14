from collections.abc import Iterable


MAX_DOCUMENT_TAGS = 10
MAX_DOCUMENT_TAG_LENGTH = 50


def normalize_document_tags(tags: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    for raw_tag in tags or []:
        tag = str(raw_tag).strip()
        if not tag or tag in normalized:
            continue
        if len(tag) > MAX_DOCUMENT_TAG_LENGTH:
            raise ValueError(f"document tags must be {MAX_DOCUMENT_TAG_LENGTH} characters or fewer")
        normalized.append(tag)
    if len(normalized) > MAX_DOCUMENT_TAGS:
        raise ValueError(f"documents support at most {MAX_DOCUMENT_TAGS} tags")
    return normalized


def parse_document_tags(value: str | None) -> list[str]:
    return normalize_document_tags(value.split(",") if value else [])
