"""
Keyword Notifications API

GET    /api/users/me/keywords        List the current user's keywords
POST   /api/users/me/keywords        Add a keyword  { keyword: str }
DELETE /api/users/me/keywords/{id}   Remove a keyword
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.keyword import UserKeyword
from app.models.user import User

router = APIRouter(prefix="/api/users/me/keywords", tags=["keywords"])

MAX_KEYWORDS = 20


class KeywordCreate(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=50)


class KeywordResponse(BaseModel):
    id: int
    keyword: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[KeywordResponse])
def list_keywords(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KeywordResponse]:
    rows = db.query(UserKeyword).filter(UserKeyword.user_id == current_user.id).all()
    return rows


@router.post("", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
def add_keyword(
    body: KeywordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KeywordResponse:
    existing = db.query(UserKeyword).filter(UserKeyword.user_id == current_user.id).count()
    if existing >= MAX_KEYWORDS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_KEYWORDS} keywords allowed")

    kw = body.keyword.strip().lower()
    if not kw:
        raise HTTPException(status_code=400, detail="Keyword must not be blank")

    # Silently ignore duplicates — return existing row
    existing_row = (
        db.query(UserKeyword).filter(UserKeyword.user_id == current_user.id, UserKeyword.keyword == kw).first()
    )
    if existing_row:
        return existing_row

    row = UserKeyword(user_id=current_user.id, keyword=kw)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword(
    keyword_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    row = db.query(UserKeyword).filter(UserKeyword.id == keyword_id, UserKeyword.user_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(row)
    db.commit()
