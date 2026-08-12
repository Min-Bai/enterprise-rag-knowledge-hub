from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.task import (
    TaskCountResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from ..services.tasks import (
    create_task_service,
    delete_task_service,
    archive_task_service,
    get_task_service,
    get_tasks_service,
    mark_task_done_service,
    mark_task_undone_service,
    unarchive_task_service,
    update_task_service,
    get_task_count_service,
    get_accessible_task_service,
)
from ..exceptions import (
    DuplicateTitleError,
    EmptyUpdateError,
    TaskNotFoundError,
    TaskUserNotFoundError,
    TaskPermissionDeniedError
)

from ..auth import get_current_user
from ..models.user import UserORM
from ..query_params import PaginationParams, get_pagination_params

TaskSort = Literal["id_asc", "id_desc", "priority_asc", "priority_desc"]

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return create_task_service(
    task=task,
    current_user=current_user,
    db=db,
) 
    except DuplicateTitleError:
        raise HTTPException(status_code=400, detail="title already exists")


@router.get("", response_model=TaskListResponse)
def get_tasks(
    done: bool | None = Query(default=None),
    archived: bool | None = Query(default=False),
    keyword: str | None = Query(default=None, min_length=1),
    user_id: int | None = Query(default=None, ge=1),
    sort: TaskSort = Query(default="id_asc"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    if current_user.role != "admin":
        user_id = current_user.id

    return get_tasks_service(
        db=db,
        done=done,
        archived=archived,
        keyword=keyword,
        user_id=user_id,
        sort=sort,
        limit=pagination.limit,
        offset=pagination.offset,
        page=pagination.page,
        page_size=pagination.page_size,
    )

@router.get("/me", response_model=TaskListResponse)
def get_my_tasks(
    done: bool | None = Query(default=None),
    archived: bool | None = Query(default=False),
    keyword: str | None = Query(default=None, min_length=1),
    sort: TaskSort = Query(default="id_asc"),
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_tasks_service(
        db=db,
        done=done,
        archived=archived,
        keyword=keyword,
        user_id=current_user.id,
        sort=sort,
        limit=pagination.limit,
        offset=pagination.offset,
        page=pagination.page,
        page_size=pagination.page_size,
    )

@router.get("/count", response_model=TaskCountResponse)
def get_task_count(
    done: bool | None = Query(default=None),
    archived: bool | None = Query(default=False),
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    user_id = None
    if current_user.role != "admin":
        user_id = current_user.id

    count = get_task_count_service(db=db, done=done, archived=archived, user_id=user_id,)
    return {"count": count}

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    try:
        return get_accessible_task_service(
    task_id=task_id,
    current_user=current_user,
    db=db,
)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    except TaskPermissionDeniedError:
        raise HTTPException(
            status_code=403,
            detail="task permission denied",
        )
    


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_update: TaskUpdate,
    task_id: int = Path(ge=1),
    db: Session = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    try:
        return update_task_service(
            task_id=task_id,
            task_update=task_update,
            db=db,
            current_user=current_user,
        )
    except EmptyUpdateError:
        raise HTTPException(
            status_code=400,
            detail="provide at least one field to update",
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    except DuplicateTitleError:
        raise HTTPException(status_code=400, detail="title already exists")
    except TaskPermissionDeniedError:
        raise HTTPException(
            status_code=403,
            detail="task permission denied",
        )


@router.patch("/{task_id}/done", response_model=TaskResponse)
def mark_task_done(
    task_id: int = Path(ge=1),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return mark_task_done_service(
            task_id=task_id,
            current_user=current_user,
            db=db,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    except TaskPermissionDeniedError:
        raise HTTPException(status_code=403, detail="task permission denied")


@router.patch("/{task_id}/undone", response_model=TaskResponse)
def mark_task_undone(
    task_id: int = Path(ge=1),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return mark_task_undone_service(
            task_id=task_id,
            current_user=current_user,
            db=db,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    except TaskPermissionDeniedError:
        raise HTTPException(status_code=403, detail="task permission denied")


@router.patch("/{task_id}/archive", response_model=TaskResponse)
def archive_task(
    task_id: int = Path(ge=1),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return archive_task_service(
            task_id=task_id,
            current_user=current_user,
            db=db,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    except TaskPermissionDeniedError:
        raise HTTPException(status_code=403, detail="task permission denied")


@router.patch("/{task_id}/unarchive", response_model=TaskResponse)
def unarchive_task(
    task_id: int = Path(ge=1),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return unarchive_task_service(
            task_id=task_id,
            current_user=current_user,
            db=db,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    except TaskPermissionDeniedError:
        raise HTTPException(status_code=403, detail="task permission denied")


@router.delete("/{task_id}")
def delete_task(
    task_id: int = Path(ge=1),
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return delete_task_service(
            task_id=task_id,
            current_user=current_user,
            db=db,
        )
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="task not found")
    except TaskPermissionDeniedError:
        raise HTTPException(status_code=403, detail="task permission denied")
