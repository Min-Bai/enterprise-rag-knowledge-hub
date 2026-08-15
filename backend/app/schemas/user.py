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
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


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


class PublicUserProfile(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


class UserLogin(StrictRequestSchema):
    username: str
    password: str


class PasswordChange(StrictRequestSchema):
    old_password: str = Field(min_length=6, max_length=72)
    new_password: str = Field(min_length=6, max_length=72)


class UserRoleUpdate(StrictRequestSchema):
    role: Literal["user", "admin"]


class AdminUserCreate(UserCreate):
    role: Literal["user", "admin"] = "user"


class UserProfileUpdate(StrictRequestSchema):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    email: str | None = None
    display_name: str | None = Field(default=None, max_length=80)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=280)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if value is None:
            return None

        if value.strip() == "":
            raise ValueError("username cannot be empty")

        return value.strip()

    @field_validator("display_name", "avatar_url", "bio")
    @classmethod
    def normalize_optional_text(cls, value):
        return value.strip() if value else None

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, value):
        if value is not None and not value.startswith(("https://", "http://")):
            raise ValueError("avatar_url must be an http or https URL")
        return value
