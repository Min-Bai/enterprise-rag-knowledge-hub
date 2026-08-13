from pydantic import BaseModel, ConfigDict, Field, field_validator

from typing import Literal

class StrictRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

class UserCreate(StrictRequestSchema):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=72)
    email: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if value.strip() == "":
            raise ValueError("username cannot be empty")
        return value.strip()


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    is_active: bool
    role: str


class UserUpdate(StrictRequestSchema):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = None
    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if value is None:
            return None

        if value.strip() == "":
            raise ValueError("username cannot be empty")

        return value.strip()


class UserDetailResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    is_active: bool
    role: str


class UserLogin(StrictRequestSchema):
    username: str
    password: str


class PasswordChange(StrictRequestSchema):
    old_password: str = Field(min_length=6, max_length=72)
    new_password: str = Field(min_length=6, max_length=72)


class UserRoleUpdate(StrictRequestSchema):
    role: Literal["user", "admin"]


class UserProfileUpdate(StrictRequestSchema):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if value is None:
            return None

        if value.strip() == "":
            raise ValueError("username cannot be empty")

        return value.strip()
