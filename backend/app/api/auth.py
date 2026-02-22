from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.channel import Channel
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _ensure_general_channel(db: Session, creator_id: int) -> None:
    """Create the default #general channel if it doesn't exist yet."""
    exists = db.query(Channel).filter(Channel.name == "general").first()
    if not exists:
        general = Channel(
            name="general",
            description="General discussion — welcome to chisme!",
            created_by=creator_id,
            is_private=False,
        )
        db.add(general)
        db.commit()


@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Token:
    # Check for duplicate username
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

    # Check for duplicate email
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=auth_service.hash_password(user_in.password),
        home_server=settings.SERVER_DOMAIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Ensure #general channel exists for first user
    _ensure_general_channel(db, creator_id=user.id)

    access_token = auth_service.create_access_token(
        user,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(user))


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not auth_service.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

    access_token = auth_service.create_access_token(
        user,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer", user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
