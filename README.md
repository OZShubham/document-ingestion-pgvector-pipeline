# 🌊 DIVE — Document Ingestion, Verification, and Embedding

> DIVE is an end-to-end document intelligence platform that ingests files, extracts and verifies content, produces embeddings, and exposes search and RAG chat capabilities.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18+-61dafb.svg)](https://reactjs.org/)

This repository contains three main components:

- `frontend/` — React + Vite single-page app used by end users
- `backend/` — FastAPI service exposing REST and WebSocket endpoints
- `cloud_function/` — GCP Cloud Function (Gen2) pipeline that processes GCS uploads

Visit the component READMEs for more detail:

- `frontend/README.md` — frontend setup, build and deploy (Vite)
- `backend/README.md` — backend setup, env, run instructions (FastAPI)
- `cloud_function/README.md` — cloud function local testing and deploy

## Quicklinks
- Repo: https://github.com/OZShubham/document-ingestion-pgvector-pipeline
- Owner: Shubham Mishra

## TL;DR — What DIVE does

- Accepts document uploads (PDF, DOCX, XLSX, images, text, etc.)
- Extracts text and metadata using multiple processors (Gemini, PyMuPDF, PyPDF, LangChain processors) with smart fallbacks
- Chunks content with configurable chunking strategies and stores chunk previews
- Generates embeddings (Vertex AI / configured embedding provider) and stores vectors in Cloud SQL (Postgres + pgvector)
- Provides semantic search, analytics, and RAG-style chat with source citations
- Exposes real-time processing status via WebSockets

## Architecture (high level)

The repository implements a modular architecture. Important components:

- Frontend (React) — uploads files and shows processing status, search, and chat UI.
- Backend (FastAPI) — API and WebSocket server. Handles project management, document metadata, queries, and orchestrates search and chat.
- Cloud Storage (GCS) — stores uploaded files under `documents/{project_id}/...`.
- Cloud Function (Gen2) — triggered on new GCS objects; runs extraction, chunking, embedding, and stores results in the DB and vector table.
- Cloud SQL (Postgres) + pgvector — stores metadata, chunks, and vector embeddings.
- Embedding & LLM services — Vertex AI embeddings (or other provider configured via `config.py`) and Gemini or other LLMs for extraction and RAG responses. The pipeline uses many processors — Gemini is one of them, with local processors as fallbacks.

See `docs/ARCHITECTURE.md` (if present) or the folder READMEs for diagrams and deeper details.

## 📁 Project Structure

```
dive/
├── backend/                    # FastAPI Backend
│   ├── main.py                # Main API application
│   ├── config.py              # Configuration
│   ├── database_manager.py   # Database connection
│   ├── vector_store_manager.py # Vector operations
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Container config
│   └── .env                  # Environment variables
│
├── cloud-function/            # Document Processing
│   ├── main.py               # Cloud Function entry
│   ├── pipeline_processor.py # Processing pipeline
│   ├── gemini_processor.py   # Gemini integration
│   ├── document_processors.py # Document handlers
│   ├── chunking_strategies.py # Text chunking
│   ├── config.py             # Configuration
│   ├── requirements.txt      # Dependencies
│   └── .env.yaml            # Environment config
│
├── frontend/                  # React Frontend
│   ├── src/
│   │   ├── App.jsx           # Main application
│   │   ├── config.js         # API client
│   │   ├── components/       # React components
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ProcessingDetail.jsx
│   │   │   ├── DocumentExplorer.jsx
│   │   │   ├── LiveStatusIndicator.jsx
│   │   │   └── MobileNav.jsx
│   │   ├── index.css         # Global styles
│   │   └── main.jsx          # Entry point
│   ├── package.json          # Dependencies
│   ├── vite.config.js        # Vite configuration
│   ├── tailwind.config.js    # Tailwind config
│   └── .env.local           # Environment variables
│
├── docs/                      # Documentation
│   ├── API.md                # API documentation
│   ├── DEPLOYMENT.md         # Deployment guide
│   └── ARCHITECTURE.md       # Architecture details
│
└── README.md                 # This file
```

---

## Endpoints (quick reference)

The backend exposes REST endpoints under `/api` and a WebSocket endpoint for real-time updates. This list is a concise reference; the running app serves full OpenAPI docs at `/docs`.

- Projects
  - GET  /api/projects?user_id={user_id}
  - POST /api/projects
  - DELETE /api/projects/{project_id}?user_id={user_id}

- Documents
  - GET  /api/documents?project_id={pid}&user_id={uid}
  - GET  /api/documents/{document_id}?project_id={pid}&user_id={uid}
  - POST /api/documents/filter  (advanced filters)
  - POST /api/documents/batch   (batch delete/tag/export)
  - DELETE /api/documents/{document_id}?project_id={pid}&user_id={uid}

- Uploads
  - POST /api/upload/signed-url  — request a signed PUT URL for direct GCS upload
  - (UI may use backend proxy endpoints to accept file uploads and write metadata)

- Search & Chat
  - POST /api/search  — semantic search over chunks
  - POST /api/chat    — RAG-style chat (project-scoped)
  - GET  /api/chat/history?project_id={pid}&user_id={uid}

- Analytics
  - GET /api/projects/{project_id}/analytics?user_id={uid}

- Members
  - GET  /api/projects/{project_id}/members?user_id={uid}
  - POST /api/projects/{project_id}/members
  - DELETE /api/projects/{project_id}/members/{member_user_id}?user_id={uid}

- WebSocket
  - WS /api/ws/{project_id}  — receive live processing updates for a project

Tip: start the backend locally and open `http://localhost:8000/docs` to view the live OpenAPI spec.

## Quickstart — run locally (Windows PowerShell)

Prerequisites: Python 3.10+, Node.js 18+, Docker (optional), gcloud CLI (for cloud deploy)

1) Frontend

