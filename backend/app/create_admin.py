from .database import SessionLocal
from .models.user import UserORM
import sys


def promote_to_admin(username: str):
    db = SessionLocal()

    try:
        user = db.query(UserORM).filter(
            UserORM.username == username
        ).first()

        if user is None:
            print("user not found")
            return

        user.role = "admin"
        user.token_version += 1
        db.commit()
        print(f"{username} is now admin")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m backend.app.create_admin <username>")

    promote_to_admin(sys.argv[1])