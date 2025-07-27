import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UTILS_PATH = ROOT / "apps" / "backend" / "app" / "services" / "utils.py"

spec = importlib.util.spec_from_file_location("hash_utils", UTILS_PATH)
hash_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hash_utils)
file_sha256 = hash_utils.file_sha256
model_sha256 = hash_utils.model_sha256


def test_file_sha256_bytes():
    data = b"hello"
    expected = hashlib.sha256(data).hexdigest()
    assert file_sha256(data) == expected


def test_model_sha256_tmp_file(tmp_path):
    file_path = tmp_path / "test.bin"
    content = b"sample content"
    file_path.write_bytes(content)

    first = model_sha256(file_path)
    second = model_sha256(str(file_path))
    assert first == second == hashlib.sha256(content).hexdigest()
