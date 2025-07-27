import sys
from pathlib import Path
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
    import importlib.util
    import types

    services_stub = types.ModuleType("app.services")
    class ResumeService:  # minimal stub
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

    async def fake_convert_and_store_resume(self, *args, **kwargs):
        return "rid"

    monkeypatch.setattr(resume_module.ResumeService, "convert_and_store_resume", fake_convert_and_store_resume)
    monkeypatch.setattr(resume_module, "model_sha256", lambda _: "modelhash")

    app = FastAPI()

    import anyio
    anyio.run(database.init_models, Base)

    app.include_router(resume_module.resume_router, prefix="/api/v1/resumes")

    with TestClient(app) as c:
        yield c


def test_upload_cached(client):
    data = b"%PDF-1.4\n%%EOF"
    files = {"file": ("test.pdf", data, "application/pdf")}

    r1 = client.post("/api/v1/resumes/upload", files=files)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/resumes/upload", files=files, follow_redirects=False)
    assert r2.status_code == 303
