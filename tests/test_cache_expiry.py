import sys
import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from freezegun import freeze_time


@pytest.fixture
def client(monkeypatch):
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "apps" / "backend"))

    mem = "file:memdb_cache?mode=memory&cache=shared"
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

    resume_path = ROOT / "apps" / "backend" / "app" / "api" / "router" / "v1" / "resume.py"
    spec = importlib.util.spec_from_file_location("resume_module", resume_path)
    resume_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resume_module)

    monkeypatch.setattr(resume_module.ResumeService, "convert_and_store_resume", ResumeService.convert_and_store_resume)
    monkeypatch.setattr(resume_module, "model_sha256", lambda _: "modelhash")

    app = FastAPI()
    import anyio
    anyio.run(database.init_models, Base)
    app.include_router(resume_module.resume_router, prefix="/api/v1/resumes")

    with TestClient(app) as c:
        yield c


def test_cache_expiry(client):
    data = b"%PDF-1.4\n%%EOF"
    files = {"file": ("test.pdf", data, "application/pdf")}

    with freeze_time("2025-06-27"):
        r1 = client.post("/api/v1/resumes/upload", files=files)
        assert r1.status_code == 201

    with freeze_time("2025-07-02"):
        r2 = client.post("/api/v1/resumes/upload", files=files, follow_redirects=False)
        assert r2.status_code == 303

    with freeze_time("2025-07-29"):
        r3 = client.post("/api/v1/resumes/upload", files=files)
        assert r3.status_code == 201
