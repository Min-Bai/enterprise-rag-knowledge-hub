from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")


    title: str = Field(min_length=1, max_length=50)
    done: bool = False
    archived: bool = False
    priority: int = Field(default=1, ge=1, le=5)
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if value.strip() == "":
            raise ValueError("title cannot be empty")
        return value.strip()


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    
    title: str | None = Field(default=None, min_length=1, max_length=50)
    done: bool | None = None
    archived: bool | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    due_date: date | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_nullable_fields(cls, data):
        if isinstance(data, dict):
            for field_name in ("title", "done", "archived", "priority"):
                if field_name in data and data[field_name] is None:
                    raise ValueError(f"{field_name} cannot be null")
        return data

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if value is None:
            return None

        if value.strip() == "":
            raise ValueError("title cannot be empty")

        return value.strip()


class TaskResponse(BaseModel):
    id: int
    title: str
    done: bool
    archived: bool
    user_id: int | None = None
    priority: int
    due_date: date | None = None
    updated_at: datetime

class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    count: int
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None
    sort: str
    page: int | None = None
    page_size: int | None = None
    next_page: int | None = None
    total_pages: int | None = None


class TaskCountResponse(BaseModel):
    count: int
