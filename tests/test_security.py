from python_practice.day57.security import hash_password, verify_password


def test_hash_password_does_not_return_plain_password():
    password = "secret123"

    password_hash = hash_password(password)

    assert password_hash != password


def test_verify_password_accepts_correct_password():
    password = "secret123"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password("secret123")

    assert verify_password("wrong-password", password_hash) is False
