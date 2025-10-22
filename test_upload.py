#!/usr/bin/env python3
'''
Test script to upload a document and trigger processing
'''

from google.cloud import storage
import sys

def upload_document(project_id, local_file_path, user_email):
    '''Upload a document to GCS to trigger processing'''
    
    bucket_name = "your-docs-bucket"  # Replace with your bucket
    
    # Extract filename
    filename = local_file_path.split('/')[-1]
    
    # GCS path format: documents/{project_id}/{filename}
    gcs_path = f"documents/{project_id}/{filename}"
    
    print(f"📤 Uploading {filename} to {gcs_path}...")
    
    # Upload to GCS
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    
    # Set metadata
    blob.metadata = {
        'uploaded_by': user_email,
        'uploader': user_email
    }
    
    # Upload
    blob.upload_from_filename(local_file_path)
    
    print(f"✅ Upload complete!")
    print(f"📍 GCS URI: gs://{bucket_name}/{gcs_path}")
    print(f"🔔 Processing will start automatically...")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python test_upload.py <project_id> <file_path> <user_email>")
        print("Example: python test_upload.py demo-project ./invoice.pdf user@example.com")
        sys.exit(1)
    
    project_id = sys.argv[1]
    file_path = sys.argv[2]
    user_email = sys.argv[3]
    
    upload_document(project_id, file_path, user_email)