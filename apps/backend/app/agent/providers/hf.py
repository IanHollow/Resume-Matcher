import logging
from typing import List

from fastapi.concurrency import run_in_threadpool
from sentence_transformers import SentenceTransformer

from .base import EmbeddingProvider
from ..exceptions import ProviderError

logger = logging.getLogger(__name__)


class HFEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using HuggingFace sentence-transformers."""

    def __init__(self, model_name: str) -> None:
        try:
            self._model = SentenceTransformer(model_name)
        except Exception as e:  # pragma: no cover - runtime error if model fails
            logger.error(f"hf load error: {e}")
            raise ProviderError(f"HF - Error loading embedding model: {e}") from e

    async def embed(self, text: str) -> List[float]:
        try:
            embedding = await run_in_threadpool(self._model.encode, text)
            return embedding.tolist()
        except Exception as e:  # pragma: no cover - runtime error if model fails
            logger.error(f"hf embedding error: {e}")
            raise ProviderError(f"HF - Error generating embedding: {e}") from e
