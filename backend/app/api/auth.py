from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.channel import Channel
from app.models.server import Server
from app.models.server_membership import ROLE_MEMBER, ROLE_OWNER, ServerMembership
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _ensure_main_server_and_membership(db: Session, user: User) -> None:
    """
    Bootstrap logic run on every registration:

    1. If no 'main' server exists yet, create it with this user as owner
       and seed a #general channel inside it.
    2. If the 'main' server already exists, enroll this user as a member
       (if not already enrolled).

    This ensures:
    - The first user to register becomes the owner of 'main'.
    - Every subsequent user is automatically joined to 'main' on registration.
    """
    main_server = db.query(Server).filter(Server.slug == "main").first()

    if not main_server:
        # First-ever registration — bootstrap the deployment
        main_server = Server(
            name="Main",
            slug="main",
            description="The original Chisme community",
            owner_id=user.id,
            is_public=False,
        )
        db.add(main_server)
        db.flush()  # get main_server.id

        general = Channel(
            name="general",
            description="General discussion — welcome to Chisme!",
            server_id=main_server.id,
            created_by=user.id,
            is_private=False,
        )
        db.add(general)

        membership = ServerMembership(
            server_id=main_server.id,
            user_id=user.id,
            role=ROLE_OWNER,
        )
        db.add(membership)
        db.commit()
    else:
        # Subsequent registrations — auto-join main
        existing = (
            db.query(ServerMembership)
            .filter(
                ServerMembership.server_id == main_server.id,
                ServerMembership.user_id == user.id,
            )
            .first()
        )
        if not existing:
            membership = ServerMembership(
                server_id=main_server.id,
                user_id=user.id,
                role=ROLE_MEMBER,
            )
            db.add(membership)
            db.commit()


@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Token:
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=auth_service.hash_password(user_in.password),
        home_server=settings.SERVER_DOMAIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _ensure_main_server_and_membership(db, user)

    access_token = auth_service.create_access_token(
        user,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not auth_service.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    access_token = auth_service.create_access_token(
        user,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
