import json
import math
from typing import List, Dict, AsyncGenerator

import numpy as np
import sys
import importlib

if "fastapi" in sys.modules and not hasattr(sys.modules["fastapi"], "FastAPI"):
    del sys.modules["fastapi"]
    if "fastapi.concurrency" in sys.modules:
        del sys.modules["fastapi.concurrency"]
    sys.modules["fastapi"] = importlib.import_module("fastapi")

from app.agent import EmbeddingManager, AgentManager


class LocalQwenRewriter:
    """Rewrite low-similarity resume bullets using local Qwen3-8B."""

    def __init__(
        self,
        embedder: EmbeddingManager | None = None,
        llm: AgentManager | None = None,
        threshold: float = 0.30,
    ) -> None:
        self.embedder = embedder or EmbeddingManager()
        self.llm = llm or AgentManager(model="qwen3:8b")
        self.threshold = threshold

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        if a.size == 0 or b.size == 0:
            return 0.0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    @staticmethod
    def _build_patch(replacements: Dict[int, str]) -> List[Dict[str, str]]:
        """Return RFC-6902 patch operations from index->text mapping."""
        patch = []
        for idx, text in replacements.items():
            patch.append({"op": "replace", "path": f"/{idx}", "value": text})
        return patch

    async def rewrite(self, bullets: List[str], job_requirements: str) -> List[Dict[str, str]]:
        """Return JSON patch replacing low-similarity bullets."""
        req_emb = await self.embedder.embed(job_requirements)
        req_emb = np.asarray(req_emb)
        replacements: Dict[int, str] = {}
        for i, bullet in enumerate(bullets):
            emb = await self.embedder.embed(bullet)
            sim = self._cosine(np.asarray(emb), req_emb)
            if sim < self.threshold:
                prompt = (
                    "Rewrite the following resume bullet to better match the job requirements.\n"
                    f"Requirements: {job_requirements}\nBullet: {bullet}"
                )
                new_bullet = await self.llm.run(prompt)
                if isinstance(new_bullet, dict):
                    new_bullet = new_bullet.get("response", "")
                replacements[i] = str(new_bullet).strip()
        return self._build_patch(replacements)

    async def rewrite_and_stream(
        self, bullets: List[str], job_requirements: str
    ) -> AsyncGenerator[str, None]:
        """Yield SSE events for progress with JSON patch at the end."""
        total = len(bullets)
        req_emb = await self.embedder.embed(job_requirements)
        req_emb = np.asarray(req_emb)
        replacements: Dict[int, str] = {}
        for idx, bullet in enumerate(bullets, 1):
            emb = await self.embedder.embed(bullet)
            sim = self._cosine(np.asarray(emb), req_emb)
            if sim < self.threshold:
                prompt = (
                    "Rewrite the following resume bullet to better match the job requirements.\n"
                    f"Requirements: {job_requirements}\nBullet: {bullet}"
                )
                new_bullet = await self.llm.run(prompt)
                if isinstance(new_bullet, dict):
                    new_bullet = new_bullet.get("response", "")
                replacements[idx - 1] = str(new_bullet).strip()
            progress = math.floor((idx / total) * 10) * 10
            if idx == total or (idx / total) * 100 % 10 == 0:
                yield f"data: {json.dumps({'progress': progress})}\n\n"
        patch = self._build_patch(replacements)
        yield f"data: {json.dumps({'patch': patch})}\n\n"

