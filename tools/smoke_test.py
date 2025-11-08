"""
smoke_test.py

Basic smoke test to exercise an upload + trigger flow. This script supports two modes:

1. Upload mode (default): upload a local file to a GCS bucket under `documents/{project_id}/`.
   If your Cloud Function is deployed and triggered by the bucket, this will start processing.

2. Local invoke mode: upload the file to GCS (optional) and POST a CloudEvent to a local
   functions-framework endpoint to simulate the GCS finalized event. Set LOCAL_FUNCTION_URL.

Environment variables expected:
- SMOKE_PROJECT_ID - GCP project id
- SMOKE_GCS_BUCKET - GCS bucket name
- SMOKE_PROJECT - project id path segment used by the pipeline (project_id)
- GOOGLE_APPLICATION_CREDENTIALS - path to service account JSON (for GCS upload)
- LOCAL_FUNCTION_URL (optional) - http://localhost:8080/ to POST a CloudEvent

Usage example:
  python tools/smoke_test.py ./test_files/sample.pdf my-project-id my-bucket demo-project

Or using local invoke:
  export LOCAL_FUNCTION_URL=http://localhost:8080/
  python tools/smoke_test.py ./test_files/sample.pdf my-project-id my-bucket demo-project

"""
import sys
import os
import json
import time
from google.cloud import storage
import urllib.request
import urllib.error


def upload_to_gcs(local_path, bucket_name, project_id, dest_filename=None):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    filename = dest_filename or os.path.basename(local_path)
    gcs_path = f"documents/{project_id}/{filename}"
    blob = bucket.blob(gcs_path)
    print(f"Uploading {local_path} -> gs://{bucket_name}/{gcs_path}")
    blob.metadata = {"uploaded_by": "smoke-test@example.com"}
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{gcs_path}", gcs_path


def post_cloudevent(local_function_url, bucket, name):
    # Minimal CloudEvent compatible payload (JSON)
    event = {
        "id": f"smoke-{int(time.time())}",
        "type": "google.cloud.storage.object.v1.finalized",
        "source": f"//storage.googleapis.com/{bucket}",
        "data": {
            "bucket": bucket,
            "name": name,
            "metageneration": "1",
            "timeCreated": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "updated": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }
    }

    data = json.dumps(event).encode("utf-8")
    req = urllib.request.Request(local_function_url, data=data, method="POST")
    req.add_header("Content-Type", "application/cloudevents+json")
    print(f"Posting CloudEvent to {local_function_url} (bucket={bucket} name={name})")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            print("Response:", resp.status, body)
    except urllib.error.HTTPError as e:
        print("HTTPError:", e.code, e.read().decode("utf-8"))
    except Exception as e:
        print("Error posting CloudEvent:", e)


def main():
    if len(sys.argv) < 5:
        print("Usage: python tools/smoke_test.py <local-file> <gcp-project-id> <gcs-bucket> <pipeline-project-id>")
        sys.exit(1)

    local_file = sys.argv[1]
    gcp_project = sys.argv[2]
    gcs_bucket = sys.argv[3]
    pipeline_project = sys.argv[4]

    if not os.path.exists(local_file):
        print(f"Local file not found: {local_file}")
        sys.exit(1)

    # Upload to GCS
    gcs_uri, gcs_path = upload_to_gcs(local_file, gcs_bucket, pipeline_project)

    local_fn = os.getenv("LOCAL_FUNCTION_URL")
    if local_fn:
        # When running functions-framework locally, post a CloudEvent to simulate the trigger.
        post_cloudevent(local_fn, gcs_bucket, gcs_path)
    else:
        print("Uploaded file to GCS. If your Cloud Function is deployed and triggers on the bucket, processing should start automatically.")
        print(f"GCS URI: {gcs_uri}")


if __name__ == "__main__":
    main()
