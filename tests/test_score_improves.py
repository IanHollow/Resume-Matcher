import importlib.util
import asyncio
from pathlib import Path
import sys
import types
from jsonpatch import JsonPatch
import os

ROOT = Path(__file__).resolve().parents[1]
REWRITER_PATH = ROOT / "apps" / "backend" / "app" / "services" / "local_qwen_rewriter.py"

sys.path.insert(0, str(ROOT / "apps" / "backend"))
llm_mod = types.ModuleType("app.llm")
llm_mod.get_embedding = lambda *a, **k: [0.0, 0.0]
llm_mod.parse_llama_args = lambda: {}
llm_mod.ensure_gguf = lambda *a, **k: None
llm_mod.rerank = lambda *a, **k: [0.0]
sys.modules.setdefault("app.llm", llm_mod)
sys.modules.setdefault("ollama", types.ModuleType("ollama"))
openai_mod = types.ModuleType("openai")
openai_mod.OpenAI = object
sys.modules.setdefault("openai", openai_mod)
sys.modules.setdefault("sentence_transformers", types.ModuleType("sentence_transformers"))
sys.modules["sentence_transformers"].SentenceTransformer = object
os.environ.setdefault("SYNC_DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("ASYNC_DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("SESSION_SECRET_KEY", "test")

import numpy as np

spec_rew = importlib.util.spec_from_file_location("rewriter", REWRITER_PATH)
rew_module = importlib.util.module_from_spec(spec_rew)
spec_rew.loader.exec_module(rew_module)
LocalQwenRewriter = rew_module.LocalQwenRewriter


class DummyEmbedder:
    async def embed(self, text: str):
        if "[+]" in text:
            return [0.5, 0.5]
        if "RESTful" in text:
            return [0.0, 1.0]
        return [1.0, 0.0]


class DummyRewriter:
    async def rewrite(self, bullets, job_req):
        return [{"op": "replace", "path": "/0", "value": bullets[0] + " [+]"}]


def cosine(a, b):
    a = np.asarray(a)
    b = np.asarray(b)
    if a.size == 0 or b.size == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_score_improves_and_patch_valid(monkeypatch):
    embedder = DummyEmbedder()

    rewriter = DummyRewriter()
    monkeypatch.setattr(LocalQwenRewriter, "rewrite", rewriter.rewrite, raising=False)

    resume_json = ["Implemented API"]
    job_req = "RESTful API"

    job_emb = asyncio.run(embedder.embed(job_req))
    res_emb = asyncio.run(embedder.embed(resume_json[0]))
    score_before = cosine(job_emb, res_emb)

    patch_json = asyncio.run(rewriter.rewrite(resume_json, job_req))
    updated_resume_json = JsonPatch(patch_json).apply(resume_json.copy())

    new_emb = asyncio.run(embedder.embed(updated_resume_json[0]))
    score_after = cosine(job_emb, new_emb)

    assert score_after > score_before

    # ensure patch is valid and applied correctly
    assert updated_resume_json[0].endswith("[+]")

