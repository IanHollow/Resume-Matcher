import logging
import os
from typing import List

from fastapi.concurrency import run_in_threadpool
from llama_cpp import Llama
from app.llm.embedding_loader import parse_llama_args

from .base import EmbeddingProvider
from ..exceptions import ProviderError

logger = logging.getLogger(__name__)


class GGUFEmbeddingProvider(EmbeddingProvider):
    """Embedding provider for local GGUF models via llama-cpp."""

    def __init__(self, model_path: str) -> None:
        if not os.path.isfile(model_path):
            raise ProviderError(f"GGUF model not found at {model_path}")
        # Parse LLAMA_ARGS; these flags allow device-specific tuning
        kwargs = parse_llama_args()
        kwargs.setdefault("embedding", True)
        try:
            self._llama = Llama(model_path=model_path, **kwargs)
        except Exception as e:  # pragma: no cover - runtime error if model missing
            logger.error(f"gguf load error: {e}")
            raise ProviderError(f"GGUF - Error loading model: {e}") from e

    async def embed(self, text: str) -> List[float]:
        try:
            return await run_in_threadpool(self._llama.embed, text)
        except Exception as e:  # pragma: no cover - runtime error if model fails
            logger.error(f"gguf embedding error: {e}")
            raise ProviderError(f"GGUF - Error generating embedding: {e}") from e
