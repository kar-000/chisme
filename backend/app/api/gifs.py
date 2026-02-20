"""Tenor GIF search proxy and attachment creation."""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.attachment import Attachment
from app.models.user import User
from app.schemas.attachment import AttachmentResponse

router = APIRouter(prefix="/gifs", tags=["gifs"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class GifResult(BaseModel):
    id: str
    url: str
    preview_url: str
    title: str
    width: int
    height: int


class GifAttachRequest(BaseModel):
    tenor_id: str
    url: str
    title: str = ""
    width: int = 0
    height: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tenor_fetch(path: str, params: dict) -> dict:
    """Call the Tenor v2 API and return the parsed JSON response."""
    params["key"] = settings.TENOR_API_KEY
    params["media_filter"] = "gif"
    qs = urllib.parse.urlencode(params)
    url = f"{settings.TENOR_API_BASE}/{path}?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Tenor API error: {exc}",
        ) from exc


def _parse_results(data: dict) -> List[GifResult]:
    results = []
    for item in data.get("results", []):
        fmts = item.get("media_formats", {})
        tinygif = fmts.get("tinygif", {})
        nanogif = fmts.get("nanogif", tinygif)
        if not tinygif.get("url"):
            continue
        dims = tinygif.get("dims", [0, 0])
        results.append(
            GifResult(
                id=item["id"],
                url=tinygif["url"],
                preview_url=nanogif.get("url", tinygif["url"]),
                title=item.get("content_description", ""),
                width=dims[0] if dims else 0,
                height=dims[1] if len(dims) > 1 else 0,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/search", response_model=List[GifResult])
def search_gifs(
    q: str = "",
    limit: int = 20,
    current_user: User = Depends(get_current_user),
) -> List[GifResult]:
    """Search Tenor for GIFs (or return featured GIFs when query is empty)."""
    limit = min(limit, settings.TENOR_SEARCH_LIMIT)
    if q.strip():
        data = _tenor_fetch("search", {"q": q.strip(), "limit": limit})
    else:
        data = _tenor_fetch("featured", {"limit": limit})
    return _parse_results(data)


@router.post("/attach", response_model=AttachmentResponse)
def attach_gif(
    body: GifAttachRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttachmentResponse:
    """Record a Tenor GIF as an attachment (external URL, no local storage)."""
    attachment = Attachment(
        user_id=current_user.id,
        filename=f"tenor_{body.tenor_id}.gif",
        original_filename=body.title or f"tenor_{body.tenor_id}.gif",
        mime_type="image/gif",
        size=0,
        external_url=body.url,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return AttachmentResponse.model_validate(attachment)
