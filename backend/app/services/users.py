from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..exceptions import (
    DuplicateUsernameError,
    EmptyUserUpdateError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    UserInactiveError,
    UserNotFoundError,
)
from ..models.user import UserORM
from ..schemas.user import (
    PasswordChange,
    UserCreate,
    UserLogin,
    UserProfileUpdate,
    UserRoleUpdate,
    UserUpdate,
)
from ..security import hash_password, verify_password
from .knowledge_bases import get_default_knowledge_base_service


def get_users_service(
    db: Session,
    is_active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
):
    statement = select(UserORM).order_by(UserORM.id)
    if is_active is not None:
        statement = statement.where(UserORM.is_active == is_active)
    return db.scalars(statement.limit(limit).offset(offset)).all()


def get_user_service(user_id: int, db: Session):
    user = db.scalar(select(UserORM).where(UserORM.id == user_id))
    if user is None:
        raise UserNotFoundError('user not found')
    return user


def deactivate_user_service(user_id: int, db: Session):
    return update_user_service(user_id, UserUpdate(is_active=False), db)


def delete_user_service(user_id: int, db: Session):
    db.delete(get_user_service(user_id, db))
    db.commit()
    return {'message': 'delete success'}


def update_user_service(user_id: int, user_update: UserUpdate, db: Session):
    if all(value is None for value in (user_update.username, user_update.email, user_update.is_active)):
        raise EmptyUserUpdateError('provide at least one field to update')
    user = get_user_service(user_id, db)
    active_status_changed = (
        user_update.is_active is not None
        and user.is_active != user_update.is_active
    )
    for field in ('username', 'email', 'is_active'):
        value = getattr(user_update, field)
        if value is not None:
            setattr(user, field, value)
    if active_status_changed:
        user.token_version += 1
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateUsernameError('username already exists')
    db.refresh(user)
    return user


def create_user_service(user: UserCreate, db: Session):
    return create_user_with_role_service(user=user, role="user", db=db)


def create_admin_user_service(user: UserCreate, db: Session):
    return create_user_with_role_service(user=user, role="admin", db=db)


def create_user_with_role_service(*, user: UserCreate, role: str, db: Session):
    new_user = UserORM(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
        role=role,
    )
    db.add(new_user)
    try:
        db.flush()
        get_default_knowledge_base_service(db, new_user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateUsernameError('username already exists')
    db.refresh(new_user)
    return new_user


def get_user_detail_service(user_id: int, db: Session):
    return get_user_service(user_id, db)


def get_public_user_profile_service(user_id: int, db: Session):
    return get_user_service(user_id, db)


def login_user_service(user_login: UserLogin, db: Session):
    user = db.scalar(select(UserORM).where(UserORM.username == user_login.username))
    if user is None or not verify_password(user_login.password, user.password_hash):
        raise InvalidCredentialsError('invalid username or password')
    if not user.is_active:
        raise UserInactiveError('user is inactive')
    return user


def change_password_service(current_user: UserORM, password_change: PasswordChange, db: Session):
    if not verify_password(password_change.old_password, current_user.password_hash):
        raise IncorrectPasswordError('old password is incorrect')
    current_user.password_hash = hash_password(password_change.new_password)
    current_user.token_version += 1
    db.commit()


def logout_user_service(current_user: UserORM, db: Session):
    current_user.token_version += 1
    db.commit()


def update_user_role_service(user_id: int, role_update: UserRoleUpdate, db: Session):
    user = get_user_service(user_id, db)
    user.role = role_update.role
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user


def update_my_profile_service(current_user: UserORM, profile_update: UserProfileUpdate, db: Session):
    update_data = profile_update.model_dump(exclude_unset=True)
    if not update_data:
        raise EmptyUserUpdateError('provide at least one field to update')
    for field, value in update_data.items():
        setattr(current_user, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateUsernameError('username already exists')
    db.refresh(current_user)
    return current_user
