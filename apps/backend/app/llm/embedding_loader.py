import os
import logging
import shlex
from typing import Any, Dict, List

try:
    from ctransformers import AutoModelForCausalLM, Config
except Exception:  # pragma: no cover - optional dependency
    AutoModelForCausalLM = None  # type: ignore[misc]
    Config = None  # type: ignore[misc]

logger = logging.getLogger(__name__)


def _convert_value(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_llama_args(env: str | None = None) -> Dict[str, Any]:
    """Parse LLAMA_ARGS style environment variables into kwargs."""
    raw = env if env is not None else os.getenv("LLAMA_ARGS", "")
    args: Dict[str, Any] = {}
    for token in shlex.split(raw):
        if "=" in token:
            key, val = token.split("=", 1)
            args[key.lstrip("-").replace("-", "_")] = _convert_value(val)
        else:
            args[token.lstrip("-").replace("-", "_")] = True
    return args


def get_embedding(text: str, model_path: str, llama_args: Dict[str, Any] | None = None) -> List[float]:
    """Return the embedding vector for *text* using a GGUF model."""
    if AutoModelForCausalLM is None or Config is None:
        raise RuntimeError("ctransformers is not available")

    kwargs = parse_llama_args() if llama_args is None else llama_args
    if "n_gpu_layers" in kwargs:
        kwargs["gpu_layers"] = kwargs.pop("n_gpu_layers")
    if "n_threads" in kwargs:
        kwargs["threads"] = kwargs.pop("n_threads")
    if "n_ctx" in kwargs:
        kwargs["context_length"] = kwargs.pop("n_ctx")

    try:
        llm = AutoModelForCausalLM.from_pretrained(model_path, config=Config(**kwargs))
        return llm.embed(text)
    except Exception as e:  # pragma: no cover - runtime error if model missing
        logger.error("embedding generation failed: %s", e)
        raise
