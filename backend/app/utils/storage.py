import os
from pathlib import Path
from typing import Tuple
import uuid

from fastapi import HTTPException, UploadFile, status
from app.core.config import settings


def get_upload_dir() -> Path:
    # Ensure storage path is relative to Backend base directory or absolute
    base_dir = Path(__file__).resolve().parent.parent.parent
    upload_path = base_dir / settings.UPLOAD_DIR
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


async def save_upload_file(upload_file: UploadFile) -> Tuple[str, str, int]:
    if not upload_file or not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided."
        )

    # 1. Path traversal prevention & original filename sanitization
    raw_filename = upload_file.filename
    sanitized_original_filename = Path(raw_filename).name
    if not sanitized_original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename."
        )

    # 2. Extension validation
    file_ext = os.path.splitext(sanitized_original_filename)[1].lower()
    if file_ext != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    # 3. MIME type validation
    content_type = upload_file.content_type
    if content_type and content_type.lower() not in ["application/pdf", "application/x-pdf", "application/acrobat"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    # 4. Generate unique internal file ID & filename (never trust original filename)
    internal_file_id = uuid.uuid4().hex
    stored_filename = f"{internal_file_id}.pdf"

    upload_dir = get_upload_dir()
    destination_path = upload_dir / stored_filename

    # 5. Chunked stream read to enforce max size (20 MB) & non-empty check
    total_bytes = 0
    chunk_size = 64 * 1024  # 64 KB chunks

    try:
        with open(destination_path, "wb") as buffer:
            while chunk := await upload_file.read(chunk_size):
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                    # File too large: remove partial file before raising exception
                    buffer.close()
                    if destination_path.exists():
                        destination_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File size exceeds maximum limit of 20 MB."
                    )
                buffer.write(chunk)
    except Exception as e:
        if destination_path.exists():
            destination_path.unlink()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

    if total_bytes == 0:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    return stored_filename, sanitized_original_filename, total_bytes


def delete_stored_file(stored_filename: str) -> bool:
    if not stored_filename:
        return False
    # Prevent path traversal in deletion
    safe_filename = Path(stored_filename).name
    target_path = get_upload_dir() / safe_filename
    if target_path.exists() and target_path.is_file():
        target_path.unlink()
        return True
    return False
