import time
import json
from datetime import datetime
from google.cloud import storage
from typing import Dict, Any
import logging
import asyncio
import traceback

logger = logging.getLogger(__name__)

class EnhancedPipelineProcessor:
    """Enhanced pipeline with smart Gemini handling"""
    
    def __init__(self):
        from config import Config
        # ====== UPDATED: Use SmartDocumentProcessorFactory ======
        from gemini_processor import SmartDocumentProcessorFactory
        from chunking_strategies import ChunkingFactory
        from database_manager import DatabaseManager
        
        
        self.config = Config
        self.db_manager = DatabaseManager()
        self.vector_manager = None
        self.doc_processor = SmartDocumentProcessorFactory()  # ← NEW
        self.chunking_factory = ChunkingFactory()
        self.storage_client = storage.Client(project=Config.PROJECT_ID)
    
    async def initialize(self):
        """Initialize all components"""
        from vector_store_manager import VectorStoreManager
        try:
            await self.db_manager.initialize()
            self.vector_manager = VectorStoreManager(self.db_manager)
            await self.vector_manager.initialize()
            logger.info("Enhanced pipeline processor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize pipeline: {e}")
            raise
    
    async def process_document(
        self,
        gcs_uri: str,
        project_id: str,
        uploaded_by: str
    ) -> Dict[str, Any]:
        """Main document processing pipeline with enhanced error handling"""
        
        document_id = None
        start_time = time.time()
        
        try:
            # Extract file info
            filename = gcs_uri.split('/')[-1]
            mime_type = self._get_mime_type(filename)
            
            logger.info(f"Processing: {filename} ({mime_type})")
            
            # Download file
            file_bytes = await self._download_file(gcs_uri)
            file_size = len(file_bytes)
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"File size: {file_size_mb:.2f}MB")
            
            # Check file size against limits
            if file_size > self.config.MAX_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(f"File size {file_size_mb:.1f}MB exceeds {self.config.MAX_FILE_SIZE_MB}MB limit")
            
            # Create document record
            document_id = await self._create_document_record(
                project_id, filename, gcs_uri, mime_type, file_size, uploaded_by
            )
            
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
            
            # ====== NEW: Check for warnings (truncation, etc.) ======
            extraction_metadata = {
                'method': processed_doc.processing_method,
                'file_size_mb': file_size_mb
            }
            
            if processed_doc.metadata and 'warning' in processed_doc.metadata:
                logger.warning(f"Processing warning: {processed_doc.metadata['warning']}")
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
            
            logger.info(f"Created {len(documents)} chunks using {chunk_method}")
            
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
            
            logger.info(f"Stored {len(chunk_ids)} embeddings")
            
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
                'processing_method': processed_doc.processing_method
            }
            
            # Add warning to notification if present
            if processed_doc.metadata and 'warning' in processed_doc.metadata:
                notification_metadata['warning'] = processed_doc.metadata['warning']
            
            await self._publish_notification(
                document_id, project_id, 'completed',
                metadata=notification_metadata
            )
            
            logger.info(f"✓ Document {document_id} processed in {total_time}ms")
            
            return {
                'status': 'success',
                'document_id': str(document_id),
                'filename': filename,
                'chunks_count': len(documents),
                'processing_method': processed_doc.processing_method,
                'processing_time_ms': total_time,
                'warning': processed_doc.metadata.get('warning') if processed_doc.metadata else None
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"✗ Processing failed: {error_msg}\n{traceback.format_exc()}")
            
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
            
            raise e
   
    def _get_mime_type(self, filename: str) -> str:
        """Determine MIME type"""
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
   
    async def _create_document_record(
        self,
        project_id: str,
        filename: str,
        gcs_uri: str,
        file_type: str,
        file_size: int,
        uploaded_by: str
    ) -> str:
        """Create document record"""
        query = """
            INSERT INTO documents
            (project_id, filename, gcs_uri, file_type, file_size, uploaded_by, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        result = await self.db_manager.execute_query(
            query,
            (project_id, filename, gcs_uri, file_type, file_size, uploaded_by, 'processing')
        )
        return result.fetchone()[0]
   
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
                metadata = $6
            WHERE id = $7
        """
        await self.db_manager.execute_query(
            query,
            (
                status,
                processing_method,
                page_count,
                error_message,
                datetime.now() if status in ['completed', 'failed'] else None,
                json.dumps(metadata) if metadata else None,
                document_id
            )
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
        await self.db_manager.execute_query(
            query,
            (
                document_id,
                project_id,
                stage,
                status,
                duration_ms,
                error_details,
                json.dumps(metadata) if metadata else None
            )
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
       
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_publish)
 