from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.task import TaskORM
from ..models.user import UserORM
from ..schemas.task import TaskCreate, TaskUpdate
from ..exceptions import (
    DuplicateTitleError,
    EmptyUpdateError,
    TaskNotFoundError,
    TaskUserNotFoundError,
    TaskPermissionDeniedError,
)


TASK_STATUS_FIELDS = {"done", "archived"}

def create_task_service(
    task: TaskCreate,
    current_user: UserORM,
    db: Session,
):

    task_orm = TaskORM(
        title=task.title,
        done=task.done,
        archived=task.archived,
        user_id=current_user.id,
        priority=task.priority,
        due_date=task.due_date,
    )
    db.add(task_orm)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateTitleError("title already exists")

    db.refresh(task_orm)
    return task_orm

def get_tasks_service(
    db: Session,
    done: bool | None = None,
    archived: bool | None = False,
    keyword: str | None = None,
    sort: str = "id_asc",
    limit: int = 10,
    offset: int = 0,
    page: int | None = None,
    page_size: int | None = None,
    user_id: int | None = None,
):
    statement = select(TaskORM)
    count_statement = select(func.count()).select_from(TaskORM)

    if archived is not None:
        statement = statement.where(TaskORM.archived == archived)
        count_statement = count_statement.where(TaskORM.archived == archived)

    if done is not None:
        statement = statement.where(TaskORM.done == done)
        count_statement = count_statement.where(TaskORM.done == done)

    if keyword is not None:
        statement = statement.where(TaskORM.title.contains(keyword))
        count_statement = count_statement.where(TaskORM.title.contains(keyword))

    if sort == "id_desc":
        statement = statement.order_by(TaskORM.id.desc())
    elif sort == "priority_asc":
        statement = statement.order_by(TaskORM.priority.asc(), TaskORM.id.asc())
    elif sort == "priority_desc":
        statement = statement.order_by(TaskORM.priority.desc(), TaskORM.id.asc())
    else:
        statement = statement.order_by(TaskORM.id.asc())

    if user_id is not None:
        statement = statement.where(TaskORM.user_id == user_id)
        count_statement = count_statement.where(TaskORM.user_id == user_id)
        
    statement = statement.limit(limit).offset(offset)

    tasks = db.scalars(statement).all()
    total = db.scalar(count_statement)
    count = len(tasks)
    has_more = offset + count < total
    next_offset = offset + count if has_more else None
    total_pages = (
        (total + page_size - 1) // page_size
        if page is not None and page_size is not None
        else None
    )
    next_page = (
        page + 1
        if page is not None and total_pages is not None and page < total_pages
        else None
    )

    return {
        "items": tasks,
        "total": total,
        "count": count,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": next_offset,
        "sort": sort,
        "page": page,
        "page_size": page_size,
        "next_page": next_page,
        "total_pages": total_pages,
    }


def get_task_service(task_id: int, db: Session):
    statement = select(TaskORM).where(TaskORM.id == task_id)
    task = db.scalars(statement).first()

    if task is None:
        raise TaskNotFoundError("task not found")

    return task

def get_accessible_task_service(
    task_id: int,
    current_user: UserORM,
    db: Session,
):
    task = get_task_service(task_id=task_id, db=db)
    ensure_task_access_permission(
        task=task,
        current_user=current_user,
    )
    return task

def update_task_service(
    task_id: int,
    task_update: TaskUpdate,
    current_user: UserORM,
    db: Session,
):
    update_data = task_update.model_dump(exclude_unset=True)

    if not update_data:
        raise EmptyUpdateError("provide at least one field to update")

    task = get_task_service(task_id=task_id, db=db)
    ensure_task_access_permission(
        task=task,
        current_user=current_user,
    )

    for field_name, value in update_data.items():
        setattr(task, field_name, value)

    task.updated_at = datetime.now(UTC)
        
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateTitleError("title already exists")

    db.refresh(task)
    return task


def delete_task_service(task_id: int, db: Session,current_user: UserORM,):
    task = get_task_service(task_id=task_id, db=db)
    ensure_task_access_permission(
        task=task,
        current_user=current_user,
    )
    db.delete(task)
    db.commit()

    return {"message": "delete success"}


def update_task_status_service(
    task_id: int,
    db: Session,
    field_name: str,
    value: bool,
    current_user: UserORM,
):
    if field_name not in TASK_STATUS_FIELDS:
        raise ValueError("invalid task status field")

    task = get_task_service(task_id=task_id, db=db)
    ensure_task_access_permission(
        task=task,
        current_user=current_user,
    )
    setattr(task, field_name, value)
    task.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(task)

    return task


def mark_task_done_service(
    task_id: int,
    current_user: UserORM,
    db: Session,
):
    return update_task_status_service(
        task_id=task_id,
        current_user=current_user,
        db=db,
        field_name="done",
        value=True,
    )


def mark_task_undone_service(
    task_id: int,
    current_user: UserORM,
    db: Session,
):
    return update_task_status_service(
        task_id=task_id,
        current_user=current_user,
        db=db,
        field_name="done",
        value=False,
    )


def archive_task_service(
    task_id: int,
    current_user: UserORM,
    db: Session,
):
    return update_task_status_service(
        task_id=task_id,
        current_user=current_user,
        db=db,
        field_name="archived",
        value=True,
    )


def unarchive_task_service(
    task_id: int,
    current_user: UserORM,
    db: Session,
):
    return update_task_status_service(
        task_id=task_id,
        current_user=current_user,
        db=db,
        field_name="archived",
        value=False,
    )

def get_task_count_service(
    db: Session,
    done: bool | None = None,
    archived: bool | None = False,
    user_id: int | None = None,
):
    statement = select(func.count()).select_from(TaskORM)

    if archived is not None:
        statement = statement.where(TaskORM.archived == archived)

    if done is not None:
        statement = statement.where(TaskORM.done == done)
        
    if user_id is not None:
        statement = statement.where(TaskORM.user_id == user_id)
    return db.scalar(statement)

def ensure_task_access_permission(
    task: TaskORM,
    current_user: UserORM,
):
    if current_user.role == "admin":
        return

    if task.user_id != current_user.id:
        raise TaskPermissionDeniedError(
            "task permission denied"
        )
