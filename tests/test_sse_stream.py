import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "apps" / "backend"))

    db_file = tmp_path / "test.db"
    monkeypatch.setenv("SYNC_DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("ASYNC_DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("SESSION_SECRET_KEY", "test")

    from app.core import database
    from apps.backend.app.models.base import Base
    import db.models

    services_stub = types.ModuleType("app.services")

    class ResumeService:
        def __init__(self, *a, **k):
            pass

        async def convert_and_store_resume(self, *a, **k):
            return "rid"

    class ScoreImprovementService:
        def __init__(self, *a, **k):
            pass

        async def run(self, *a, **k):
            return {}

        def run_and_stream(self, *a, **k):
            async def gen():
                for i in range(5):
                    yield f"event: progress\ndata: {i}\n\n"
                yield "event: rewrite\ndata: {}\n\n"
                for i in range(5, 9):
                    yield f"event: progress\ndata: {i}\n\n"
                yield "event: patch\ndata: []\n\n"

            return gen()

    services_stub.ResumeService = ResumeService
    services_stub.ScoreImprovementService = ScoreImprovementService
    services_stub.ResumeNotFoundError = Exception
    services_stub.ResumeParsingError = Exception
    services_stub.ResumeValidationError = Exception
    services_stub.JobNotFoundError = Exception
    services_stub.JobParsingError = Exception
    services_stub.ResumeKeywordExtractionError = Exception
    services_stub.JobKeywordExtractionError = Exception
    sys.modules.setdefault("app.services", services_stub)

    utils_path = ROOT / "apps" / "backend" / "app" / "services" / "utils.py"
    util_spec = importlib.util.spec_from_file_location("app.services.utils", utils_path)
    utils_module = importlib.util.module_from_spec(util_spec)
    util_spec.loader.exec_module(utils_module)
    sys.modules["app.services.utils"] = utils_module

    resume_path = ROOT / "apps" / "backend" / "app" / "api" / "router" / "v1" / "resume.py"
    spec = importlib.util.spec_from_file_location("resume_module", resume_path)
    resume_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resume_module)

    app = FastAPI()

    import anyio
    anyio.run(database.init_models, Base)

    app.include_router(resume_module.resume_router, prefix="/api/v1/resumes")

    with TestClient(app) as c:
        yield c


def _parse_event(chunk: str) -> dict:
    event: dict = {}
    for part in chunk.split("\n"):
        if part.startswith("event:"):
            event["event"] = part.split(":", 1)[1].strip()
        elif part.startswith("data:"):
            data = part.split(":", 1)[1].strip()
            if data:
                try:
                    event["data"] = json.loads(data)
                except Exception:
                    event["data"] = data
    return event


def test_improve_stream_order(client):
    payload = {
        "resume_id": "00000000-0000-0000-0000-000000000000",
        "job_id": "00000000-0000-0000-0000-000000000000",
    }
    events = []
    with client.stream("POST", "/api/v1/resumes/improve?stream=true", json=payload) as resp:
        buffer = ""
        for chunk in resp.iter_text():
            buffer += chunk
            while "\n\n" in buffer:
                raw, buffer = buffer.split("\n\n", 1)
                if raw:
                    events.append(_parse_event(raw))

    names = [e["event"] for e in events]
    assert names[0] == "progress"
    assert names[-1] == "patch"
    assert "rewrite" in names
    assert names.count("patch") == 1
    assert len(events) >= 10
    first_rewrite = names.index("rewrite")
    assert all(n == "progress" for n in names[:first_rewrite])
