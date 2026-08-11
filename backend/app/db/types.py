"""Portable column types for PaperLens Atlas.

`GUID` transparently maps Python `uuid.UUID` values to:
- PostgreSQL's native `UUID` type when the active dialect is postgresql
- `CHAR(36)` (canonical hyphenated string form) on any other dialect,
  primarily SQLite for local development.

Usage:
    from app.db.types import GUID

    class Paper(Base):
        id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID column type.

    - Postgres: stored natively via `postgresql.UUID(as_uuid=True)`.
    - Everything else (SQLite, etc.): stored as a `CHAR(36)` string using
      the canonical `str(uuid.UUID(...))` representation, and always
      deserialized back into a `uuid.UUID` instance on read.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Optional[Any], dialect: Dialect):
        if value is None:
            return value

        # Coerce strings (or anything uuid.UUID accepts) to a real UUID first
        # so both dialects get consistent, validated input.
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))

        if dialect.name == "postgresql":
            # asyncpg/psycopg drivers accept native UUID objects directly.
            return value

        # SQLite (or any non-Postgres dialect): canonical 36-char string.
        return str(value)

    def process_result_value(self, value: Optional[Any], dialect: Dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    def process_literal_param(self, value: Optional[Any], dialect: Dialect) -> str:
        # Used for inline literal rendering (e.g. debug SQL / logging).
        if value is None:
            return "NULL"
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return f"'{value}'"

    @property
    def python_type(self):
        return uuid.UUID
