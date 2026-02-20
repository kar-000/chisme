from pydantic import BaseModel, computed_field
from datetime import datetime
from typing import Optional


class AttachmentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    mime_type: str
    size: int
    created_at: datetime
    external_url: Optional[str] = None
    thumbnail_filename: Optional[str] = None

    @computed_field
    @property
    def url(self) -> str:
        if self.external_url:
            return self.external_url
        return f"/uploads/{self.filename}"

    @computed_field
    @property
    def thumbnail_url(self) -> Optional[str]:
        if self.thumbnail_filename:
            return f"/uploads/{self.thumbnail_filename}"
        return None

    model_config = {"from_attributes": True}
