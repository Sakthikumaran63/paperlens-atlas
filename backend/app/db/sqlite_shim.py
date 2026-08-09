import logging
import sqlalchemy.dialects.postgresql as _pg
from sqlalchemy import String, JSON as _JSON
from app.core.config import settings

logger = logging.getLogger("paperlens")

import uuid
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

if settings.DATABASE_URL.startswith("sqlite"):
    class _UUIDCompat(TypeDecorator):
        """Platform-independent UUID type. Stored as CHAR(36) in SQLite."""
        impl = CHAR
        cache_ok = True

        def __init__(self, as_uuid=True, **kw):
            super().__init__()

        def load_dialect_impl(self, dialect):
            if dialect.name == "postgresql":
                return dialect.type_descriptor(PG_UUID(as_uuid=True))
            return dialect.type_descriptor(CHAR(36))

        def process_bind_param(self, value, dialect):
            if value is None:
                return value
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)

        def process_result_value(self, value, dialect):
            if value is None:
                return value
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value

    _pg.UUID = _UUIDCompat  # type: ignore[attr-defined]
    _pg.JSONB = _JSON  # type: ignore[attr-defined]

    try:
        import pgvector.sqlalchemy as _pv
        _pv.Vector = _JSON  # type: ignore[attr-defined]
    except ImportError:
        pass

    logger.info("SQLite mode: patched postgresql.UUID with TypeDecorator for local development.")

