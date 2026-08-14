from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeBaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("name cannot be empty")
        return name


class KnowledgeBaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        if not name:
            raise ValueError("name cannot be empty")
        return name


class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    role: Literal["owner", "editor", "viewer"] = "owner"

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseMemberCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50)
    role: Literal["editor", "viewer"]


class KnowledgeBaseMemberResponse(BaseModel):
    user_id: int
    username: str
    role: Literal["owner", "editor", "viewer"]


class AuditLogResponse(BaseModel):
    id: int
    actor_user_id: int
    actor_username: str
    action: str
    target_type: str
    target_id: int | None
    details: dict[str, object] | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackSummaryResponse(BaseModel):
    total_feedback: int
    helpful_count: int
    unhelpful_count: int
    helpful_rate: float | None
    recent_unhelpful: list[dict[str, object]]
