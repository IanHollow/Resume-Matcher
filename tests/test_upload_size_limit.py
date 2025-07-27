import io
from fastapi import UploadFile
from starlette.datastructures import Headers
from test_upload_cache import client


def test_upload_size_limit(client):
    data = b"x" * 3_000_000
    file = UploadFile(io.BytesIO(data), filename="big.pdf", headers=Headers({"content-type": "application/pdf"}))
    files = {"file": (file.filename, file.file, file.content_type)}
    resp = client.post("/api/v1/resumes/upload", files=files)
    assert resp.status_code == 413
