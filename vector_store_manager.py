from langchain_google_cloud_sql_pg import PostgresVectorStore
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_core.documents import Document
from typing import List, Dict
import uuid
import json
import logging

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Enhanced vector store with project isolation"""
    
    def __init__(self, db_manager):
        from config import Config
        
        self.db_manager = db_manager
        self.embeddings = VertexAIEmbeddings(
            model_name=Config.EMBEDDING_MODEL,
            project=Config.PROJECT_ID,
        )
        self.vector_store = None
        self._initialized = False
        self.config = Config
    
    async def initialize(self):
        """Initialize vector store"""
        if self._initialized:
            return
        
        try:
            await self.db_manager.initialize()
            await self.db_manager.init_vector_table()
            
            self.vector_store = await PostgresVectorStore.create(
                engine=self.db_manager.engine,
                table_name=self.config.VECTOR_TABLE_NAME,
                embedding_service=self.embeddings,
            )
            
            self._initialized = True
            logger.info("Vector store initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    async def add_documents(
        self,
        documents: List[Document],
        document_id: str,
        project_id: str
    ) -> List[str]:
        """Add documents with project isolation"""
        
        # Enrich metadata
        for doc in documents:
            doc.metadata.update({
                'document_id': document_id,
                'project_id': project_id,
            })
        
        # Generate IDs
        ids = [str(uuid.uuid4()) for _ in documents]
        
        # Store in vector database
        await self.vector_store.aadd_documents(documents, ids=ids)
        
        # Track chunks in metadata table
        chunk_records = [
            (
                ids[idx],
                document_id,
                project_id,
                idx,
                doc.metadata.get('chunk_method', 'unknown'),
                doc.page_content[:500],
                self._estimate_tokens(doc.page_content),
                json.dumps(doc.metadata)
            )
            for idx, doc in enumerate(documents)
        ]
        
        await self._save_chunk_metadata(chunk_records)
        
        return ids
    
    async def _save_chunk_metadata(self, chunk_records: List[tuple]):
        """Save chunk metadata"""
        query = """
            INSERT INTO document_chunks 
            (id, document_id, project_id, chunk_index, chunk_method, 
             content_preview, token_count, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (document_id, chunk_index) DO UPDATE
            SET chunk_method = EXCLUDED.chunk_method,
                content_preview = EXCLUDED.content_preview,
                token_count = EXCLUDED.token_count,
                metadata = EXCLUDED.metadata
        """
        await self.db_manager.execute_many(query, chunk_records)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        return len(text) // 4
    
    async def search_similar(
        self,
        query: str,
        project_id: str,
        k: int = 5,
        filter_dict: dict = None
    ) -> List[Document]:
        """Search with project isolation"""
        
        filters = filter_dict or {}
        filters['project_id'] = project_id
        
        results = await self.vector_store.asimilarity_search(
            query=query,
            k=k,
            filter=filters
        )
        
        return results
    
    async def delete_document_vectors(self, document_id: str, project_id: str):
        """Delete all vectors for a document"""
        
        await self.vector_store.adelete(
            filter={'document_id': document_id, 'project_id': project_id}
        )
        
        query = "DELETE FROM document_chunks WHERE document_id = $1 AND project_id = $2"
        await self.db_manager.execute_query(query, (document_id, project_id))