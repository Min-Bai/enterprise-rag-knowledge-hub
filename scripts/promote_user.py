"""Promote an existing Enterprise RAG user to administrator."""

import argparse

from backend.app.database import SessionLocal
from backend.app.models.user import UserORM
from backend.app.schemas.user import UserRoleUpdate
from backend.app.services.users import update_user_role_service


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(UserORM).filter(UserORM.username == args.username).first()
        if user is None:
            parser.error("username not found")
        update_user_role_service(user.id, UserRoleUpdate(role="admin"), db)
    finally:
        db.close()

    print(f"Promoted administrator: {args.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
