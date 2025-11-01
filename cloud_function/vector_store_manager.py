from langchain_google_vertexai import VertexAIEmbeddings
from langchain_core.documents import Document
from typing import List, Dict, Optional
import uuid
import json
import logging

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Enhanced vector store with project isolation using direct asyncpg queries."""

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
        """Initialize vector store and tables (loop-safe)."""
        if self._initialized:
            logger.info("✅ Vector store already initialized")
            return

        try:
            logger.info("🔧 Initializing vector store...")
            
            # Ensure connector + pool + vector extension exists
            await self.db_manager.init_vector_extension()

            # Create vector table (if not exists)
            await self.db_manager.init_vector_table()

            # Ensure metadata table for chunks
            create_chunks_table = """
            CREATE TABLE IF NOT EXISTS document_chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID NOT NULL,
                project_id UUID NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_method TEXT,
                content_preview TEXT,
                token_count INTEGER,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(document_id, chunk_index)
            );
            """
            await self.db_manager.execute_query(create_chunks_table)

            # Indexes for chunks table
            await self.db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS document_chunks_document_idx 
                ON document_chunks(document_id);
            """)
            
            await self.db_manager.execute_query("""
                CREATE INDEX IF NOT EXISTS document_chunks_project_idx 
                ON document_chunks(project_id);
            """)
            
            logger.info("✅ Vector store initialized successfully")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize vector store: {e}", exc_info=True)
            raise

    async def add_documents(
        self,
        documents: List[Document],
        document_id: str,
        project_id: str
    ) -> List[str]:
        """
        Add documents with project isolation.
        
        Args:
            documents: List of LangChain Document objects
            document_id: UUID of the parent document
            project_id: UUID of the project
            
        Returns:
            List of chunk IDs that were inserted
        """
        if not documents:
            logger.warning("⚠️ No documents to add")
            return []

        try:
            logger.info(f"📝 Adding {len(documents)} chunks for document {document_id}")

            # Enrich metadata and get contents
            contents = []
            for idx, doc in enumerate(documents):
                metadata = doc.metadata or {}
                metadata.update({
                    'document_id': document_id,
                    'project_id': project_id,
                    'chunk_index': idx
                })
                doc.metadata = metadata
                contents.append(doc.page_content)

            # Get embeddings from Vertex AI (async)
            logger.info("🔮 Generating embeddings...")
            embeddings = await self.embeddings.aembed_documents(contents)
            logger.info(f"✅ Generated {len(embeddings)} embeddings")

            # Generate unique IDs for chunks
            ids = [str(uuid.uuid4()) for _ in documents]

            # Insert into vector table
            insert_query = f"""
                INSERT INTO {self.config.VECTOR_TABLE_NAME}
                (id, document_id, project_id, chunk_index, content, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO NOTHING;
            """

            pool = await self.db_manager._get_pool()
            async with pool.acquire() as conn:
                async with conn.transaction():
                    for idx, doc in enumerate(documents):
                        meta_json = json.dumps(doc.metadata)
                        emb = embeddings[idx]
                        
                        await conn.execute(
                            insert_query,
                            ids[idx],
                            document_id,
                            project_id,
                            idx,
                            doc.page_content,
                            emb,  # asyncpg accepts Python list for vector column
                            meta_json
                        )

            logger.info(f"✅ Inserted {len(documents)} vectors into database")

            # Save chunk metadata in document_chunks table
            chunk_records = [
                (
                    ids[idx],
                    document_id,
                    project_id,
                    idx,
                    doc.metadata.get('chunk_method', 'unknown'),
                    doc.page_content[:500],  # Preview first 500 chars
                    self._estimate_tokens(doc.page_content),
                    json.dumps(doc.metadata)
                )
                for idx, doc in enumerate(documents)
            ]
            await self._save_chunk_metadata(chunk_records)

            logger.info(f"✅ Successfully added {len(documents)} document chunks for project {project_id}")
            return ids

        except Exception as e:
            logger.error(f"❌ Failed to add documents: {e}", exc_info=True)
            raise

    async def _save_chunk_metadata(self, chunk_records: List[tuple]):
        """Save chunk metadata to document_chunks table"""
        query = """
            INSERT INTO document_chunks 
            (id, document_id, project_id, chunk_index, chunk_method, 
             content_preview, token_count, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (document_id, chunk_index) DO UPDATE
            SET chunk_method = EXCLUDED.chunk_method,
                content_preview = EXCLUDED.content_preview,
                token_count = EXCLUDED.token_count,
                metadata = EXCLUDED.metadata;
        """
        
        pool = await self.db_manager._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                for record in chunk_records:
                    await conn.execute(query, *record)
        
        logger.info(f"✅ Saved metadata for {len(chunk_records)} chunks")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 1 token ≈ 4 chars)"""
        return max(1, len(text) // 4)

    async def search_similar(
        self,
        query: str,
        project_id: str,
        k: int = 5,
        filter_dict: Optional[dict] = None
    ) -> List[Document]:
        """
        Search with project isolation using cosine similarity.
        
        Args:
            query: Search query text
            project_id: Project UUID to search within
            k: Number of results to return
            filter_dict: Additional filters (optional)
            
        Returns:
            List of Document objects with similarity scores
        """
        try:
            logger.info(f"🔍 Searching for '{query[:50]}...' in project {project_id}")

            # Compute query embedding
            query_emb = await self.embeddings.aembed_query(query)
            
            # Build SQL with cosine distance operator (<=>)
            # Lower distance = more similar
            # We calculate similarity as 1 - distance for easier interpretation
            search_sql = f"""
                SELECT 
                    id,
                    document_id,
                    project_id,
                    chunk_index,
                    content,
                    metadata,
                    1 - (embedding <=> $1::vector) AS similarity
                FROM {self.config.VECTOR_TABLE_NAME}
                WHERE project_id = $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3;
            """

            pool = await self.db_manager._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(search_sql, query_emb, project_id, k)

            # Format results as LangChain Documents
            results = []
            for row in rows:
                # Parse metadata JSON
                meta = row['metadata']
                if isinstance(meta, str):
                    meta = json.loads(meta)
                elif meta is None:
                    meta = {}
                
                # Create Document with enriched metadata
                doc = Document(
                    page_content=row['content'],
                    metadata={
                        **meta,
                        'id': str(row['id']),
                        'document_id': str(row['document_id']),
                        'project_id': str(row['project_id']),
                        'chunk_index': int(row['chunk_index']),
                        'similarity': float(row['similarity']),
                    }
                )
                results.append(doc)

            logger.info(f"✅ Found {len(results)} similar chunks (top result: {results[0].metadata['similarity']:.3f})" if results else "✅ No results found")
            return results

        except Exception as e:
            logger.error(f"❌ Search error: {e}", exc_info=True)
            raise

    async def search_with_filters(
        self,
        query: str,
        project_id: str,
        k: int = 5,
        document_ids: Optional[List[str]] = None,
        min_similarity: float = 0.0
    ) -> List[Document]:
        """
        Advanced search with additional filters.
        
        Args:
            query: Search query text
            project_id: Project UUID
            k: Number of results
            document_ids: Filter by specific document IDs
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
        """
        try:
            logger.info(f"🔍 Advanced search in project {project_id}")

            # Compute query embedding
            query_emb = await self.embeddings.aembed_query(query)
            
            # Build dynamic SQL with filters
            where_clauses = ["project_id = $2"]
            params = [query_emb, project_id]
            param_count = 2
            
            if document_ids:
                param_count += 1
                where_clauses.append(f"document_id = ANY(${param_count})")
                params.append(document_ids)
            
            if min_similarity > 0.0:
                param_count += 1
                where_clauses.append(f"(1 - (embedding <=> $1::vector)) >= ${param_count}")
                params.append(min_similarity)
            
            where_clause = " AND ".join(where_clauses)
            
            search_sql = f"""
                SELECT 
                    id, document_id, project_id, chunk_index,
                    content, metadata,
                    1 - (embedding <=> $1::vector) AS similarity
                FROM {self.config.VECTOR_TABLE_NAME}
                WHERE {where_clause}
                ORDER BY embedding <=> $1::vector
                LIMIT {k};
            """

            pool = await self.db_manager._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(search_sql, *params)

            # Format results
            results = []
            for row in rows:
                meta = row['metadata']
                if isinstance(meta, str):
                    meta = json.loads(meta)
                elif meta is None:
                    meta = {}
                
                doc = Document(
                    page_content=row['content'],
                    metadata={
                        **meta,
                        'id': str(row['id']),
                        'document_id': str(row['document_id']),
                        'project_id': str(row['project_id']),
                        'chunk_index': int(row['chunk_index']),
                        'similarity': float(row['similarity']),
                    }
                )
                results.append(doc)

            logger.info(f"✅ Advanced search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"❌ Advanced search error: {e}", exc_info=True)
            raise

    async def get_document_chunks(
        self,
        document_id: str,
        project_id: str
    ) -> List[Document]:
        """Get all chunks for a specific document"""
        try:
            query = f"""
                SELECT id, chunk_index, content, metadata
                FROM {self.config.VECTOR_TABLE_NAME}
                WHERE document_id = $1 AND project_id = $2
                ORDER BY chunk_index;
            """
            
            rows = await self.db_manager.fetch_all(query, (document_id, project_id))
            
            results = []
            for row in rows:
                meta = row['metadata'] if isinstance(row['metadata'], dict) else json.loads(row['metadata'] or '{}')
                doc = Document(
                    page_content=row['content'],
                    metadata={
                        **meta,
                        'id': str(row['id']),
                        'chunk_index': int(row['chunk_index'])
                    }
                )
                results.append(doc)
            
            logger.info(f"✅ Retrieved {len(results)} chunks for document {document_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error getting document chunks: {e}", exc_info=True)
            raise

    async def delete_document_vectors(self, document_id: str, project_id: str):
        """Delete all vectors for a document"""
        try:
            logger.info(f"🗑️ Deleting vectors for document {document_id} in project {project_id}")

            # Delete from vector table
            delete_vectors_query = f"""
                DELETE FROM {self.config.VECTOR_TABLE_NAME} 
                WHERE document_id = $1 AND project_id = $2;
            """
            await self.db_manager.execute_query(delete_vectors_query, (document_id, project_id))

            # Delete from chunks metadata table
            delete_chunks_query = """
                DELETE FROM document_chunks 
                WHERE document_id = $1 AND project_id = $2;
            """
            await self.db_manager.execute_query(delete_chunks_query, (document_id, project_id))

            logger.info(f"✅ Deleted vectors for document {document_id} in project {project_id}")
            
        except Exception as e:
            logger.error(f"❌ Error deleting document vectors: {e}", exc_info=True)
            raise

    async def get_project_stats(self, project_id: str) -> Dict:
        """Get statistics about vectors in a project"""
        try:
            query = f"""
                SELECT 
                    COUNT(*) as total_chunks,
                    COUNT(DISTINCT document_id) as total_documents,
                    AVG(LENGTH(content)) as avg_chunk_length,
                    SUM(LENGTH(content)) as total_content_length
                FROM {self.config.VECTOR_TABLE_NAME}
                WHERE project_id = $1;
            """
            
            result = await self.db_manager.fetch_one(query, (project_id,))
            
            stats = {
                'total_chunks': result['total_chunks'],
                'total_documents': result['total_documents'],
                'avg_chunk_length': float(result['avg_chunk_length']) if result['avg_chunk_length'] else 0,
                'total_content_length': result['total_content_length'] or 0,
            }
            
            logger.info(f"📊 Project {project_id} stats: {stats['total_chunks']} chunks across {stats['total_documents']} documents")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting project stats: {e}", exc_info=True)
            raise

    async def bulk_delete_by_project(self, project_id: str):
        """Delete all vectors for a project (use with caution!)"""
        try:
            logger.warning(f"⚠️ BULK DELETE: Removing all vectors for project {project_id}")

            # Delete from vector table
            delete_vectors = f"""
                DELETE FROM {self.config.VECTOR_TABLE_NAME} 
                WHERE project_id = $1;
            """
            await self.db_manager.execute_query(delete_vectors, (project_id,))

            # Delete from chunks table
            delete_chunks = """
                DELETE FROM document_chunks 
                WHERE project_id = $1;
            """
            await self.db_manager.execute_query(delete_chunks, (project_id,))

            logger.info(f"✅ Bulk deleted all vectors for project {project_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in bulk delete: {e}", exc_info=True)
            raise