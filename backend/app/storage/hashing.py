"""
File Hashing & Integrity Module
-------------------------------
Computes deterministic SHA-256 hashes for uploaded files and content blocks.
"""
import hashlib
from pathlib import Path
from typing import Union


class FileHasher:
    """Computes SHA-256 hashes for deduplication and integrity."""

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_file(file_path: Union[str, Path]) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
