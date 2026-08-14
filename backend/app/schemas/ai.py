from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentAnswerRequest(BaseModel):
    document_id: int = Field(gt=0)
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = Field(default=None, gt=0)


class SourceItem(BaseModel):
    document_id: int
    filename: str
    page: int | None = None
    chunk_index: int


class DocumentAnswerResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    conversation_id: int


class KnowledgeBaseAnswerRequest(BaseModel):
    knowledge_base_id: int = Field(gt=0)
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = Field(default=None, gt=0)
    tags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        from ..services.document_tags import normalize_document_tags

        return normalize_document_tags(value)


class ConversationMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: list[SourceItem] | None
    feedback: Literal["helpful", "unhelpful"] | None = None
    feedback_comment: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnswerFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback: Literal["helpful", "unhelpful"]
    comment: str | None = Field(default=None, max_length=1000)


class ConversationResponse(BaseModel):
    id: int
    document_id: int | None
    knowledge_base_id: int | None
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse]

    model_config = ConfigDict(from_attributes=True)
