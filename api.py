from typing import Dict, Any, List
import logging
 
logger = logging.getLogger(__name__)
 
async def search_documents(
    query: str,
    project_id: str,
    user_id: str,
    k: int = 5,
    filters: Dict = None
) -> Dict[str, Any]:
    """
    Search API with project isolation
    Usage: Call this from your application backend
    """
    from pipeline_processor import PipelineProcessor
   
    processor = PipelineProcessor()
    await processor.initialize()
   
    # Search
    results = await processor.vector_manager.search_similar(
        query=query,
        project_id=project_id,
        k=k,
        filter_dict=filters
    )
   
    # Format results
    formatted_results = []
    for doc in results:
        formatted_results.append({
            'content': doc.page_content,
            'metadata': doc.metadata,
            'document_id': doc.metadata.get('document_id'),
            'filename': doc.metadata.get('filename'),
            'chunk_index': doc.metadata.get('chunk_index'),
        })
   
    return {
        'query': query,
        'results': formatted_results,
        'count': len(formatted_results)
    }
 
async def get_document_status(
    document_id: str,
    project_id: str,
    user_id: str
) -> Dict[str, Any]:
    """Get document processing status"""
    from pipeline_processor import PipelineProcessor
   
    processor = PipelineProcessor()
    await processor.initialize()
   
    # Get document info
    query = """
        SELECT d.id, d.filename, d.status, d.processing_method, d.page_count,
               d.file_size, d.uploaded_by, d.created_at, d.processed_at,
               d.error_message, d.metadata,
               COUNT(dc.id) as chunk_count
        FROM documents d
        LEFT JOIN document_chunks dc ON d.id = dc.document_id
        WHERE d.id = $1 AND d.project_id = $2 AND d.deleted_at IS NULL
        GROUP BY d.id
    """
   
    row = await processor.db_manager.fetch_one(query, (document_id, project_id))
   
    if not row:
        raise ValueError("Document not found")
   
    # Get processing logs
    logs_query = """
        SELECT stage, status, duration_ms, created_at, metadata
        FROM processing_logs
        WHERE document_id = $1
        ORDER BY created_at DESC
        LIMIT 20
    """
   
    logs = await processor.db_manager.fetch_all(logs_query, (document_id,))
   
    return {
        'document_id': str(row[0]),
        'filename': row[1],
        'status': row[2],
        'processing_method': row[3],
        'page_count': row[4],
        'file_size': row[5],
        'uploaded_by': row[6],
        'created_at': row[7].isoformat() if row[7] else None,
        'processed_at': row[8].isoformat() if row[8] else None,
        'error_message': row[9],
        'metadata': row[10],
        'chunk_count': row[11],
        'processing_logs': [
            {
                'stage': log[0],
                'status': log[1],
                'duration_ms': log[2],
                'timestamp': log[3].isoformat(),
                'metadata': log[4]
            }
            for log in logs
        ]
    }