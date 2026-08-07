from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class DocumentSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=300)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("question cannot be empty")
        return question


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