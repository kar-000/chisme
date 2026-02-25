"""
Centralized auth service — all auth decisions flow through here.

No JWT decoding should happen outside this module.

Federation seam: get_user_from_token() checks home_server to determine whether
a token belongs to this server or a future remote server. Right now only local
tokens are accepted; the remote branch is a comment marking where federation
would hook in.
"""

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User

# ── Password ──────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Token ─────────────────────────────────────────────────────────────────────


def create_access_token(user: User, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT for a local user.

    The 'sub' claim uses the qualified name (username@home_server) so that
    tokens from Server A are distinguishable from tokens from Server B —
    the key change that supports future federation.
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user.qualified_name,  # e.g. "kyle@chisme-groupa.example.com"
        "user_id": user.id,
        "home_server": user.home_server,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT. Returns payload dict or None on failure."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None


# ── User Lookup ───────────────────────────────────────────────────────────────


def get_user_from_token(token: str, db: Session) -> User | None:
    """
    Resolve a JWT to a local User object.

    Only accepts tokens issued by THIS server (home_server == SERVER_DOMAIN).
    When federation is added, tokens from other servers take a different code
    path here — this is the seam.
    """
    payload = decode_access_token(token)
    if payload is None:
        return None

    home_server = payload.get("home_server")

    # Local user — look up by ID
    if home_server == settings.SERVER_DOMAIN:
        user_id = payload.get("user_id")
        if user_id is None:
            return None
        return db.query(User).filter(User.id == int(user_id), User.is_active == True).first()  # noqa: E712

    # Future: federated user from another server
    # return federated_user_service.resolve(payload, db)
    return None


# ── Refresh Token ──────────────────────────────────────────────────────────────


def create_refresh_token(user: User, db: Session) -> str:
    """Issue a new opaque refresh token, persist it, and return the raw value."""
    from app.models.refresh_token import RefreshToken

    raw = secrets.token_hex(64)  # 128 hex chars, 256 bits of entropy
    expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(user_id=user.id, token=raw, expires_at=expires))
    db.commit()
    return raw


def validate_refresh_token(token: str, db: Session) -> User | None:
    """Return the active user for a valid refresh token, or None."""
    from app.models.refresh_token import RefreshToken

    rt = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == token, RefreshToken.revoked == False)  # noqa: E712
        .first()
    )
    if rt is None or rt.expires_at < datetime.now(timezone.utc):
        return None
    return db.query(User).filter(User.id == rt.user_id, User.is_active == True).first()  # noqa: E712


def revoke_refresh_token(token: str, db: Session) -> None:
    """Mark a refresh token as revoked."""
    from app.models.refresh_token import RefreshToken

    rt = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if rt:
        rt.revoked = True
        db.commit()
