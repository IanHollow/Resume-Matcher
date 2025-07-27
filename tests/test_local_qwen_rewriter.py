import importlib.util
import asyncio
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "apps" / "backend" / "app" / "services" / "local_qwen_rewriter.py"
sys.path.insert(0, str(ROOT / "apps" / "backend"))
sys.modules.setdefault("ollama", types.ModuleType("ollama"))
fastapi_mod = types.ModuleType("fastapi")
fastapi_conc = types.ModuleType("fastapi.concurrency")
def run_in_threadpool(func, *args, **kwargs):
    return func(*args, **kwargs)
fastapi_conc.run_in_threadpool = run_in_threadpool
fastapi_mod.concurrency = fastapi_conc
sys.modules.setdefault("fastapi", fastapi_mod)
sys.modules.setdefault("fastapi.concurrency", fastapi_conc)
openai_mod = types.ModuleType("openai")
openai_mod.OpenAI = object
sys.modules.setdefault("openai", openai_mod)
sys.modules.setdefault("sentence_transformers", types.ModuleType("sentence_transformers"))
sys.modules["sentence_transformers"].SentenceTransformer = object

spec = importlib.util.spec_from_file_location("local_qwen_rewriter", SERVICE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
LocalQwenRewriter = module.LocalQwenRewriter


class DummyEmbedder:
    async def embed(self, text: str):
        if text == "python developer":
            return [1.0, 0.0]
        if "foo" in text:
            return [0.0, 1.0]
        return [1.0, 0.0]


class DummyLLM:
    async def run(self, prompt: str, **kwargs):
        return "improved bullet"


def test_rewrite_builds_patch():
    bullets = ["foo bar", "python guru"]
    job_req = "python developer"
    svc = LocalQwenRewriter(embedder=DummyEmbedder(), llm=DummyLLM(), threshold=0.3)

    patch = asyncio.run(svc.rewrite(bullets, job_req))
    assert any(op["path"] == "/0" for op in patch)

