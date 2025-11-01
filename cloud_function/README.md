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

## Prerequisites

1. GCP Project with billing enabled
2. Enable APIs:
   ```bash
   gcloud services enable \
       cloudfunctions.googleapis.com \
       sqladmin.googleapis.com \
       aiplatform.googleapis.com \
       storage.googleapis.com \
       pubsub.googleapis.com
   ```

## Setup

### 1. Create Cloud SQL Instance

```bash
gcloud sql instances create vectordb-instance \
    --database-version=POSTGRES_15 \
    --tier=db-custom-2-7680 \
    --region=us-central1 \
    --database-flags=cloudsql.iam_authentication=On

# Create database
gcloud sql databases create vectordb --instance=vectordb-instance
```

### 2. Create GCS Bucket

```bash
gsutil mb -c standard gs://your-docs-bucket
```

### 3. Create Pub/Sub Topic

```bash
gcloud pubsub topics create document-processing
gcloud pubsub subscriptions create document-processing-sub \
    --topic=document-processing
```

### 4. Initialize Database

```bash
# Connect to database
gcloud sql connect vectordb-instance --user=postgres

# Run schema.sql
\i schema.sql
```

### 5. Deploy Cloud Function

```bash
# Update deploy.sh with your values
chmod +x deploy.sh
./deploy.sh
```

### 6. Run Setup Script

```bash
python setup.py
```

## Usage

### Upload Document via CLI

```bash
python test_upload.py demo-project ./invoice.pdf user@example.com
```

### Upload Document via Python

```python
from google.cloud import storage

client = storage.Client()
bucket = client.bucket('your-docs-bucket')
blob = bucket.blob('documents/project-id/filename.pdf')

blob.metadata = {'uploaded_by': 'user@example.com'}
blob.upload_from_filename('./document.pdf')
```

### Search Documents

```python
from api import search_documents

results = await search_documents(
    query="What are the revenue figures?",
    project_id="demo-project",
    user_id="user123",
    k=5
)

for result in results['results']:
    print(f"Content: {result['content']}")
    print(f"Source: {result['filename']}")
    print(f"---")
```

### Get Document Status

```python
from api import get_document_status

status = await get_document_status(
    document_id="uuid-here",
    project_id="demo-project",
    user_id="user123"
)

print(f"Status: {status['status']}")
print(f"Chunks: {status['chunk_count']}")
print(f"Processing time: {status['metadata']['processing_time_ms']}ms")
```

## Configuration

Environment variables (set in Cloud Function):

- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_REGION` - Region (default: us-central1)
- `GCS_BUCKET_NAME` - GCS bucket name
- `DB_INSTANCE` - Cloud SQL instance name
- `DB_REGION` - Cloud SQL region
- `DB_NAME` - Database name
- `USE_IAM_AUTH` - Use IAM auth (default: true)
- `PUBSUB_TOPIC` - Pub/Sub topic name
- `EMBEDDING_MODEL` - Vertex AI embedding model
- `GEMINI_MODEL` - Gemini model for processing

## Project Structure

```
.
├── schema.sql              # Database schema
├── requirements.txt        # Python dependencies
├── config.py              # Configuration
├── document_processors.py  # Document processing logic
├── chunking_strategies.py  # Chunking strategies
├── database_manager.py     # Database management
├── vector_store_manager.py # Vector store management
├── pipeline_processor.py   # Main pipeline
├── main.py                # Cloud Function entry point
├── api.py                 # Search API
├── deploy.sh              # Deployment script
├── setup.py               # Setup script
├── test_upload.py         # Test upload script
└── README.md              # This file
```

## File Organization

Expected GCS structure:
```
gs://your-bucket/
└── documents/
    ├── project-1/
    │   ├── file1.pdf
    │   └── file2.docx
    └── project-2/
        └── file3.xlsx
```

## Supported File Types

- **PDFs**: Uses Gemini, PyMuPDF, or PyPDF (with fallback)
- **Images**: JPEG, PNG, WebP (via Gemini)
- **Documents**: DOCX, DOC
- **Spreadsheets**: XLSX, XLS
- **Text**: TXT, MD, CSV, HTML

## Chunking Strategies

1. **Recursive** (default): Splits on paragraph, sentence, word boundaries
2. **Semantic**: Uses embeddings to find natural breakpoints
3. **Sentence**: Splits by sentences with size limits

Configure per-project in database:
```sql
UPDATE projects 
SET settings = '{"chunk_method": "semantic"}'::jsonb
WHERE id = 'project-id';
```

## Monitoring

### View Logs

```bash
# Function logs
gcloud functions logs read doc-processor --region=us-central1

