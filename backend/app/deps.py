"""FastAPI dependency injection — auth, DB session, role checks."""

import uuid
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token_claims
from app.db.models import DoctorRole, Doctors
from app.services.credentials import get_doctor_by_uuid
from app.services.login_sessions import get_login_session


def get_token_from_request(request: Request) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[len("Bearer "):]
    return None


def get_current_doctor(
    request: Request,
    db: Session = Depends(get_db),
) -> Doctors:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = decode_access_token_claims(token)
    if not claims or not claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate login session is still active.
    # Tokens issued before session tracking was added won't have "sid" — allow
    # them through during the transition window (they expire within 120 min).
    sid = claims.get("sid")
    if sid:
        try:
            login_session = get_login_session(db, uuid.UUID(sid))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed session ID")
        if not login_session or not login_session.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    try:
        doctor_uuid = uuid.UUID(claims["sub"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token subject",
        )
    doctor = get_doctor_by_uuid(db, doctor_uuid)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doctor not found",
        )
    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return doctor


def get_current_admin(
    doctor: Doctors = Depends(get_current_doctor),
) -> Doctors:
    if doctor.role != DoctorRole.Admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return doctor


def get_refresh_token_from_cookie(
    refresh_token: Optional[str] = Cookie(default=None),
) -> str:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )
    return refresh_token
