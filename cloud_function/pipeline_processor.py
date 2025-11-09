import time
import json
from datetime import datetime
from google.cloud import storage
from typing import Dict, Any
import logging
import asyncio
import traceback
import httpx
import os

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
            
            # *** UPDATED: Smart document creation/update handling ***
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
        Implements an "Upsert" (Update/Insert) logic.
        
        - If file is new, creates a new document record.
        - If file exists, clears old data (chunks, vectors) and resets the 
          document for reprocessing.

        Returns:
            tuple: (document_id, is_new, should_skip)
        """
        
        # Look for an existing document with this STABLE GCS_URI
        check_query = """
            SELECT id, status, file_size
            FROM documents 
            WHERE gcs_uri = $1 AND project_id = $2 AND deleted_at IS NULL
        """
        
        pool = await self.db_manager._get_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(check_query, gcs_uri, project_id)
            
            if existing:
                # === UPDATE (OVERWRITE) PATH ===
                doc_id = str(existing['id'])
                old_status = existing['status']
                old_file_size = existing['file_size']
                
                # Check if the file is *actually* different.
                # If GCS just sends a duplicate event for a file that's already
                # processed and the size is the same, we can skip.
                if old_status == 'completed' and old_file_size == file_size:
                    logger.info(f"✅ Document {doc_id} is unchanged and already completed. Skipping.")
                    return doc_id, False, True # (doc_id, is_new=False, should_skip=True)

                logger.info(f"📋 Document exists: {doc_id} (status: {old_status}). Clearing old data for reprocessing.")

                # 1. Delete old vector data from vector store
                await self.vector_manager.delete_document_vectors(doc_id, project_id)

                # 2. Delete old data from relational DB (chunks and logs)
                async with conn.transaction():
                    await conn.execute("DELETE FROM document_chunks WHERE document_id = $1", doc_id)
                    await conn.execute("DELETE FROM processing_logs WHERE document_id = $1", doc_id)
                
                    # 3. Update the main document record to trigger reprocessing
                    update_query = """
                        UPDATE documents
                        SET 
                            status = 'processing',
                            file_size = $1,
                            file_type = $2,
                            uploaded_by = $3,
                            created_at = CURRENT_TIMESTAMP, -- Reset creation time
                            processed_at = NULL,
                            error_message = NULL,
                            retry_count = 0,
                            metadata = '{}'::jsonb -- Clear all old metadata
                        WHERE id = $4
                    """
                    await conn.execute(
                        update_query,
                        file_size,
                        file_type,
                        uploaded_by,
                        doc_id
                    )
                
                # Return (doc_id, is_new=False, should_skip=False)
                return doc_id, False, False

            else:
                # === INSERT (NEW FILE) PATH ===
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
                    'processing',  # Set to processing, as this function *is* the processor
                    0  # retry_count
                )
        
                # Return (new_doc_id, is_new=True, should_skip=False)
                return str(document_id), True, False
    
    async def _reset_for_reprocessing(self, conn, doc_id: str):
        """Reset a 'failed' or 'stuck' document for reprocessing"""
        logger.info(f"♻️ Resetting document {doc_id} for reprocessing.")
        
        # 1. Delete old vector data
        # We pass None for project_id because it's not strictly needed by the
        # vector_manager.delete_document_vectors method as long as doc_id is present.
        await self.vector_manager.delete_document_vectors(doc_id, None) 

        # 2. Delete old chunks and logs (inside a transaction)
        async with conn.transaction():
            await conn.execute("DELETE FROM document_chunks WHERE document_id = $1", doc_id)
            await conn.execute("DELETE FROM processing_logs WHERE document_id = $1", doc_id)
            
            # 3. Reset document status
            query = """
                UPDATE documents
                SET status = 'processing',
                    retry_count = retry_count + 1,
                    error_message = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            """
            await conn.execute(query, doc_id)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    # Helper function for WebSocket updates
    async def send_websocket_update(
        self,
        *,  # Force keyword arguments
        project_id: str,
        document_id: str,
        status: str,
        data: dict
    ):
        """Send update via API to broadcast through WebSocket"""
        try:
            # Get backend API URL from config
            api_url = self.config.API_URL
            
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
            RETURNING project_id
        """
        
        pool = await self.db_manager._get_pool()
        async with pool.acquire() as conn:
            project_id = await conn.fetchval(
                query,
                status,
                processing_method,
                page_count,
                error_message,
                datetime.now() if status in ['completed', 'failed'] else None,
                json.dumps(metadata) if metadata else None,
                document_id
            )
            
            # Send WebSocket update for status changes
            if project_id:
                await self.send_websocket_update(
                    project_id=str(project_id),
                    document_id=document_id,
                    status=status,
                    data={
                        'processing_method': processing_method,
                        'page_count': page_count,
                        'error_message': error_message,
                        'metadata': metadata
                    }
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
            
            # Send WebSocket update for stage progress
            stage_data = {
                'stage': stage,
                'status': status,
                'duration_ms': duration_ms,
                'error_details': error_details,
                'metadata': metadata
            }
            
            await self.send_websocket_update(
                project_id=str(project_id),
                document_id=document_id,
                status=f"{stage}_{status}",
                data=stage_data
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
