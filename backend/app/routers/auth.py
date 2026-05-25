"""Authentication router — register, login, refresh, logout."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, verify_refresh_token
from app.db.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.deps import get_current_doctor, get_refresh_token_from_cookie
from app.services.credentials import authenticate_doctor, register_doctor
from app.services.errors import (
    DuplicateEntryError,
    InactiveAccountError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from app.services.login_sessions import create_login_session

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=False,  # set True in production behind HTTPS
        samesite="lax",
        max_age=settings.refresh_token_expire_seconds,
        path="/api/auth/refresh",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    try:
        doctor = register_doctor(
            db,
            username=body.username,
            password=body.password,
            email=body.email,
        )
    except DuplicateEntryError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    access = create_access_token(str(doctor.uuid), extra={"role": doctor.role.value})
    refresh = create_refresh_token(str(doctor.uuid))
    create_login_session(db, doctor.uuid)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        doctor = authenticate_doctor(db, body.username, body.password)
    except (UserNotFoundError, InvalidCredentialsError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    except InactiveAccountError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    access = create_access_token(str(doctor.uuid), extra={"role": doctor.role.value})
    refresh = create_refresh_token(str(doctor.uuid))
    create_login_session(db, doctor.uuid)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: str = Depends(get_refresh_token_from_cookie),
):
    subject = verify_refresh_token(refresh_token)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    import uuid
    from app.services.credentials import get_doctor_by_uuid
    doctor = get_doctor_by_uuid(db, uuid.UUID(subject))
    if not doctor or not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doctor not found or inactive",
        )
    access = create_access_token(str(doctor.uuid), extra={"role": doctor.role.value})
    new_refresh = create_refresh_token(str(doctor.uuid))
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, doctor=Depends(get_current_doctor)):
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/auth/refresh")
