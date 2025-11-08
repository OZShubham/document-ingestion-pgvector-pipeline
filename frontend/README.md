# Frontend (React + Vite)

This folder contains the React single-page application (SPA) for the Document Ingestion + Vector DB pipeline. It is built with Vite and React and talks to the backend API.

Key points:
- Built with Vite (dev server + HMR)
- Scripts are defined in `package.json` (dev, build, preview, lint)
- Environment variables start with `VITE_` and are provided in `.env.example`

## Prerequisites
- Node.js 18+ (LTS recommended)
- npm (or yarn/pnpm)

## Quick start (Windows PowerShell)

Install dependencies:

```powershell
cd frontend
npm install
```

Run the dev server (hot reload):

```powershell
npm run dev
```

Open http://localhost:5173 in your browser (Vite prints the exact URL).

Build for production:

```powershell
npm run build
```

Preview the production build locally:

```powershell
npm run preview
```

Linting:

```powershell
npm run lint
```

## Environment variables
Copy `.env.example` to `.env` (or create a `.env.local`) and update values. Important variables:

- `VITE_API_URL` — base URL for the backend API (e.g. `http://localhost:8000/api`)
- `VITE_GCS_BUCKET` — (optional) GCS bucket name used by the UI for previews

Example (.env or PowerShell set):

```powershell
$env:VITE_API_URL = 'http://localhost:8000/api'
# Or create a .env file in the frontend folder
```

## Docker
There is a `Dockerfile` in this folder to build the frontend image. Example (PowerShell):

```powershell
cd frontend
docker build -t doc-ingest-frontend:latest .
# Run static server (example using httpd/nginx) or use a multi-stage Dockerfile produced image
```

## Notes
- The frontend expects the backend API to expose endpoints under `/api`.
- If the backend runs on a different host/port, update `VITE_API_URL` before building.

If you need help wiring auth or CORS settings, update the backend `main.py` CORS allow list (`FRONTEND_URL` env) so the browser can call the API.
