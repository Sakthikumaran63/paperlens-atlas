"""SQLite compatibility shim for Postgres-only column types.

PaperLens Atlas models declare columns using `postgresql.UUID` and
`pgvector.sqlalchemy.Vector` directly (in addition to the portable `GUID`
type in `types.py`), because those types carry Postgres-specific semantics
(native UUID storage, ANN vector search) in production.

When running locally against SQLite, neither type has a native SQLite
counterpart, so SQLAlchemy raises a compile error the moment it tries to
emit DDL or bind a parameter. This module monkey-patches both types so
they degrade gracefully on SQLite:

- `postgresql.UUID`  -> compiled as `CHAR(36)`, values stored as canonical
                        UUID strings, always returned as `uuid.UUID`.
- `pgvector.sqlalchemy.Vector` -> compiled as `TEXT`, values stored as a
                        JSON-encoded list of floats, returned as a
                        plain Python list on read.

IMPORTANT: call `patch_sqlite_types()` once, before any SQLite engine is
created (e.g. at the top of `env.py` for Alembic, or in your app's
settings/bootstrap module, gated behind a "using SQLite locally" check).
Patching is a no-op against a real Postgres connection since the patched
processors only activate when `dialect.name == "sqlite"`.

Example:
    # app/db/session.py
    from app.core.config import settings

    if settings.DATABASE_URL.startswith("sqlite"):
        from app.db.sqlite_shim import patch_sqlite_types
        patch_sqlite_types()
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles

_PATCHED = False


def patch_sqlite_types() -> None:
    """Idempotently patch `postgresql.UUID` and `pgvector.Vector` for SQLite."""
    global _PATCHED
    if _PATCHED:
        return

    _patch_uuid()
    _patch_vector()

    _PATCHED = True


def _patch_uuid() -> None:
    @compiles(PG_UUID, "sqlite")
    def _compile_pg_uuid_sqlite(type_, compiler, **kw) -> str:  # noqa: ARG001
        return "CHAR(36)"

    _orig_bind_processor = PG_UUID.bind_processor
    _orig_result_processor = PG_UUID.result_processor

    def bind_processor(self, dialect):
        if dialect.name != "sqlite":
            return _orig_bind_processor(self, dialect)

        def process(value: Optional[Any]):
            if value is None:
                return value
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(uuid.UUID(str(value)))

        return process

    def result_processor(self, dialect, coltype):
        if dialect.name != "sqlite":
            return _orig_result_processor(self, dialect, coltype)

        def process(value: Optional[Any]):
            if value is None:
                return value
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(str(value))

        return process

    PG_UUID.bind_processor = bind_processor
    PG_UUID.result_processor = result_processor


def _patch_vector() -> None:
    try:
        from pgvector.sqlalchemy import Vector
    except ImportError:
        # pgvector isn't installed in this environment (e.g. minimal CI
        # image) — nothing to patch, and nothing will try to use it.
        return

    @compiles(Vector, "sqlite")
    def _compile_vector_sqlite(type_, compiler, **kw) -> str:  # noqa: ARG001
        # No native vector type on SQLite; store as JSON-encoded TEXT.
        # (Similarity search must fall back to a Python-side implementation
        # in local dev — there's no ANN index here.)
        return "TEXT"

    _orig_bind_processor = Vector.bind_processor
    _orig_result_processor = Vector.result_processor

    def bind_processor(self, dialect):
        if dialect.name != "sqlite":
            return _orig_bind_processor(self, dialect)

        def process(value):
            if value is None:
                return value
            if hasattr(value, "tolist"):  # numpy array
                value = value.tolist()
            return json.dumps(list(value))

        return process

    def result_processor(self, dialect, coltype):
        if dialect.name != "sqlite":
            return _orig_result_processor(self, dialect, coltype)

        def process(value):
            if value is None:
                return value
            return json.loads(value)

        return process

    Vector.bind_processor = bind_processor
    Vector.result_processor = result_processor
