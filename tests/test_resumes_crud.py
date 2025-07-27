import sys
import types
import importlib.util
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
    import db.models  # ensure models are registered

    services_stub = types.ModuleType("app.services")

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

    monkeypatch.setattr(resume_module, "model_sha256", lambda _: "modelhash")

    resume_doc_path = ROOT / "apps" / "backend" / "app" / "api" / "router" / "v1" / "resume_doc.py"
    doc_spec = importlib.util.spec_from_file_location("resume_doc_module", resume_doc_path)
    resume_doc_module = importlib.util.module_from_spec(doc_spec)
    doc_spec.loader.exec_module(resume_doc_module)
    orig_validate = resume_doc_module.ResumeDocModel.model_validate

    def _patched(cls, obj, *a, **kw):
        if not isinstance(obj, dict):
            obj = {
                "id": obj.id,
                "hash": obj.hash,
                "modelHash": obj.model_hash,
                "filename": obj.filename,
                "displayName": obj.display_name,
                "uploadDt": obj.upload_dt,
            }
        return orig_validate(obj, *a, **kw)

    resume_doc_module.ResumeDocModel.model_validate = classmethod(_patched)

    app = FastAPI()

    import anyio
    anyio.run(database.init_models, Base)

    app.include_router(resume_module.resume_router, prefix="/api/v1/resumes")
    app.include_router(resume_doc_module.resume_doc_router, prefix="/api/v1/resumes")

    with TestClient(app) as c:
        yield c


def test_resumes_crud(client):
    data = b"%PDF-1.4\n%%EOF"
    files = {"file": ("test.pdf", data, "application/pdf")}

    r = client.post("/api/v1/resumes/upload", files=files)
    assert r.status_code == 201
    res = r.json()
    assert res.get("resume_id")

    r = client.get("/api/v1/resumes")
    assert r.status_code == 200
    docs = r.json()
    assert any(d["filename"] == "test.pdf" for d in docs)
    doc = next(d for d in docs if d["filename"] == "test.pdf")
    doc_id = doc["id"]

    new_name = "renamed.pdf"
    r = client.patch(f"/api/v1/resumes/{doc_id}", json={"displayName": new_name})
    assert r.status_code == 200
    assert r.json()["displayName"] == new_name

    r = client.delete(f"/api/v1/resumes/{doc_id}")
    assert r.status_code == 204

    r = client.get(f"/api/v1/resumes/{doc_id}")
    assert r.status_code == 404
