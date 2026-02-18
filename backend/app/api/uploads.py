from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.attachment import Attachment
from app.models.user import User
from app.schemas.attachment import AttachmentResponse
from app.storage import save_upload

router = APIRouter(prefix="/upload", tags=["uploads"])


@router.post("", response_model=AttachmentResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttachmentResponse:
    """Upload a file and get back an attachment ID to attach to a message."""

    # Validate MIME type before reading the body
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{file.content_type}' is not allowed",
        )

    content = await file.read()

    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit",
        )

    stored_filename, _ = save_upload(
        content=content,
        original_filename=file.filename,
        upload_dir=settings.UPLOAD_DIR,
    )

    attachment = Attachment(
        user_id=current_user.id,
        filename=stored_filename,
        original_filename=file.filename or "upload",
        mime_type=file.content_type,
        size=len(content),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return AttachmentResponse.model_validate(attachment)