```powershell
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

2) Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# (set up .env from .env.example)
$env:GOOGLE_APPLICATION_CREDENTIALS = (Resolve-Path .\secrets\credentials.json).Path
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Open http://localhost:8000/docs
```

3) Cloud Function (local test)

```powershell
cd cloud_function
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
functions-framework --target=process_document_upload --signature-type=cloudevent --port=8080
# POST a sample CloudEvent to http://localhost:8080/ to simulate a GCS finalized trigger
```

For full instructions and more configuration, see the component READMEs in each folder.

## Configuration & env

- Backend: `backend/.env.example` contains keys like `GCS_BUCKET_NAME`, `DB_*`, `GCP_PROJECT_ID`, `EMBEDDING_MODEL`, `GEMINI_MODEL`.
- Frontend: `frontend/.env.example` has `VITE_API_URL` and `VITE_GCS_BUCKET`.
- Cloud Function: `cloud_function/requirements.txt` and `cloud_function/main.py` drive the pipeline behavior.

Important note: service account credentials (file found at `backend/secrets/credentials.json` in this repo) are used for local dev only — in production use Workload Identity or Secret Manager.

## Database schema

The DB uses PostgreSQL with `pgvector` installed for vector storage. Core tables include `projects`, `members`, `documents`, `document_chunks`, `document_vectors`, and `processing_logs` (see `backend/migration.py` and `cloud_function/schema.sql` for schema and examples).

## How extraction and processing works (brief)

1. A user uploads a file (frontend or API). Backend stores metadata and either proxies the upload to GCS or returns a signed URL for direct upload.
2. When the object is finalized in GCS under `documents/{project_id}/...`, the Cloud Function is triggered.
3. The Cloud Function pipeline (`pipeline_processor.py`) chooses an extraction strategy:
   - Try Gemini-based extraction (if configured and available)
   - Fallback to local processors (PyMuPDF, pypdf, OCR, LangChain processors) depending on file type
4. Extracted text is chunked via configured chunking strategies (`chunking_strategies.py`) with configurable token/page size.
5. The pipeline generates embeddings (Vertex AI or configured embedding model), stores vectors in `document_vectors`, and updates `documents` and `processing_logs`.
6. The backend serves search/chat requests by querying vectors and optionally combining keyword filters (hybrid search) and then composing RAG prompts for the LLM.

This design intentionally mixes cloud LLM services (Gemini/Vertex) and on-host processors for robustness and cost control.

## Deployment notes

- The repo contains example `cloudbuild.yaml` files and `Dockerfile`s for the frontend and backend. For production deployments we recommend:
  - Backend: Cloud Run (managed) or Cloud Run for Anthos
  - Processing: Cloud Functions (Gen2) or Cloud Run jobs for heavy workloads
  - Database: Cloud SQL (Postgres) with pgvector or a managed vector DB

- Example deploy commands are present in the per-component READMEs. Remember to set IAM roles for the service account: Storage Admin (or Storage Object Admin), Cloud SQL Client, and Vertex AI User where applicable.

## Contributing

See `CONTRIBUTING.md` (if present). Basic workflow:

1. Fork the repo
2. Create a feature branch
3. Run tests and linters
4. Open a pull request

## License

This project is released under the MIT License — see `LICENSE`.

Built with ❤️ — Shubham Mishra
https://github.com/OZShubham/document-ingestion-pgvector-pipeline