# Database logs
gcloud sql operations list --instance=vectordb-instance
```

### View Processing Status

```sql
-- Recent documents
SELECT filename, status, processing_method, created_at, processed_at
FROM documents
ORDER BY created_at DESC
LIMIT 10;

-- Processing logs
SELECT d.filename, pl.stage, pl.status, pl.duration_ms
FROM processing_logs pl
JOIN documents d ON pl.document_id = d.id
WHERE d.filename = 'your-file.pdf'
ORDER BY pl.created_at;

-- Failed documents
SELECT filename, error_message, retry_count
FROM documents
WHERE status = 'failed';
```

## Performance Optimization

### Batch Processing

For bulk uploads, consider:
1. Upload multiple files
2. Process in parallel (Cloud Function auto-scales)
3. Monitor with processing_logs table

### Memory Optimization

- Adjust Cloud Function memory based on file sizes
- Large PDFs (>50MB): Use 4-8GB memory
- Regular documents: 2-4GB memory

### Cost Optimization

- Use Cloud Function min instances = 0 for dev
- Set max instances to control costs
- Use Cloud SQL connection pooling

## Troubleshooting

### Document Processing Fails

1. Check Cloud Function logs:
   ```bash
   gcloud functions logs read doc-processor --region=us-central1 --limit=50
   ```

2. Check document status:
   ```sql
   SELECT * FROM documents WHERE status = 'failed';
   ```

3. Retry failed document:
   ```python
   from pipeline_processor import PipelineProcessor
   
   processor = PipelineProcessor()
   await processor.initialize()
   await processor.retry_failed_document(document_id, project_id)
   ```

### Connection Issues

1. Verify IAM permissions
2. Check Cloud SQL instance is running
3. Verify network connectivity

### Slow Processing

1. Check processing_logs for bottlenecks
2. Consider using Gemini for faster extraction
3. Adjust chunk size for faster embedding

## Security

### IAM Authentication

The pipeline uses IAM authentication by default:
- No passwords stored
- Service account based
- Automatic credential rotation

### Row-Level Security

Enable RLS for multi-tenant isolation:
```sql
-- Set user context before queries
SET app.current_user_id = 'user123';

-- Queries automatically filtered by project access
SELECT * FROM documents;
```

### Data Encryption

- Data encrypted at rest (Cloud SQL)
- Data encrypted in transit (TLS)
- Vector embeddings stored securely

## Advanced Usage

### Custom Processing Method

Add custom processor:

```python
from document_processors import BaseDocumentProcessor, ProcessedDocument

class CustomProcessor(BaseDocumentProcessor):
    def supports(self, mime_type: str) -> bool:
        return mime_type == 'application/custom'
    
    async def process(self, file_bytes: bytes, filename: str, **kwargs) -> ProcessedDocument:
        # Your custom processing logic
        return ProcessedDocument(
            text="extracted text",
            metadata={},
            processing_method='custom'
        )

# Register in DocumentProcessorFactory
factory.processors['custom'] = CustomProcessor()
```

### Custom Chunking Strategy

```python
from chunking_strategies import ChunkingStrategy

class CustomChunker(ChunkingStrategy):
    async def chunk(self, text: str, metadata: Dict = None) -> List[Document]:
        # Your custom chunking logic
        return documents

# Register in ChunkingFactory
factory.strategies['custom'] = CustomChunker()
```

### Hybrid Search

Combine vector similarity with keyword search:

```python
# Add to vector_store_manager.py
async def hybrid_search(
    self,
    query: str,
    project_id: str,
    k: int = 5
) -> List[Document]:
    # Vector search
    vector_results = await self.vector_store.asimilarity_search(
        query=query,
        k=k,
        filter={'project_id': project_id}
    )
    
    # Keyword search (full-text)
    keyword_query = '''
        SELECT dc.id, dc.content_preview
        FROM document_chunks dc
        WHERE dc.project_id = $1
        AND to_tsvector('english', dc.content_preview) @@ plainto_tsquery('english', $2)
        LIMIT $3
    '''
    
    keyword_results = await self.db_manager.fetch_all(
        keyword_query, (project_id, query, k)
    )
    
    # Combine and re-rank results
    # (implement your ranking logic)
    
    return combined_results
