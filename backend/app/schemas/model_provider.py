from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelProviderUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=80)
    base_url: str = Field(min_length=8, max_length=500)
    model_name: str = Field(min_length=1, max_length=120)
    api_key: str | None = Field(default=None, max_length=500)
    is_active: bool = False
    input_price_per_million: float | None = Field(default=None, ge=0, le=1_000_000)
    output_price_per_million: float | None = Field(default=None, ge=0, le=1_000_000)

    @field_validator("display_name", "base_url", "model_name")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        if not value.startswith(("https://", "http://")):
            raise ValueError("base_url must be an http or https URL")
        return value.rstrip("/")


class ModelProviderResponse(BaseModel):
    slug: str
    display_name: str
    base_url: str
    model_name: str
    api_key_configured: bool
    api_key_masked: str | None
    is_active: bool
    input_price_per_million: float | None
    output_price_per_million: float | None
