from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import uuid4

from .database import SessionLocal
from .models.task import TaskORM
from .models.user import UserORM


db = SessionLocal()

try:
    username = f"relationship_user_{uuid4().hex[:8]}"
    title = f"relationship task {uuid4().hex[:8]}"

    user = UserORM(username=username)
    db.add(user)
    db.commit()
    db.refresh(user)

    task = TaskORM(
        title=title,
        done=False,
        user_id=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    statement = select(UserORM).where(UserORM.id == user.id)
    found_user = db.scalars(statement).first()

    print(found_user.username)
    print("before tasks")
    print([task.title for task in found_user.tasks])
    print("after tasks")
    print(found_user.tasks[0].title)

    statement = select(TaskORM).where(TaskORM.id == task.id)
    found_task = db.scalars(statement).first()

    print(found_task.title)
    print(found_task.user.username)

    print("selectinload users")

    statement = select(UserORM).options(selectinload(UserORM.tasks))
    users = db.scalars(statement).all()

    print(len(users[-1].tasks))

    for user in users[-3:]:
        print(user.username, [task.title for task in user.tasks])

    print(len(users[-1].tasks))
finally:
    db.close()
