import functions_framework
import asyncio
import threading
import logging
import google.cloud.logging as cloud_logging
import time
from config import Config
from pipeline_processor import PipelineProcessor # Import at top

# Initialize Cloud Logging
try:
    logging_client = cloud_logging.Client()
    logging_client.setup_logging()
except Exception as e:
    print(f"Warning: Could not setup cloud logging: {e}")

logger = logging.getLogger(__name__)

# --- Persistent Async Loop Setup ---

_LOOP = None
_LOOP_THREAD_LOCK = threading.Lock() # Lock for creating the loop thread
_PROCESSOR = None
_PROCESSOR_LOCK = None # This will become an *asyncio.Lock*

def _start_event_loop():
    """Runs the asyncio event loop in a separate thread."""
    global _LOOP, _PROCESSOR_LOCK
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create the asyncio lock *within the loop it will manage*
        _PROCESSOR_LOCK = asyncio.Lock()
        
        # Signal that the loop and its lock are ready
        _LOOP = loop
        
        loop.run_forever()
    except Exception as e:
        logger.critical(f"Fatal error in async event loop thread: {e}", exc_info=True)
    finally:
        loop.close()

def get_event_loop():
    """
    Gets the single, persistent event loop, starting it
    in a new thread if it doesn't exist.
    """
    global _LOOP
    with _LOOP_THREAD_LOCK:
        if _LOOP is None:
            logger.info("Starting persistent asyncio event loop thread...")
            thread = threading.Thread(target=_start_event_loop, daemon=True)
            thread.start()
            
            # Wait for the loop and its lock to be initialized
            while _LOOP is None or _PROCESSOR_LOCK is None:
                time.sleep(0.01)
                
        return _LOOP

# --- End Persistent Async Loop Setup ---

async def get_processor():
    """
    Get or create processor instance (singleton).
    This is now fully async-safe.
    """
    global _PROCESSOR
    
    # Use the asyncio.Lock with async with.
    # _PROCESSOR_LOCK is guaranteed to exist by get_event_loop()
    async with _PROCESSOR_LOCK:
        if _PROCESSOR is None:
            logger.info("Initializing PipelineProcessor singleton...")
            _PROCESSOR = PipelineProcessor()
            await _PROCESSOR.initialize()
            logger.info("PipelineProcessor initialized.")
            
        return _PROCESSOR

@functions_framework.cloud_event
def process_document_upload(cloud_event):
    """
    Cloud Function triggered by GCS object finalization (SYNCHRONOUS).
    This function bridges the sync world to the async world.
    """
    try:
        # 1. Get the persistent event loop
        loop = get_event_loop()
        
        # 2. Submit the *actual* async logic to that loop thread-safely
        future = asyncio.run_coroutine_threadsafe(
            async_process_document_upload(cloud_event), 
            loop
        )
        
        # 3. Wait for the result and return it
        # You can add a timeout, e.g., timeout=540 (Cloud Functions max)
        return future.result()
        
    except Exception as e:
        logger.error(f"Critical error in sync wrapper: {e}", exc_info=True)
        return {'error': str(e), 'status': 'critical_failure'}

async def async_process_document_upload(cloud_event):
    """Async handler for document processing (RUNS IN THE BACKGROUND LOOP)"""
    data = cloud_event.data
    bucket_name = data['bucket']
    file_path = data['name']
    
    logger.info(f"📥 New file: gs://{bucket_name}/{file_path}")
    
    # Parse project_id from path
    config = Config()
    path_parts = file_path.split('/')
    
    if len(path_parts) < 3 or path_parts[0] != config.DOCUMENTS_PREFIX:
        logger.warning(f"⚠️ Invalid path: {file_path}")
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
    # This await is now safe and correct
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
        
        logger.error(f"✗ Processing failed: {error_msg}", exc_info=True)
        return {
            'error': error_msg,
            'status': 'failed',
            'gcs_uri': gcs_uri
        }
