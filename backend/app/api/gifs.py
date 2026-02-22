"""Tenor GIF search proxy and attachment creation."""

import httpx
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
    params["media_filter"] = "tinygif,nanogif"
    url = f"{settings.TENOR_API_BASE}/{path}"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Tenor API error: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Tenor API error: {exc}",
        ) from exc


def _parse_results(data: dict) -> list[GifResult]:
    results = []
    for item in data.get("results", []):
        fmts = item.get("media_formats", {})
        tinygif = fmts.get("tinygif") or fmts.get("gif", {})
        nanogif = fmts.get("nanogif") or tinygif
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


@router.get("/search", response_model=list[GifResult])
def search_gifs(
    q: str = "",
    limit: int = 20,
    current_user: User = Depends(get_current_user),
) -> list[GifResult]:
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
