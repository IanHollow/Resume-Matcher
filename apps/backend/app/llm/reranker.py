import os
import logging
from typing import Any, Dict, Iterable, List

from .embedding_loader import parse_llama_args

try:
    from exllamav2 import ExLlamaV2, ExLlamaV2Config, ExLlamaV2Tokenizer
    from exllamav2.generator import ExLlamaV2BaseGenerator
except Exception:  # pragma: no cover - optional dependency
    ExLlamaV2 = None  # type: ignore[misc]

try:
    from ctransformers import AutoModelForCausalLM, Config
except Exception:  # pragma: no cover - optional dependency
    AutoModelForCausalLM = None  # type: ignore[misc]
    Config = None  # type: ignore[misc]

logger = logging.getLogger(__name__)


def rerank(
    query: str,
    docs: Iterable[str],
    model_path: str | None = None,
    llama_args: Dict[str, Any] | None = None,
) -> List[float]:
    """Return relevance scores for *docs* in relation to *query*."""

    path = model_path or os.getenv("RERANK_PATH", "Qwen3-Reranker-0.6B-Q8_0.safetensors")
    kwargs = parse_llama_args() if llama_args is None else llama_args

    # Prefer exllamav2 when available
    if ExLlamaV2 is not None:
        try:
            cfg = ExLlamaV2Config(path)
            model = ExLlamaV2(cfg)
            tokenizer = ExLlamaV2Tokenizer(cfg)
            gen = ExLlamaV2BaseGenerator(model, tokenizer)
            scores: List[float] = []
            for doc in docs:
                prompt = f"<query>{query}</query><doc>{doc}</doc>"
                out = gen.generate_simple(prompt, max_new_tokens=1, **kwargs).strip()
                try:
                    scores.append(float(out))
                except ValueError:
                    scores.append(float('nan'))
            return scores
        except Exception as e:  # pragma: no cover - runtime error
            logger.error("exllamav2 rerank failed: %s", e)

    if AutoModelForCausalLM is None or Config is None:
        raise RuntimeError("ctransformers is not available")

    if "n_gpu_layers" in kwargs:
        kwargs["gpu_layers"] = kwargs.pop("n_gpu_layers")
    if "n_threads" in kwargs:
        kwargs["threads"] = kwargs.pop("n_threads")
    if "n_ctx" in kwargs:
        kwargs["context_length"] = kwargs.pop("n_ctx")

    llm = AutoModelForCausalLM.from_pretrained(path, config=Config(**kwargs))
    scores = []
    for doc in docs:
        prompt = f"<query>{query}</query><doc>{doc}</doc>"
        text = llm(prompt, max_new_tokens=1, temperature=0).strip()
        try:
            scores.append(float(text))
        except ValueError:
            scores.append(float("nan"))
    return scores
