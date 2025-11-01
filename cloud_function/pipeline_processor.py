import time
import json
from datetime import datetime
from google.cloud import storage
from typing import Dict, Any
import logging
import asyncio
import traceback

logger = logging.getLogger(__name__)

class PipelineProcessor:
    """Enhanced pipeline with smart Gemini handling and document updates"""
    
    def __init__(self):
        from config import Config
        from gemini_processor import SmartDocumentProcessorFactory
        from chunking_strategies import ChunkingFactory
        from database_manager import DatabaseManager
        
        # FIXED: Create Config instance
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.vector_manager = None
        self.doc_processor = SmartDocumentProcessorFactory()
        self.chunking_factory = ChunkingFactory()
        self.storage_client = storage.Client(project=self.config.PROJECT_ID)
    
    async def initialize(self):
        """Initialize all components"""
        from vector_store_manager import VectorStoreManager
        try:
            # DB manager initializes its pool on first use
            self.vector_manager = VectorStoreManager(self.db_manager)
            await self.vector_manager.initialize()
            logger.info("✅ Enhanced pipeline processor initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize pipeline: {e}")
            raise
    
    async def process_document(
        self,
        gcs_uri: str,
        project_id: str,
        uploaded_by: str
    ) -> Dict[str, Any]:
        """Main document processing pipeline with smart update handling"""
        
        document_id = None
        start_time = time.time()
        
        try:
            # Extract file info
            filename = gcs_uri.split('/')[-1]
            mime_type = self._get_mime_type(filename)
            
            logger.info(f"📄 Processing: {filename} ({mime_type})")
            
            # Download file
            file_bytes = await self._download_file(gcs_uri)
            file_size = len(file_bytes)
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"📦 File size: {file_size_mb:.2f}MB")
            
            # Check file size against limits
            if file_size > self.config.MAX_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(f"File size {file_size_mb:.1f}MB exceeds {self.config.MAX_FILE_SIZE_MB}MB limit")
            
            # UPDATED: Smart document creation/update handling
            document_id, is_new, should_skip = await self._create_or_update_document_record(
                project_id, filename, gcs_uri, mime_type, file_size, uploaded_by
            )
            
            if is_new:
                logger.info(f"✨ Created new document record: {document_id}")
            else:
                logger.info(f"♻️ Processing existing/updated document: {document_id}")
            
            # Check if we should skip processing (document already completed and unchanged)
            if should_skip:
                logger.info(f"⏩ Skipping already completed document: {document_id}")
                return {
                    'status': 'skipped',
                    'document_id': document_id,
                    'filename': filename,
                    'reason': 'Document already processed successfully'
                }
            
            # ====== STEP 1: Extract content with smart processor ======
            await self._log_stage(document_id, project_id, 'extraction', 'started')
            extraction_start = time.time()
            
            # Use enhanced processor with automatic fallback
            processed_doc = await self.doc_processor.process_document(
                file_bytes=file_bytes,
                filename=filename,
                mime_type=mime_type
            )
            
            extraction_time = int((time.time() - extraction_start) * 1000)
            
            if processed_doc.error:
                raise Exception(f"Extraction failed: {processed_doc.error}")
            
            # Check for warnings (truncation, etc.)
            extraction_metadata = {
                'method': processed_doc.processing_method,
                'file_size_mb': file_size_mb,
                'is_update': not is_new
            }
            
            if processed_doc.metadata and 'warning' in processed_doc.metadata:
                logger.warning(f"⚠️ Processing warning: {processed_doc.metadata['warning']}")
                extraction_metadata['warning'] = processed_doc.metadata['warning']
                extraction_metadata['truncated'] = True
                
                # Log warning separately
                await self._log_stage(
                    document_id, project_id, 'extraction', 'warning',
                    metadata={'warning': processed_doc.metadata['warning']}
                )
            
            await self._log_stage(
                document_id, project_id, 'extraction', 'completed',
                duration_ms=extraction_time,
                metadata=extraction_metadata
            )
            
            logger.info(f"✅ Extraction completed in {extraction_time}ms using {processed_doc.processing_method}")
            
            # ====== STEP 2: Intelligent chunking ======
            await self._log_stage(document_id, project_id, 'chunking', 'started')
            chunking_start = time.time()
            
            chunk_method = 'recursive'  # Default
            
            chunk_metadata = {
                'filename': filename,
                'file_type': mime_type,
                'uploaded_by': uploaded_by,
                'processing_method': processed_doc.processing_method,
                'has_tables': len(processed_doc.tables) > 0,
                'has_images': len(processed_doc.images) > 0,
                'page_count': processed_doc.page_count,
                'is_update': not is_new
            }
            
            # Add truncation info to chunk metadata if present
            if processed_doc.metadata and 'warning' in processed_doc.metadata:
                chunk_metadata['warning'] = processed_doc.metadata['warning']
                chunk_metadata['total_pages'] = processed_doc.metadata.get('total_pages')
                chunk_metadata['processed_pages'] = processed_doc.metadata.get('processed_pages')
            
            documents = await self.chunking_factory.chunk_text(
                text=processed_doc.text,
                method=chunk_method,
                metadata=chunk_metadata
            )
            
            chunking_time = int((time.time() - chunking_start) * 1000)
            
            logger.info(f"✅ Created {len(documents)} chunks using {chunk_method} in {chunking_time}ms")
            
            await self._log_stage(
                document_id, project_id, 'chunking', 'completed',
                duration_ms=chunking_time,
                metadata={'chunk_count': len(documents), 'method': chunk_method}
            )
            
            # ====== STEP 3: Generate embeddings ======
            await self._log_stage(document_id, project_id, 'embedding', 'started')
            embedding_start = time.time()
            
            chunk_ids = await self.vector_manager.add_documents(
                documents, str(document_id), project_id
            )
            
            embedding_time = int((time.time() - embedding_start) * 1000)
            
            logger.info(f"✅ Stored {len(chunk_ids)} embeddings in {embedding_time}ms")
            
            await self._log_stage(
                document_id, project_id, 'embedding', 'completed',
                duration_ms=embedding_time,
                metadata={'embedding_count': len(chunk_ids)}
            )
            
            # ====== STEP 4: Update document status ======
            total_time = int((time.time() - start_time) * 1000)
            
            final_metadata = {
                'chunks_count': len(documents),
                'chunk_method': chunk_method,
                'has_tables': len(processed_doc.tables) > 0,
                'has_images': len(processed_doc.images) > 0,
                'tables_count': len(processed_doc.tables),
                'images_count': len(processed_doc.images),
                'processing_time_ms': total_time,
                'file_size_mb': file_size_mb,
                'is_update': not is_new
            }
            
            # Add warning to final metadata if present
            if processed_doc.metadata and 'warning' in processed_doc.metadata:
                final_metadata['warning'] = processed_doc.metadata['warning']
                final_metadata['truncated'] = True
            
            await self._update_document_status(
                document_id,
                status='completed',
                processing_method=processed_doc.processing_method,
                page_count=processed_doc.page_count,
                metadata=final_metadata
            )
            
            # ====== STEP 5: Publish notification ======
            notification_metadata = {
                'chunks_count': len(documents),
                'processing_method': processed_doc.processing_method,
                'is_update': not is_new
            }
            
            # Add warning to notification if present
            if processed_doc.metadata and 'warning' in processed_doc.metadata:
                notification_metadata['warning'] = processed_doc.metadata['warning']
            
            await self._publish_notification(
                document_id, project_id, 'completed',
                metadata=notification_metadata
            )
            
            logger.info(f"🎉 Document {document_id} processed successfully in {total_time}ms")
            
            return {
                'status': 'success',
                'document_id': str(document_id),
                'filename': filename,
                'chunks_count': len(documents),
                'processing_method': processed_doc.processing_method,
                'processing_time_ms': total_time,
                'is_update': not is_new,
                'warning': processed_doc.metadata.get('warning') if processed_doc.metadata else None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Processing failed: {error_msg}\n{traceback.format_exc()}")
            
            if document_id:
                await self._update_document_status(
                    document_id,
                    status='failed',
                    error_message=error_msg
                )
                await self._log_stage(
                    document_id, project_id, 'pipeline', 'failed',
                    error_details=error_msg
                )
                await self._publish_notification(
                    document_id, project_id, 'failed', error=error_msg
                )
            
            raise
    
    # ========================================================================
    # SMART DOCUMENT UPDATE HANDLING
    # ========================================================================
    
    async def _create_or_update_document_record(
        self,
        project_id: str,
        filename: str,
        gcs_uri: str,
        file_type: str,
        file_size: int,
        uploaded_by: str,
        file_hash: str = None
    ) -> tuple:
        """
        Create or update document record with smart handling
        
        Returns:
            tuple: (document_id, is_new, should_skip)
        """
        
        # First check if document already exists
        check_query = """
            SELECT id, status, file_size, created_at, updated_at, metadata
            FROM documents 
            WHERE gcs_uri = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        pool = await self.db_manager._get_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(check_query, gcs_uri)
            
            if existing:
                doc_id = str(existing['id'])
                old_status = existing['status']
                old_file_size = existing['file_size']
                
                logger.info(f"📋 Document exists: {doc_id} (status: {old_status})")
                
                # Detect if file was updated (size changed)
                file_updated = (old_file_size != file_size)
                
                if file_updated:
                    logger.info(f"🔄 File updated detected! Old size: {old_file_size}, New size: {file_size}")
                    
                    # Archive old version and create new record
                    await self._archive_old_version(conn, doc_id)
                    
                    # Create new version
                    new_doc_id = await self._create_new_document_version(
                        conn, project_id, filename, gcs_uri, file_type, 
                        file_size, uploaded_by, doc_id
                    )
                    
                    logger.info(f"✨ Created new version: {new_doc_id} (previous: {doc_id})")
                    return str(new_doc_id), False, False  # Not new, but updated, should process
                
                # File not updated - decide based on status
                if old_status == 'completed':
                    logger.info(f"✅ Document already processed successfully - skipping")
                    return doc_id, False, True  # Existing doc, should skip
                
                elif old_status == 'failed':
                    logger.info(f"♻️ Previous processing failed - retrying")
                    await self._reset_for_reprocessing(conn, doc_id)
                    return doc_id, False, False  # Existing doc, should process
                
                elif old_status == 'processing':
                    # Check if stuck (processing for too long)
                    updated_at = existing['updated_at']
                    time_elapsed = datetime.now() - updated_at.replace(tzinfo=None) if updated_at.tzinfo else datetime.now() - updated_at
                    
                    if time_elapsed.total_seconds() > self.config.TIMEOUT_SECONDS:
                        logger.warning(f"⏰ Document stuck in processing - retrying")
                        await self._reset_for_reprocessing(conn, doc_id)
                        return doc_id, False, False  # Existing doc, should process
                    else:
                        logger.info(f"⏳ Document currently being processed - skipping (processed {time_elapsed.total_seconds():.0f}s ago)")
                        # Return without processing to avoid duplicates
                        raise Exception(f"Document is currently being processed by another instance")
                
                else:
                    # Unknown status - reset and retry
                    await self._reset_for_reprocessing(conn, doc_id)
                    return doc_id, False, False  # Existing doc, should process
            
            # Document doesn't exist - create new
            logger.info(f"✨ Creating new document record")
            query = """
                INSERT INTO documents
                (project_id, filename, gcs_uri, file_type, file_size, uploaded_by, status, retry_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """
            
            document_id = await conn.fetchval(
                query,
                project_id, 
                filename, 
                gcs_uri, 
                file_type, 
                file_size, 
                uploaded_by, 
                'processing',
                0  # retry_count
            )
        
        return str(document_id), True, False  # New doc, should process
    
    async def _archive_old_version(self, conn, old_doc_id: str):
        """Archive old version by marking it as superseded"""
        query = """
            UPDATE documents
            SET status = 'archived',
                metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
                    'archived', true,
                    'superseded_at', CURRENT_TIMESTAMP::text
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        await conn.execute(query, old_doc_id)
        logger.info(f"📦 Archived old version: {old_doc_id}")
    
    async def _create_new_document_version(
        self, 
        conn, 
        project_id: str, 
        filename: str, 
        gcs_uri: str, 
        file_type: str, 
        file_size: int, 
        uploaded_by: str,
        previous_version_id: str
    ) -> str:
        """Create new document version"""
        query = """
            INSERT INTO documents
            (project_id, filename, gcs_uri, file_type, file_size, uploaded_by, status, retry_count, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """
        
        metadata = {
            'previous_version_id': previous_version_id,
            'version': 'updated',
            'is_update': True
        }
        
        document_id = await conn.fetchval(
            query,
            project_id, 
            filename, 
            gcs_uri, 
            file_type, 
            file_size, 
            uploaded_by, 
            'processing',
            0,
            json.dumps(metadata)
        )
        
        return str(document_id)
    
    async def _reset_for_reprocessing(self, conn, doc_id: str):
        """Reset document status for reprocessing"""
        query = """
            UPDATE documents
            SET status = 'processing',
                retry_count = retry_count + 1,
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        await conn.execute(query, doc_id)
        
        # Also delete old embeddings to avoid stale data
        delete_embeddings_query = """
            DELETE FROM document_vectors WHERE document_id = $1
        """
        deleted = await conn.execute(delete_embeddings_query, doc_id)
        logger.info(f"🗑️ Deleted old embeddings for document {doc_id}: {deleted}")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    # Add this helper function
    async def send_websocket_update(
        project_id: str,
        document_id: str,
        status: str,
        data: dict
    ):
        """Send update via API to broadcast through WebSocket"""
        try:
            # Get your backend API URL from environment variable
            api_url = os.getenv('API_URL', 'http://localhost:8000')
            
            # Use a system user ID for Cloud Function calls
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{api_url}/api/projects/{project_id}/broadcast",
                    json={
                        "type": "document_update",
                        "document_id": document_id,
                        "status": status,
                        "data": data,
                        "timestamp": datetime.now().isoformat()
                    },
                    params={"user_id": "system"},
                    timeout=5.0
                )
                logger.info(f"✅ Sent WebSocket update for document {document_id}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to send WebSocket update: {e}")
   
    def _get_mime_type(self, filename: str) -> str:
        """Determine MIME type from filename"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'
   
    async def _download_file(self, gcs_uri: str) -> bytes:
        """Download file from GCS"""
        def _sync_download():
            parts = gcs_uri.replace('gs://', '').split('/', 1)
            bucket_name = parts[0]
            blob_path = parts[1]
           
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            return blob.download_as_bytes()
       
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_download)
   
    async def _update_document_status(
        self,
        document_id: str,
        status: str,
        processing_method: str = None,
        page_count: int = None,
        error_message: str = None,
        metadata: Dict = None
    ):
        """Update document status"""
        query = """
            UPDATE documents
            SET status = $1,
                processing_method = $2,
                page_count = $3,
                error_message = $4,
                processed_at = $5,
                metadata = $6,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $7
        """
        
        pool = await self.db_manager._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                query,
                status,
                processing_method,
                page_count,
                error_message,
                datetime.now() if status in ['completed', 'failed'] else None,
                json.dumps(metadata) if metadata else None,
                document_id
            )
   
    async def _log_stage(
        self,
        document_id: str,
        project_id: str,
        stage: str,
        status: str,
        duration_ms: int = None,
        error_details: str = None,
        metadata: Dict = None
    ):
        """Log processing stage"""
        query = """
            INSERT INTO processing_logs
            (document_id, project_id, stage, status, duration_ms, error_details, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        
        pool = await self.db_manager._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                query,
                document_id,
                project_id,
                stage,
                status,
                duration_ms,
                error_details,
                json.dumps(metadata) if metadata else None
            )
   
    async def _publish_notification(
        self,
        document_id: str,
        project_id: str,
        status: str,
        error: str = None,
        metadata: Dict = None
    ):
        """Publish notification to Pub/Sub"""
        from google.cloud import pubsub_v1
       
        def _sync_publish():
            try:
                publisher = pubsub_v1.PublisherClient()
                topic_path = publisher.topic_path(self.config.PROJECT_ID, self.config.PUBSUB_TOPIC)
               
                message = {
                    'document_id': str(document_id),
                    'project_id': str(project_id),
                    'status': status,
                    'timestamp': datetime.now().isoformat(),
                    'error': error,
                    'metadata': metadata
                }
               
                future = publisher.publish(
                    topic_path,
                    json.dumps(message).encode('utf-8'),
                    document_id=str(document_id),
                    project_id=str(project_id),
                    status=status
                )
               
                return future.result(timeout=5.0)
            except Exception as e:
                logger.warning(f"⚠️ Failed to publish notification: {e}")
                return None
       
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_publish)