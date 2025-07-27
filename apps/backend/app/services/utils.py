import functools
import hashlib
from pathlib import Path
from typing import Union

CHUNK_SIZE = 128 * 1024  # 128 KiB


def file_sha256(data_or_path: Union[bytes, str, Path]) -> str:
    """Return SHA-256 hex digest for bytes or file."""
    hasher = hashlib.sha256()
    if isinstance(data_or_path, (str, Path)):
        path = Path(data_or_path)
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                hasher.update(chunk)
    elif isinstance(data_or_path, (bytes, bytearray)):
        hasher.update(data_or_path)
    else:
        raise TypeError("data_or_path must be bytes or path-like")
    return hasher.hexdigest()


@functools.lru_cache(maxsize=None)
def model_sha256(model_path: Union[str, Path]) -> str:
    """Return SHA-256 hex digest for a model file."""
    return file_sha256(model_path)
