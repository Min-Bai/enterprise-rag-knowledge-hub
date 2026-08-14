from os import getenv
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"))


def get_required_env(name: str) -> str:
    value = getenv(name)

    if not value:
        raise RuntimeError(f"{name} is required")

    return value


def validate_jwt_secret(value: str) -> str:
    if value == "replace-this-with-a-long-random-secret" or len(value) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters and not use the example value")
    return value


JWT_SECRET_KEY = validate_jwt_secret(get_required_env("JWT_SECRET_KEY"))
JWT_ALGORITHM = "HS256"

jwt_expire_minutes_text = get_required_env("JWT_EXPIRE_MINUTES")

try:
    JWT_EXPIRE_MINUTES = int(jwt_expire_minutes_text)
except ValueError:
    raise RuntimeError("JWT_EXPIRE_MINUTES must be an integer")

if JWT_EXPIRE_MINUTES <= 0:
    raise RuntimeError("JWT_EXPIRE_MINUTES must be positive")

def get_bool_env(name: str) -> bool:
    value = get_required_env(name).lower()

    if value == "true":
        return True

    if value == "false":
        return False

    raise RuntimeError(f"{name} must be true or false")


def get_optional_bool_env(name: str, default: bool) -> bool:
    value = getenv(name)
    if value is None:
        return default
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    raise RuntimeError(f"{name} must be true or false")


SQL_ECHO = get_bool_env("SQL_ECHO")
DATABASE_URL = getenv("DATABASE_URL")
REDIS_URL = getenv("REDIS_URL")
DEEPSEEK_API_KEY = getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = getenv("DEEPSEEK_MODEL", "deepseek-chat")


def get_positive_int_env(name: str, default: int) -> int:
    value = getenv(name, str(default))

    try:
        number = int(value)
    except ValueError:
        raise RuntimeError(f"{name} must be an integer")

    if number <= 0:
        raise RuntimeError(f"{name} must be positive")

    return number


LOGIN_RATE_LIMIT = get_positive_int_env("LOGIN_RATE_LIMIT", 5)
LOGIN_RATE_WINDOW_SECONDS = get_positive_int_env(
    "LOGIN_RATE_WINDOW_SECONDS",
    60,
)
AI_RATE_LIMIT = get_positive_int_env("AI_RATE_LIMIT", 10)
AI_RATE_WINDOW_SECONDS = get_positive_int_env("AI_RATE_WINDOW_SECONDS", 60)
DOCUMENT_UPLOAD_RATE_LIMIT = get_positive_int_env(
    "DOCUMENT_UPLOAD_RATE_LIMIT",
    10,
)
DOCUMENT_UPLOAD_RATE_WINDOW_SECONDS = get_positive_int_env(
    "DOCUMENT_UPLOAD_RATE_WINDOW_SECONDS",
    60 * 60,
)
MAX_DOCUMENT_SIZE_MB = get_positive_int_env("MAX_DOCUMENT_SIZE_MB", 10)


def get_score_env(name: str, default: float) -> float:
    value = getenv(name, str(default))

    try:
        score = float(value)
    except ValueError:
        raise RuntimeError(f"{name} must be a number")

    if not 0 <= score <= 1:
        raise RuntimeError(f"{name} must be between 0 and 1")

    return score


RAG_MIN_SCORE = get_score_env("RAG_MIN_SCORE", 0.5)
RAG_QUERY_REWRITE_ENABLED = get_optional_bool_env(
    "RAG_QUERY_REWRITE_ENABLED",
    False,
)
ALLOW_SELF_REGISTRATION = get_optional_bool_env(
    "ALLOW_SELF_REGISTRATION",
    False,
)

CORS_ORIGINS = [
    origin.strip()
    for origin in get_required_env("CORS_ORIGINS").split(",")
    if origin.strip()
]

if not CORS_ORIGINS:
    raise RuntimeError("CORS_ORIGINS must contain at least one origin")

LOG_LEVEL = get_required_env("LOG_LEVEL").upper()

if LOG_LEVEL not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
    raise RuntimeError(
        "LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR"
    )
