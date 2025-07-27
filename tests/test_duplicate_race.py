import sys
import importlib.util
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class DummyEmbedder:
    async def embed(self, text: str):
        return [0.0]


@pytest.fixture
def client(monkeypatch):
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "apps" / "backend"))

    mem = "file:memdb_race?mode=memory&cache=shared"
    sync_url = f"sqlite:///{mem}&uri=true"
    async_url = f"sqlite+aiosqlite:///{mem}&uri=true"
    monkeypatch.setenv("SYNC_DATABASE_URL", sync_url)
    monkeypatch.setenv("ASYNC_DATABASE_URL", async_url)
    monkeypatch.setenv("SESSION_SECRET_KEY", "test")

    from app.core import database
    from apps.backend.app.models.base import Base
    import db.models

    services_stub = importlib.util.module_from_spec(
        importlib.machinery.ModuleSpec("app.services", None)
    )

    class ResumeService:
        def __init__(self, *a, **k):
            pass

        async def convert_and_store_resume(self, *a, **k):
            return "rid"

    services_stub.ResumeService = ResumeService
    services_stub.ScoreImprovementService = object()
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

    manager_path = ROOT / "apps" / "backend" / "app" / "agent" / "manager.py"
    manager_spec = importlib.util.spec_from_file_location("manager_module", manager_path)
    manager_module = importlib.util.module_from_spec(manager_spec)
    manager_spec.loader.exec_module(manager_module)
    monkeypatch.setattr(manager_module.EmbeddingManager, "embed", DummyEmbedder.embed, raising=False)

    resume_path = ROOT / "apps" / "backend" / "app" / "api" / "router" / "v1" / "resume.py"
    spec = importlib.util.spec_from_file_location("resume_module", resume_path)
    resume_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resume_module)

    doc_path = ROOT / "apps" / "backend" / "app" / "api" / "router" / "v1" / "resume_doc.py"
    doc_spec = importlib.util.spec_from_file_location("resume_doc_module", doc_path)
    resume_doc_module = importlib.util.module_from_spec(doc_spec)
    doc_spec.loader.exec_module(resume_doc_module)

    monkeypatch.setattr(resume_module.ResumeService, "convert_and_store_resume", ResumeService.convert_and_store_resume)
    monkeypatch.setattr(resume_module, "model_sha256", lambda _: "modelhash")

    app = FastAPI()
    import anyio
    anyio.run(database.init_models, Base)
    app.include_router(resume_module.resume_router, prefix="/api/v1/resumes")
    app.include_router(resume_doc_module.resume_doc_router, prefix="/api/v1/resumes")

    with TestClient(app) as c:
        yield c


def test_no_duplicate_on_race(client):
    data = b"%PDF-1.4\n%%EOF"
    files = {"file": ("test.pdf", data, "application/pdf")}

    def send():
        resp = client.post("/api/v1/resumes/upload", files=files)
        assert resp.status_code in {201, 303}

    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(lambda _: send(), range(3)))

    from app.core import database
    from sqlalchemy import select, func
    from db import ResumeDoc

    with database.SessionLocal() as session:
        count = session.scalar(select(func.count()).select_from(ResumeDoc))

    assert count == 1
