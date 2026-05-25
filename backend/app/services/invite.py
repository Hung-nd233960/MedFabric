"""Invitation code service — hashed once at import, never stored in DB."""

from app.core.config import get_settings
from app.core.security import hash_password, verify_password

_settings = get_settings()
_invite_hash: str | None = (
    hash_password(_settings.registration_code) if _settings.registration_code else None
)


def registration_enabled() -> bool:
    return _invite_hash is not None


def verify_invite_code(code: str) -> bool:
    if _invite_hash is None:
        return False
    return verify_password(code, _invite_hash)
