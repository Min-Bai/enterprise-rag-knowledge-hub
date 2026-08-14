from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentResponse(BaseModel):
    id: int
    knowledge_base_id: int
    filename: str
    status: str
    content_sha256: str | None = None
    tags: list[str] = Field(default_factory=list)
    chunk_count: int = 0
    processed_at: datetime | None = None
    error_message: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DocumentTagsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        from ..services.document_tags import normalize_document_tags

        return normalize_document_tags(value)


class DocumentChunkResponse(BaseModel):
    document_id: int
    filename: str
    chunk_index: int
    page: int | None = None
    text: str
    score: float


class DocumentSearchResponse(BaseModel):
    items: list[DocumentChunkResponse]


class DocumentSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=300)
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("question cannot be empty")
        return question

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        from ..services.document_tags import normalize_document_tags

        return normalize_document_tags(value)


class DocumentAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: int = Field(gt=0)
    question: str = Field(min_length=2, max_length=2000)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("question cannot be empty")
        return question
