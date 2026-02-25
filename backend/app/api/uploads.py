from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.attachment import Attachment
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.storage import generate_thumbnail, save_upload

router = APIRouter(prefix="/upload", tags=["uploads"])

# Magic byte signatures for image types. Clients control the Content-Type header,
# so we verify the actual file bytes match the declared MIME for images, which are
# served publicly and are the primary target of MIME-spoof attacks.
_IMAGE_MAGIC: dict[str, tuple[bytes, ...]] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/gif": (b"GIF87a", b"GIF89a"),
}


def _image_magic_valid(mime: str, content: bytes) -> bool:
    """Return True if content magic bytes match the declared image MIME type."""
    if not mime.startswith("image/"):
        return True
    if mime == "image/webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    magic_options = _IMAGE_MAGIC.get(mime)
    if magic_options is None:
        return True  # unknown image subtype — allow
    return any(content[: len(m)] == m for m in magic_options)


@router.post("", response_model=AttachmentResponse)
async def upload_file(
    file: UploadFile = File(...),
    duration_secs: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttachmentResponse:
    """Upload a file and get back an attachment ID to attach to a message."""

    # Validate MIME type before reading the body.
    # Strip codec/parameter suffixes (e.g. "audio/webm;codecs=opus" → "audio/webm")
    # so the allowlist doesn't need an entry for every codec variant.
    base_mime = (file.content_type or "").split(";")[0].strip()
    if base_mime not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{base_mime}' is not allowed",
        )

    content = await file.read()

    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit",
        )

    # Verify magic bytes match the declared MIME for image types.
    # Prevents spoofed Content-Type attacks (e.g. PE binary uploaded as image/jpeg).
    if not _image_magic_valid(base_mime, content):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File content does not match declared type '{base_mime}'",
        )

    stored_filename, full_path = save_upload(
        content=content,
        original_filename=file.filename,
        upload_dir=settings.UPLOAD_DIR,
    )

    thumb_name = None
    if file.content_type and file.content_type.startswith("image/"):
        thumb_name = generate_thumbnail(full_path, settings.UPLOAD_DIR)

    attachment = Attachment(
        user_id=current_user.id,
        filename=stored_filename,
        original_filename=file.filename or "upload",
        mime_type=file.content_type,
        size=len(content),
        thumbnail_filename=thumb_name,
        duration_secs=duration_secs,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return AttachmentResponse.model_validate(attachment)
