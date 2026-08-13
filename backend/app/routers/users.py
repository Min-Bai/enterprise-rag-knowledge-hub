from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.user import (
    PasswordChange,
    UserCreate,
    UserDetailResponse,
    UserResponse,
    UserUpdate,
    UserRoleUpdate,
    UserProfileUpdate,
)
from ..services.users import (
    create_user_service,
    get_users_service,
    get_user_service,
    deactivate_user_service,
    delete_user_service,
    update_user_service,
    get_user_detail_service,
    change_password_service,
    logout_user_service,
    update_my_profile_service,
    update_user_role_service,
)
from ..exceptions import (
    DuplicateUsernameError,
    EmptyUserUpdateError,
    UserNotFoundError,
    IncorrectPasswordError,
)
from ..auth import get_current_user, require_admin
from ..models.user import UserORM


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/ping")
def users_ping():
    return {"message": "users router ok"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserORM = Depends(get_current_user)):
    return current_user

@router.get("/admin/ping")
def admin_ping(
    current_user: UserORM = Depends(require_admin),
):
    return {
        "message": "admin access granted",
        "username": current_user.username,
    }

@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    profile_update: UserProfileUpdate,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return update_my_profile_service(
            current_user=current_user,
            profile_update=profile_update,
            db=db,
        )
    except EmptyUserUpdateError:
        raise HTTPException(
            status_code=400,
            detail="provide at least one field to update",
        )
    except DuplicateUsernameError:
        raise HTTPException(
            status_code=400,
            detail="username already exists",
        )

@router.patch("/me/password", status_code=204)
def change_my_password(
    password_change: PasswordChange,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        change_password_service(
            current_user=current_user,
            password_change=password_change,
            db=db,
        )
    except IncorrectPasswordError:
        raise HTTPException(
            status_code=400,
            detail="old password is incorrect",
        )
    
@router.post("/me/logout", status_code=204)
def logout(
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logout_user_service(
        current_user=current_user,
        db=db,
    )

@router.post("", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return create_user_service(user=user, db=db)
    except DuplicateUsernameError:
        raise HTTPException(status_code=400, detail="username already exists")
    
@router.get("", response_model=list[UserResponse])
def get_users(
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    return get_users_service(db=db, is_active=is_active)

@router.get("/{user_id}/detail", response_model=UserDetailResponse)
def get_user_detail(user_id: int, db: Session = Depends(get_db)):
    try:
        return get_user_detail_service(user_id=user_id, db=db)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        return get_user_service(user_id=user_id, db=db)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    
@router.patch("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    current_admin: UserORM = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return deactivate_user_service(user_id=user_id, db=db)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")

@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    current_admin: UserORM = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return update_user_role_service(
            user_id=user_id,
            role_update=role_update,
            db=db,
        )
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")

@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_update: UserUpdate,
    user_id: int,
    current_admin: UserORM = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return update_user_service(
            user_id=user_id,
            user_update=user_update,
            db=db,
        )
    except EmptyUserUpdateError:
        raise HTTPException(
            status_code=400,
            detail="provide at least one field to update",
        )
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
    except DuplicateUsernameError:
        raise HTTPException(status_code=400, detail="username already exists")


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_admin: UserORM = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return delete_user_service(user_id=user_id, db=db)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="user not found")
