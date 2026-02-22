"""
Centralized auth service — all auth decisions flow through here.

No JWT decoding should happen outside this module.

Federation seam: get_user_from_token() checks home_server to determine whether
a token belongs to this server or a future remote server. Right now only local
tokens are accepted; the remote branch is a comment marking where federation
would hook in.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
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
    except JWTError:
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
