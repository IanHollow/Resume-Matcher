import logging
from typing import List

from fastapi.concurrency import run_in_threadpool
from app.llm import get_embedding, parse_llama_args, ensure_gguf

from .base import EmbeddingProvider
from ..exceptions import ProviderError

logger = logging.getLogger(__name__)


class GGUFEmbeddingProvider(EmbeddingProvider):
    """Embedding provider for local GGUF models via ctransformers."""

    def __init__(self, model_path: str) -> None:
        ensure_gguf(model_path)
        # Parse LLAMA_ARGS; these flags allow device-specific tuning
        self._kwargs = parse_llama_args()
        self._model = model_path

    async def embed(self, text: str) -> List[float]:
        try:
            return await run_in_threadpool(
                get_embedding,
                text,
                self._model,
                self._kwargs,
            )
        except Exception as e:  # pragma: no cover - runtime error if model fails
            logger.error(f"gguf embedding error: {e}")
            raise ProviderError(f"GGUF - Error generating embedding: {e}") from e
