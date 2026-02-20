"""Local disk storage for uploaded files.

Abstraction layer — swap this module to add S3/MinIO support later.
"""

import os
import uuid
from pathlib import Path
from typing import Optional


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


def generate_thumbnail(src_path: str, upload_dir: str, max_size: int = 320) -> Optional[str]:
    """Generate a JPEG thumbnail for an image file.

    Returns the thumbnail filename (e.g. ``thumb_<uuid>.jpg``) on success,
    or ``None`` if Pillow is unavailable or the file is not a supported image.
    """
    try:
        from PIL import Image  # type: ignore[import]
    except ImportError:
        return None

    try:
        img = Image.open(src_path)
        img.thumbnail((max_size, max_size))
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        thumb_name = f"thumb_{uuid.uuid4().hex}.jpg"
        img.save(
            os.path.join(upload_dir, thumb_name),
            "JPEG",
            quality=85,
            optimize=True,
        )
        return thumb_name
    except Exception:
        return None
