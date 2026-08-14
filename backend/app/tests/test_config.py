import pytest

from backend.app import config


def set_env_value(monkeypatch, value):
    monkeypatch.setattr(
        config,
        "getenv",
        lambda name, default=None: value if value is not None else default,
    )


def test_required_environment_variable_must_not_be_empty(monkeypatch):
    set_env_value(monkeypatch, "")

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY is required"):
        config.get_required_env("JWT_SECRET_KEY")


@pytest.mark.parametrize("value", ["short", "replace-this-with-a-long-random-secret"])
def test_jwt_secret_rejects_unsafe_values(value):
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        config.validate_jwt_secret(value)


def test_jwt_secret_accepts_a_long_random_value():
    value = "a" * 32
    assert config.validate_jwt_secret(value) == value


@pytest.mark.parametrize(
    ("value", "expected"),
    [("true", True), ("FALSE", False)],
)
def test_boolean_environment_variable_is_parsed(monkeypatch, value, expected):
    set_env_value(monkeypatch, value)

    assert config.get_bool_env("SQL_ECHO") is expected


@pytest.mark.parametrize("value", ["0", "-1", "not-a-number"])
def test_positive_integer_environment_variable_rejects_invalid_values(
    monkeypatch,
    value,
):
    set_env_value(monkeypatch, value)

    with pytest.raises(RuntimeError):
        config.get_positive_int_env("LOGIN_RATE_LIMIT", 5)
