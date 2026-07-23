from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskTitleRewriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=50)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title cannot be empty")
        return title


class TaskTitleRewriteResponse(BaseModel):
    reply: str


class TaskPlanSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=50)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("title cannot be empty")
        return title


class TaskPlanSuggestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=200)
    tags: list[str] = Field(min_length=1, max_length=3)


class ProjectQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=2, max_length=300)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("question cannot be empty")
        return question


class ProjectQuestionResponse(BaseModel):
    answer: str = Field(min_length=1)
    sources: list[str]
