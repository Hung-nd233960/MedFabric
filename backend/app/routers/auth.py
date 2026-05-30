"""Authentication router — register, login, refresh, logout, change-password."""

import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token_claims,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.db.models import Doctors
from app.db.schemas import (
    ChangePasswordRequest,
    DoctorMeResponse,
    LoginRequest,
    RegisterRequest,
    SetupAccountRequest,
    TokenResponse,
    UserPreferences,
)
from app.deps import get_current_doctor, get_refresh_token_from_cookie
from app.services.credentials import (
    authenticate_doctor,
    change_password,
    get_doctor_by_uuid,
    register_doctor,
)
from app.services.errors import (
    DuplicateEntryError,
    InactiveAccountError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from app.services.invite import registration_enabled, verify_invite_code
from app.services.login_sessions import create_login_session, deactivate_login_session

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.refresh_token_expire_seconds,
        path="/api/auth/refresh",
    )


def _doctor_preferences(doctor: Doctors) -> UserPreferences:
    """Return the doctor's saved preferences, falling back to defaults."""
    raw = doctor.preferences or {}
    defaults = UserPreferences()
    return UserPreferences(
        dark=raw.get("dark", defaults.dark),
        tooltip_mode=raw.get("tooltip_mode", defaults.tooltip_mode),
        show_kbd_hints=raw.get("show_kbd_hints", defaults.show_kbd_hints),
        dashboard_hint_open=raw.get(
            "dashboard_hint_open", defaults.dashboard_hint_open
        ),
        nav_mode=raw.get("nav_mode", defaults.nav_mode),
    )


def _build_token_response(
    doctor: Doctors, response: Response, db: Session
) -> TokenResponse:
    """Issue a new access+refresh token pair and record the login session."""
    session = create_login_session(db, doctor.uuid)
    access = create_access_token(
        str(doctor.uuid),
        extra={
            "role": doctor.role.value,
            "username": doctor.username,
            "is_test": doctor.is_test,
            "sid": str(session.session_uuid),
        },
    )
    refresh_token = create_refresh_token(str(doctor.uuid))
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(
        access_token=access,
        must_change_password=doctor.must_change_password,
        must_set_name=doctor.must_set_name,
        preferences=_doctor_preferences(doctor),
    )


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("5/minute")
def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    if not registration_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is disabled.",
        )
    if not verify_invite_code(body.invitation_code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid invitation code."
        )
    try:
        doctor = register_doctor(
            db,
            username=body.username,
            password=body.password,
            full_name=body.full_name,
            email=body.email,
            registration_source="self_registered",
        )
    except DuplicateEntryError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _build_token_response(doctor, response, db)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        doctor = authenticate_doctor(db, body.username, body.password)
    except (UserNotFoundError, InvalidCredentialsError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from exc
    except InactiveAccountError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return _build_token_response(doctor, response, db)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
def refresh(
    request: Request,
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
    doctor = get_doctor_by_uuid(db, _uuid.UUID(subject))
    if not doctor or not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doctor not found or inactive",
        )
    return _build_token_response(doctor, response, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _doctor=Depends(get_current_doctor),
):
    # Deactivate the specific login session bound to this access token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        claims = decode_access_token_claims(auth_header[len("Bearer ") :])
        if claims and claims.get("sid"):
            try:
                deactivate_login_session(db, _uuid.UUID(claims["sid"]))
            except (ValueError, Exception):
                pass
    response.delete_cookie(key=_REFRESH_COOKIE, path="/api/auth/refresh")


@router.post("/setup-account", status_code=status.HTTP_204_NO_CONTENT)
def setup_account(
    body: SetupAccountRequest,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """First-login: set full_name and/or change forced password."""
    if body.full_name and doctor.must_set_name:
        doctor.full_name = body.full_name
        doctor.must_set_name = False
    if body.new_password and doctor.must_change_password:
        doctor.password_hash = hash_password(body.new_password)
        doctor.must_change_password = False
    db.commit()


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def change_password_endpoint(
    request: Request,
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    if not doctor.must_change_password:
        if not body.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required.",
            )
        if not verify_password(body.current_password, doctor.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect.",
            )
    change_password(db, doctor.uuid, body.new_password, must_change_password=False)


@router.post("/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def heartbeat(
    db: Session = Depends(get_db), doctor: Doctors = Depends(get_current_doctor)
):
    """Update last_seen timestamp for the authenticated doctor."""
    doctor.last_seen = datetime.now(timezone.utc)
    db.commit()


@router.get("/me", response_model=DoctorMeResponse)
def get_me(doctor: Doctors = Depends(get_current_doctor)) -> DoctorMeResponse:
    """Return the authenticated doctor's profile."""
    return DoctorMeResponse(
        uuid=str(doctor.uuid),
        username=doctor.username,
        email=doctor.email,
        full_name=doctor.full_name,
        role=doctor.role.value,
        is_test=doctor.is_test,
        created_at=doctor.created_at.isoformat() if doctor.created_at else None,
    )


@router.get("/preferences", response_model=UserPreferences)
def get_preferences(doctor: Doctors = Depends(get_current_doctor)) -> UserPreferences:
    """Return the authenticated doctor's UI preferences."""
    return _doctor_preferences(doctor)


@router.put("/preferences", status_code=status.HTTP_204_NO_CONTENT)
def save_preferences(
    body: UserPreferences,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
) -> None:
    """Persist the authenticated doctor's UI preferences."""
    doctor.preferences = body.model_dump()
    db.commit()
