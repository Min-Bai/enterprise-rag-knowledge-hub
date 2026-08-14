"""Create the first Enterprise RAG administrator without exposing a password in CLI history."""

import argparse
from getpass import getpass

from pydantic import ValidationError

from backend.app.database import SessionLocal
from backend.app.exceptions import DuplicateUsernameError
from backend.app.schemas.user import UserCreate
from backend.app.services.users import create_admin_user_service


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--email")
    args = parser.parse_args()

    password = getpass("Password: ")
    if password != getpass("Confirm password: "):
        parser.error("passwords do not match")

    try:
        user = UserCreate(
            username=args.username,
            email=args.email,
            password=password,
        )
    except ValidationError as error:
        parser.error(str(error))

    db = SessionLocal()
    try:
        admin = create_admin_user_service(user, db)
        username = admin.username
    except DuplicateUsernameError:
        parser.error("username already exists")
    finally:
        db.close()

    print(f"Created administrator: {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