```

## API Integration Examples

### FastAPI Endpoint

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from api import search_documents, get_document_status

app = FastAPI()

class SearchRequest(BaseModel):
    query: str
    project_id: str
    k: int = 5

@app.post("/search")
async def search(request: SearchRequest, user_id: str):
    try:
        results = await search_documents(
            query=request.query,
            project_id=request.project_id,
            user_id=user_id,
            k=request.k
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents/{document_id}/status")
async def status(document_id: str, project_id: str, user_id: str):
    try:
        status = await get_document_status(
            document_id=document_id,
            project_id=project_id,
            user_id=user_id
        )
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
```

### React Frontend Example

```javascript
// Upload document
async function uploadDocument(file, projectId, userEmail) {
  const formData = new FormData();
  formData.append('file', file);
  
  // Upload to your backend, which uploads to GCS
  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData,
    headers: {
      'X-Project-ID': projectId,
      'X-User-Email': userEmail
    }
  });
  
  const { documentId } = await response.json();
  
  // Poll for status
  return pollDocumentStatus(documentId, projectId);
}

// Search documents
async function searchDocuments(query, projectId) {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, project_id: projectId })
  });
  
  return response.json();
}

// Get document status
async function pollDocumentStatus(documentId, projectId) {
  const maxAttempts = 60;
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    const response = await fetch(
      `/api/documents/${documentId}/status?project_id=${projectId}`
    );
    
    const status = await response.json();
    
    if (status.status === 'completed') {
      return status;
    } else if (status.status === 'failed') {
      throw new Error(status.error_message);
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
    attempts++;
  }
  
  throw new Error('Processing timeout');
}
```

## Testing

### Unit Tests

```python
# test_processors.py
import pytest
from document_processors import PyPDFProcessor

@pytest.mark.asyncio
async def test_pdf_processing():
    processor = PyPDFProcessor()
    
    with open('test_files/sample.pdf', 'rb') as f:
        file_bytes = f.read()
    
    result = await processor.process(file_bytes, 'sample.pdf')
    
    assert result.error is None
    assert len(result.text) > 0
    assert result.processing_method == 'pypdf'

# Run tests
pytest test_processors.py
```

### Integration Tests

```python
# test_pipeline.py
import pytest
from pipeline_processor import PipelineProcessor

@pytest.mark.asyncio
async def test_end_to_end_processing():
    processor = PipelineProcessor()
    await processor.initialize()
    
    result = await processor.process_document(
        gcs_uri='gs://test-bucket/documents/test-project/sample.pdf',
        project_id='test-project',
        uploaded_by='test@example.com'
    )
    
    assert result['status'] == 'success'
    assert result['chunks_count'] > 0
```

## Maintenance

### Database Backups

```bash
# Automated backups (daily)
gcloud sql backups create \
    --instance=vectordb-instance \
    --description="Manual backup"

# Restore from backup
gcloud sql backups restore BACKUP_ID \
    --backup-instance=vectordb-instance \
    --backup-project=your-project
```

### Clean Up Old Documents

```sql
-- Soft delete old documents
UPDATE documents 
SET deleted_at = NOW()
WHERE created_at < NOW() - INTERVAL '90 days'
AND status = 'completed';

-- Delete old logs
DELETE FROM processing_logs
WHERE created_at < NOW() - INTERVAL '30 days';
```

### Update Dependencies

```bash
# Update requirements
pip list --outdated
pip install --upgrade package-name

# Test
python -m pytest

# Redeploy
./deploy.sh
```

## Cost Estimation

Approximate monthly costs for 10,000 documents/month:

- Cloud Functions: $20-50
- Cloud SQL (db-custom-2-7680): $130
- Cloud Storage: $5
- Vertex AI Embeddings: $40-80
- Pub/Sub: $1
- **Total: ~$200-270/month**

Optimize costs:
- Use smaller Cloud SQL instance for dev
- Set Cloud Function max instances
- Archive old documents to Coldline storage

## Migration Guide

### From Existing System

1. Export existing documents
2. Create projects in database
3. Bulk upload to GCS with correct structure
4. Processing triggers automatically
5. Verify in database

### Database Migration

```sql
-- Add new columns
ALTER TABLE documents ADD COLUMN new_field TEXT;

-- Migrate data
UPDATE documents SET new_field = existing_field || '_new';

-- Deploy new version
./deploy.sh
```

## Support

- **Documentation**: This README
- **Issues**: Check Cloud Function logs
- **Community**: GCP Community forums
- **Enterprise**: Contact GCP support

## License

MIT License - See LICENSE file

## Contributors

- Your Name <your.email@example.com>

## Changelog

### v1.0.0 (2024-01-20)
- Initial release
- Multi-format document support
- Intelligent chunking
- Vector search with project isolation
- Monitoring and logging

---

**Built with ❤️ using Google Cloud Platform**