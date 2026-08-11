"""Embedding generation, with automatic offline fallback.

When `settings.EMBEDDING_API_KEY` is unset/empty (typical for local dev
without an OpenAI key), `EmbeddingService` transparently falls back to the
deterministic pseudo-embeddings from `app.services.offline_ai` instead of
calling an external API. The same fallback also kicks in if a real API
call fails at runtime (network error, rate limit, bad key, etc.) so a
pipeline run degrades gracefully rather than hard-failing the whole
EMBEDDING stage.

ASSUMPTION: `app.core.config.settings` exposes `EMBEDDING_API_KEY: str`
(empty string or None when unconfigured) and optionally
`EMBEDDING_MODEL: str`. Adjust the import/attribute names if yours differ.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional, Sequence

from app.services.offline_ai import generate_offline_embedding

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIM = 1536


class EmbeddingGenerationError(Exception):
    """Raised when embedding generation fails."""
    pass



class EmbeddingService:
    """Generates text embeddings, using a real API when configured and a
    deterministic offline heuristic otherwise (or on API failure)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        dim: int = DEFAULT_DIM,
        **kwargs: Any,
    ) -> None:

        if api_key is None:
            from app.core.config import settings  # local import: avoids a hard settings dependency at module import time (useful for tests)
            api_key = getattr(settings, "EMBEDDING_API_KEY", None)

        self.api_key = api_key
        self.model = model
        self.dim = dim
        self._client = None  # lazily built on first online use

    @property
    def is_online(self) -> bool:
        """True if a usable API key is configured (does not guarantee the
        API call itself will succeed)."""
        return bool(self.api_key and self.api_key.strip())

    async def generate_embedding(self, text: str) -> list[float]:
        """Alias for embed_text to support legacy callers."""
        return await self.embed_text(text)

    async def generate_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        """Alias for embed_batch to support legacy callers."""
        return await self.embed_batch(texts)


    async def embed_text(self, text: str) -> list[float]:
        """Return an embedding vector for a single string of text."""
        if not text or not text.strip():
            return generate_offline_embedding("empty text", dim=self.dim)

        if self.is_online:
            try:
                embeddings = await self._embed_online([text])
                return embeddings[0]
            except Exception:
                logger.exception(
                    "Online embedding call failed for model=%s; falling back to offline embedding",
                    self.model,
                )
                return generate_offline_embedding(text, dim=self.dim)

        return generate_offline_embedding(text, dim=self.dim)

    async def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input string, preserving order."""
        cleaned = list(texts)
        if not cleaned:
            return []

        if self.is_online:
            try:
                return await self._embed_online(cleaned)
            except Exception:
                logger.exception(
                    "Online batch embedding call failed for model=%s (%d texts); falling back to offline embeddings",
                    self.model,
                    len(cleaned),
                )
                return [generate_offline_embedding(t, dim=self.dim) for t in cleaned]

        return [generate_offline_embedding(t, dim=self.dim) for t in cleaned]

    # -- online path -----------------------------------------------------

    async def _embed_online(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        response = await client.embeddings.create(model=self.model, input=texts)
        # OpenAI preserves input order in `response.data`, each with an `index`;
        # sort defensively rather than assuming order.
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI  # local import: keeps `openai` an optional dependency for fully-offline environments
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Process-wide cached `EmbeddingService`, built from current settings."""
    return EmbeddingService()
