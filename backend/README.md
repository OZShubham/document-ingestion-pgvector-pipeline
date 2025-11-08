# Backend (FastAPI)

This folder contains the FastAPI backend for the Document Ingestion + Vector DB pipeline. The backend exposes REST endpoints (and WebSocket support) used by the frontend and processes document metadata, searching, and coordination with the vector store and Google Cloud Storage.

Files of interest:
- `main.py` — FastAPI application entrypoint
- `database_manager.py`, `vector_store_manager.py` — DB and vector storage helpers
- `migration.py` — database migration helper (simple script)
- `requirements.txt` — Python dependencies
- `secrets/credentials.json` — Google service account credentials (used for GCS and Cloud APIs)

## Prerequisites
- Python 3.10+ (3.11 recommended)
- pip
- Docker (optional, for containerized runs)

## Setup (Windows PowerShell)

1. Create and activate a virtual environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install requirements:

```powershell
pip install -r requirements.txt
```

3. Create a local `.env` file based on `.env.example` and update values (DB credentials, GCP project id, bucket name, etc.).

4. Set Google credentials environment variable (for local development):

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = (Resolve-Path .\secrets\credentials.json).Path
```

Note: In production use secret manager or a secure method to provide credentials.

## Run (development)

Start the app with uvicorn (auto-reload enabled):

```powershell
cd backend
pip install -r requirements.txt
# from repo root: uvicorn backend.main:app --reload --port 8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

By default the API docs are available at `http://localhost:8000/docs`.

## Migrations & Database
- There is a `migration.py` script to help create or seed database schema. Review the script before running against a production DB.

Run tests (example):

```powershell
cd backend
pytest -q
```

## Docker
The `Dockerfile` in this folder builds the backend image. Example build and run:

```powershell
cd backend
docker build -t doc-ingest-backend:latest .
docker run -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/credentials.json `
  -v ${PWD}:/app/secrets `
  -p 8000:8000 doc-ingest-backend:latest
```

Adjust environment variables passed to the container for DB connection, GCP settings, and other secrets.

## Environment variables
See `.env.example` for the list of environment variables used by the backend. Important ones:
- `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_INSTANCE` — database connection config
- `GCP_PROJECT_ID`, `GCS_BUCKET_NAME` — Google Cloud settings
- `API_CORS_ORIGINS` or `FRONTEND_URL` — allowlist for frontend origin(s)

## Notes & Troubleshooting
- Ensure `secrets/credentials.json` exists and points to a service account with access to GCS and Cloud SQL (if used).
- If connection to Cloud SQL is required locally, consider using the Cloud SQL Auth Proxy or the cloud-sql-python-connector.
- If you see CORS errors in the browser, update backend CORS origins or set `FRONTEND_URL`.

If you want CI or deployment steps added (GCP Cloud Run, Cloud Build), I can add example YAML and commands.
