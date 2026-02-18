"""Local disk storage for uploaded files.

Abstraction layer — swap this module to add S3/MinIO support later.
"""

import os
import uuid
from pathlib import Path


def _uuid_filename(original: str | None) -> str:
    """Return a UUID-based filename preserving the original extension."""
    ext = Path(original).suffix.lower() if original else ""
    return f"{uuid.uuid4().hex}{ext}"


def save_upload(content: bytes, original_filename: str | None, upload_dir: str) -> tuple[str, str]:
    """Write *content* to *upload_dir* with a UUID filename.

    Returns:
        (stored_filename, full_path)
    """
    os.makedirs(upload_dir, exist_ok=True)
    stored = _uuid_filename(original_filename)
    full_path = os.path.join(upload_dir, stored)
    with open(full_path, "wb") as fh:
        fh.write(content)
    return stored, full_path


def delete_upload(filename: str, upload_dir: str) -> None:
    """Delete *filename* from *upload_dir*. Silently ignores missing files."""
    path = os.path.join(upload_dir, filename)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
