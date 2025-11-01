
#!/bin/bash
set -e

# Configuration
PROJECT_ID="your-gcp-project"
REGION="us-central1"
FUNCTION_NAME="doc-processor"
BUCKET_NAME="your-docs-bucket"
DB_INSTANCE="your-db-instance"
DB_REGION="us-central1"
DB_NAME="vectordb"

echo "🚀 Deploying Document Processing Pipeline..."

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcf-admin-robot.iam.gserviceaccount.com"

echo "📦 Service Account: $SERVICE_ACCOUNT"

# Grant IAM roles
echo "🔐 Setting up IAM permissions..."

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.objectViewer" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/pubsub.publisher" \
    --condition=None

# Deploy Cloud Function
echo "☁️  Deploying Cloud Function..."

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python312 \
    --region=$REGION \
    --source=. \
    --entry-point=process_document_upload \
    --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
    --trigger-event-filters="bucket=$BUCKET_NAME" \
    --trigger-location=$REGION \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID" \
    --set-env-vars="GCP_REGION=$REGION" \
    --set-env-vars="GCS_BUCKET_NAME=$BUCKET_NAME" \
    --set-env-vars="DB_INSTANCE=$DB_INSTANCE" \
    --set-env-vars="DB_REGION=$DB_REGION" \
    --set-env-vars="DB_NAME=$DB_NAME" \
    --set-env-vars="USE_IAM_AUTH=true" \
    --set-env-vars="PUBSUB_TOPIC=document-processing" \
    --memory=4096MB \
    --timeout=540s \
    --max-instances=100 \
    --min-instances=0 \
    --cpu=2 \
    --service-account=$SERVICE_ACCOUNT

echo "✅ Deployment completed!"
echo ""
echo "📊 Function details:"
gcloud functions describe $FUNCTION_NAME --region=$REGION --gen2 --format="table(name,state,updateTime)"
