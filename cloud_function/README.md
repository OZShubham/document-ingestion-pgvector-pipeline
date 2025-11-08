# GCP Document Processing Pipeline

Production-ready document processing pipeline with intelligent chunking and vector search.

## Features

✅ Multi-format support (PDF, DOCX, XLSX, TXT, Images)
✅ Intelligent chunking strategies (Recursive, Semantic, Sentence-based)
✅ Vector embeddings with Vertex AI
✅ Project-based isolation
✅ Automatic retry logic
✅ Processing logs and monitoring
✅ Pub/Sub notifications

## Architecture

```
User Upload → GCS → Cloud Function → Document Processing → Vector Store → Search API
                                   ↓
                              Pub/Sub Notifications
```

# Cloud Function: Document Processor

This folder contains the Cloud Function and supporting code that processes documents uploaded to Cloud Storage. The function is triggered when objects under the `documents/{project_id}/...` prefix are finalized and will run the pipeline to extract text, chunk, create embeddings and store vectors and metadata.

Key files:
- `main.py` — Cloud Function entry (functions-framework cloud_event handler)
- `pipeline_processor.py` — Orchestrates document processing
- `document_processors.py`, `chunking_strategies.py` — Extraction & chunking
- `database_manager.py`, `vector_store_manager.py` — DB and vector helpers
- `requirements.txt` — Dependencies used by the function

## Event contract
The function expects objects in GCS under the `documents/{project_id}/{filename}` path. The Cloud Event payload is used to extract `bucket` and `name` and infer `project_id`.

## Prerequisites
- Python 3.10+ runtime locally. Cloud Functions supports Python 3.11 as of this writing.
- `gcloud` CLI configured for your project
- Service account with access to GCS, Cloud SQL, Pub/Sub, and Vertex AI as needed

## Local testing (functions-framework)

Install deps and run locally:

```powershell
cd cloud_function
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run functions-framework to host the cloud event handler locally
# signature-type=cloudevent is appropriate for CloudEvent style triggers
functions-framework --target=process_document_upload --signature-type=cloudevent --port=8080
```

You can POST a sample CloudEvent JSON to `http://localhost:8080/` for a quick integration test.

## Deploying to Cloud Functions (GCP)

Example `gcloud` deploy command (adjust region, runtime and memory):

```powershell
gcloud functions deploy process_document_upload `
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --entry-point=process_document_upload \
  --trigger-event=google.cloud.storage.object.v1.finalized \
  --trigger-resource=YOUR_BUCKET_NAME \
  --memory=2048M \
  --set-env-vars=GCP_PROJECT_ID=your-project,GCS_BUCKET_NAME=your-bucket,PUBSUB_TOPIC=document-processing
```

Notes:
- Use `--region` and `--runtime` values supported by your GCP project.
- For Gen2 Cloud Functions you may also supply a service account with `--service-account`.

## Environment variables
Supply these via `--set-env-vars` (or set them in the Cloud Console):

- `GCP_PROJECT_ID` — GCP project id
- `GCS_BUCKET_NAME` — bucket used for documents
- `DB_INSTANCE`, `DB_REGION`, `DB_NAME`, `DB_USER` — Cloud SQL settings
- `PUBSUB_TOPIC` — notifications topic (optional)
- `EMBEDDING_MODEL`, `GEMINI_MODEL` — AI model names

Also ensure the function has access to credentials (service account) to access GCS and Cloud SQL. For local runs, set `GOOGLE_APPLICATION_CREDENTIALS`:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = (Resolve-Path ..\backend\secrets\credentials.json).Path
```

## Testing / Development helpers
- `test_upload.py` demonstrates uploading a document into the `documents/{project_id}/` prefix and adding metadata. Use this to trigger the function in dev or test environments.
- `setup.py` contains helper steps used during initial setup (database provisioning, seeding, etc.).

## Expected GCS layout

```
gs://{GCS_BUCKET_NAME}/
  documents/
    {project_id}/
      file1.pdf
      file2.docx
```

The function parses `project_id` from the object path — keep uploads under `documents/`.

## Troubleshooting

- Check function logs:

```powershell
gcloud functions logs read process_document_upload --region=us-central1 --limit=50
```

- If processing fails for a file, the function returns a JSON-like error in logs and writes status into the `documents` table. Query the DB for `status = 'failed'`.

## CI / Production notes

- For production deploys prefer Cloud Build or automated CI to run tests and build the deployment.
- Pin dependency versions in `requirements.txt` and run integration tests against a staging GCS bucket and test DB.

## Want me to extend this?
I can add an opinionated `deploy.sh` or Cloud Build config with build + deploy steps, or a sample GitHub Actions workflow to deploy on push to `main`.
