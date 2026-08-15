"""
File Storage Manager
--------------------
Handles secure filesystem storage with UUID file renaming and path traversal protections.
"""
from pathlib import Path
from typing import Tuple, Union
from fastapi import UploadFile
from app.utils.storage import delete_stored_file, get_upload_dir, save_upload_file


class StorageManager:
    """Manages file storage safely without user-controlled paths."""

    @staticmethod
    async def save_upload(file: UploadFile) -> Tuple[str, str, int]:
        return await save_upload_file(file)

    @staticmethod
    def delete_file(file_path: Union[str, Path]) -> bool:
        return delete_stored_file(file_path)

    @staticmethod
    def get_storage_dir() -> Path:
        return get_upload_dir()
