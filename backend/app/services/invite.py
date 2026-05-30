"""Invitation code service — hashed once at import, never stored in DB."""

from app.core.config import get_settings
from app.core.security import hash_password, verify_password

_settings = get_settings()
_INVITE_HASH: str | None = (
    hash_password(_settings.registration_code) if _settings.registration_code else None
)


def registration_enabled() -> bool:
    return _INVITE_HASH is not None


def verify_invite_code(code: str) -> bool:
    if _INVITE_HASH is None:
        return False
    return verify_password(code, _INVITE_HASH)
