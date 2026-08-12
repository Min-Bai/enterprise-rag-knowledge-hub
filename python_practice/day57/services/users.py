from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..models.user import UserORM
from ..models.task import TaskORM
from .knowledge_bases import get_default_knowledge_base_service
from ..schemas.user import (
    PasswordChange,
    UserCreate,
    UserLogin,
    UserProfileUpdate,
    UserRoleUpdate,
    UserUpdate,
)
from ..security import hash_password, verify_password
from ..exceptions import (
    DuplicateUsernameError,
    EmptyUserUpdateError,
    UserNotFoundError,
    InvalidCredentialsError,
    UserInactiveError,
    IncorrectPasswordError,
)


def get_users_service(db: Session, is_active: bool | None = None):
    statement = select(UserORM)

    if is_active is not None:
        statement = statement.where(UserORM.is_active == is_active)

    statement = statement.order_by(UserORM.id)
    return db.scalars(statement).all()

def get_user_service(user_id: int, db: Session):
    statement = select(UserORM).where(UserORM.id == user_id)
    user = db.scalars(statement).first()

    if user is None:
        raise UserNotFoundError("user not found")

    return user


def deactivate_user_service(user_id: int, db: Session):
    user_update = UserUpdate(is_active=False)
    return update_user_service(
        user_id=user_id,
        user_update=user_update,
        db=db,
    )


def delete_user_service(user_id: int, db: Session):
    user = get_user_service(user_id=user_id, db=db)
    db.delete(user)
    db.commit()

    return {"message": "delete success"}


def update_user_service(user_id: int, user_update: UserUpdate, db: Session):
    if (
        user_update.username is None
        and user_update.email is None
        and user_update.is_active is None
    ):
        raise EmptyUserUpdateError("provide at least one field to update")

    user = get_user_service(user_id=user_id, db=db)

    if user_update.username is not None:
        user.username = user_update.username
        
    if user_update.email is not None:
        user.email = user_update.email

    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateUsernameError("username already exists")

    db.refresh(user)
    return user

def create_user_service(user: UserCreate, db: Session):
    user_orm = UserORM(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
    )
    db.add(user_orm)

    try:
        db.flush()

        task_orm = TaskORM(
            title=f"{user.username}的默认任务",
            done=False,
            priority=1,
            user_id=user_orm.id,
        )
        db.add(task_orm)
        get_default_knowledge_base_service(db, user_orm.id)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateUsernameError("username already exists")

    db.refresh(user_orm)
    return user_orm


def get_user_detail_service(user_id: int, db: Session):
    statement = (
        select(UserORM)
        .options(selectinload(UserORM.tasks))
        .where(UserORM.id == user_id)
    )
    user = db.scalars(statement).first()

    if user is None:
        raise UserNotFoundError("user not found")

    return user

def login_user_service(user_login: UserLogin, db: Session):
    statement = select(UserORM).where(
        UserORM.username == user_login.username
    )
    user = db.scalars(statement).first()

    if user is None:
        raise InvalidCredentialsError("invalid username or password")

    if not verify_password(user_login.password, user.password_hash):
        raise InvalidCredentialsError("invalid username or password")
    
    if not user.is_active:
        raise UserInactiveError("user is inactive")

    return user

def change_password_service(
    current_user: UserORM,
    password_change: PasswordChange,
    db: Session,
):
    if not verify_password(
        password_change.old_password,
        current_user.password_hash,
    ):
        raise IncorrectPasswordError("old password is incorrect")

    current_user.password_hash = hash_password(
        password_change.new_password
    )
    current_user.token_version += 1
    db.commit()

def logout_user_service(
    current_user: UserORM,
    db: Session,
):
    current_user.token_version += 1
    db.commit()

def update_user_role_service(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session,
):
    user = get_user_service(user_id=user_id, db=db)

    user.role = role_update.role
    user.token_version += 1
    db.commit()
    db.refresh(user)

    return user

def update_my_profile_service(
    current_user: UserORM,
    profile_update: UserProfileUpdate,
    db: Session,
):
    update_data = profile_update.model_dump(exclude_unset=True)

    if not update_data:
        raise EmptyUserUpdateError(
            "provide at least one field to update"
        )

    if "username" in update_data:
        current_user.username = update_data["username"]

    if "email" in update_data:
        current_user.email = update_data["email"]

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateUsernameError("username already exists")

    db.refresh(current_user)
    return current_user
