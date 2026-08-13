from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class ConversationMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: list[SourceItem] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: int
    document_id: int | None
    knowledge_base_id: int | None
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse]

    model_config = ConfigDict(from_attributes=True)
