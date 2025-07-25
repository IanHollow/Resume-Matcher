# syntax=docker/dockerfile:1
FROM python:3.12-slim
WORKDIR /usr/src/app

# ── install FastAPI stack
ENV PIP_ROOT_USER_ACTION=ignore PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── copy source
COPY . .

# ── expose & launch (running as root is OK in root‑less Podman)
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
