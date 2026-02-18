from pydantic import BaseModel, computed_field
from datetime import datetime


class AttachmentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    mime_type: str
    size: int
    created_at: datetime

    @computed_field
    @property
    def url(self) -> str:
        return f"/uploads/{self.filename}"

    model_config = {"from_attributes": True}
