import logging
from typing import List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("paperlens")


class EmbeddingGenerationError(Exception):
    """Custom exception raised when vector embedding generation fails."""
    pass


class EmbeddingService:
    """
    OpenAI-compatible embedding API client abstraction.
    Supports configurable models, base URLs, API keys, and batch generation.
    """

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        self.client = http_client
        self.api_base = settings.EMBEDDING_API_BASE.rstrip("/")
        self.api_key = settings.EMBEDDING_API_KEY
        self.model = settings.EMBEDDING_MODEL

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        url = f"{self.api_base}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "input": texts
        }

        if not self.api_key:
            from app.services.offline_ai import generate_fallback_embedding
            logger.info("EMBEDDING_API_KEY not configured. Generating local fallback embeddings.")
            return [generate_fallback_embedding(t) for t in texts]

        should_close_client = False

        client = self.client

        if client is None:
            client = httpx.AsyncClient(timeout=30.0)
            should_close_client = True

        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Embedding API request failed [{response.status_code}]: {error_detail}")
                raise EmbeddingGenerationError(
                    f"Embedding API returned status code {response.status_code}."
                )

            data = response.json()
            if "data" not in data or not isinstance(data["data"], list):
                raise EmbeddingGenerationError("Invalid response format from embedding API provider.")

            # Sort results by index to ensure positional match
            sorted_data = sorted(data["data"], key=lambda x: x.get("index", 0))
            embeddings = [item["embedding"] for item in sorted_data]

            if len(embeddings) != len(texts):
                raise EmbeddingGenerationError(
                    f"Expected {len(texts)} embeddings, but received {len(embeddings)} from provider."
                )

            return embeddings

        except Exception as e:
            if isinstance(e, EmbeddingGenerationError):
                raise e
            logger.error(f"Network or exception during embedding generation: {str(e)}", exc_info=True)
            raise EmbeddingGenerationError("Failed to communicate with embedding API provider.") from e
        finally:
            if should_close_client and client:
                await client.aclose()
