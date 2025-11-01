import functions_framework
import asyncio
import threading
import logging
import google.cloud.logging as cloud_logging
 
# Initialize Cloud Logging
try:
    logging_client = cloud_logging.Client()
    logging_client.setup_logging()
except Exception as e:
    print(f"Warning: Could not setup cloud logging: {e}")
 
logger = logging.getLogger(__name__)
 
# Global processor instance
_processor = None
_processor_lock = threading.Lock()
 
async def get_processor():
    """Get or create processor instance (singleton)"""
    global _processor
   
    with _processor_lock:
        if _processor is None:
            from pipeline_processor import PipelineProcessor
            _processor = PipelineProcessor()
            await _processor.initialize()
       
        return _processor
 
@functions_framework.cloud_event
def process_document_upload(cloud_event):
    """
    Cloud Function triggered by GCS object finalization
    Expected path: gs://bucket/documents/{project_id}/{filename}
    """
    return asyncio.run(async_process_document_upload(cloud_event))
 
async def async_process_document_upload(cloud_event):
    """Async handler for document processing"""
    from config import Config
   
    data = cloud_event.data
    bucket_name = data['bucket']
    file_path = data['name']
   
    logger.info(f"📥 New file: gs://{bucket_name}/{file_path}")
   
    # Parse project_id from path
    config = Config()
    path_parts = file_path.split('/')
   
    if len(path_parts) < 3 or path_parts[0] != config.DOCUMENTS_PREFIX:
        logger.warning(f"⚠️  Invalid path: {file_path}")
        return {
            'error': 'Invalid file path format',
            'expected': 'documents/{project_id}/{filename}'
        }
   
    project_id = path_parts[1]
    gcs_uri = f"gs://{bucket_name}/{file_path}"
   
    # Get metadata
    metadata = data.get('metadata', {})
    uploaded_by = metadata.get('uploaded_by', metadata.get('uploader', 'unknown'))
   
    # Process document
    processor = await get_processor()
   
    try:
        result = await processor.process_document(
            gcs_uri=gcs_uri,
            project_id=project_id,
            uploaded_by=uploaded_by
        )
       
        logger.info(f"✓ Processing completed: {result}")
        return result
       
    except Exception as e:
        error_msg = str(e)
        
        # Handle duplicate processing gracefully
        if "currently being processed" in error_msg.lower():
            logger.info(f"ℹ️ Skipping duplicate processing request for {gcs_uri}")
            return {
                'status': 'skipped',
                'reason': 'Document is already being processed',
                'gcs_uri': gcs_uri
            }
        
        logger.error(f"✗ Processing failed: {error_msg}")
        return {
            'error': error_msg,
            'status': 'failed',
            'gcs_uri': gcs_uri
        }