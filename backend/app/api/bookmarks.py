from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.bookmark import Bookmark
from app.models.message import Message
from app.models.user import User
from app.schemas.bookmark import BookmarkCreate, BookmarkResponse, BookmarkUpdate
from app.schemas.message import MessageResponse

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"])


@router.post("", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    body: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookmarkResponse:
    msg = db.query(Message).filter(Message.id == body.message_id, Message.is_deleted == False).first()  # noqa: E712
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    existing = db.query(Bookmark).filter_by(user_id=current_user.id, message_id=body.message_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already bookmarked")

    bookmark = Bookmark(user_id=current_user.id, message_id=body.message_id, note=body.note)
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return BookmarkResponse(
        id=bookmark.id,
        message_id=bookmark.message_id,
        note=bookmark.note,
        created_at=bookmark.created_at,
        message=MessageResponse.model_validate(bookmark.message),
    )


@router.get("", response_model=list[BookmarkResponse])
async def list_bookmarks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BookmarkResponse]:
    bookmarks = db.query(Bookmark).filter_by(user_id=current_user.id).order_by(Bookmark.created_at.desc()).all()
    return [
        BookmarkResponse(
            id=b.id,
            message_id=b.message_id,
            note=b.note,
            created_at=b.created_at,
            message=MessageResponse.model_validate(b.message),
        )
        for b in bookmarks
    ]


@router.patch("/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    body: BookmarkUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookmarkResponse:
    bookmark = db.query(Bookmark).filter_by(id=bookmark_id, user_id=current_user.id).first()
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    bookmark.note = body.note
    db.commit()
    db.refresh(bookmark)
    return BookmarkResponse(
        id=bookmark.id,
        message_id=bookmark.message_id,
        note=bookmark.note,
        created_at=bookmark.created_at,
        message=MessageResponse.model_validate(bookmark.message),
    )


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    bookmark = db.query(Bookmark).filter_by(id=bookmark_id, user_id=current_user.id).first()
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    db.delete(bookmark)
    db.commit()


@router.get("/by-message/{message_id}", response_model=BookmarkResponse | None)
async def get_bookmark_for_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookmarkResponse | None:
    """Return the current user's bookmark for a specific message, or null."""
    bookmark = db.query(Bookmark).filter_by(user_id=current_user.id, message_id=message_id).first()
    if not bookmark:
        return None
    return BookmarkResponse(
        id=bookmark.id,
        message_id=bookmark.message_id,
        note=bookmark.note,
        created_at=bookmark.created_at,
        message=MessageResponse.model_validate(bookmark.message),
    )
