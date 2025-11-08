

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import uuid
import logging
import os
from google.cloud import storage
from database_manager import DatabaseManager
from vector_store_manager import VectorStoreManager
from config import Config
from fastapi.responses import JSONResponse
from langchain_core.documents import Document
from typing import Optional
import uuid
# Add these imports at the top
from datetime import timedelta
from collections import defaultdict
# Add these imports at the top
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json
# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import warnings
warnings.filterwarnings('ignore', message='.*deprecated as of June 24, 2025.*')

# ============================================================================
# GOOGLE CLOUD CREDENTIALS
# ============================================================================

# dir_path = os.path.dirname(os.path.abspath(__file__))
# credentials_path = os.path.join(dir_path, 'secrets', 'credentials.json')
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

db_manager = DatabaseManager()
vector_manager = VectorStoreManager(db_manager)
storage_client = None

# ============================================================================
# LIFESPAN MANAGER
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global db_manager, vector_manager, storage_client

    # === STARTUP ===
    try:
        logger.info("🚀 Starting DocuMind AI API...")
        await db_manager._get_pool()
        storage_client = storage.Client(project=Config.PROJECT_ID)
        await vector_manager.initialize()
        logger.info("✅ API startup complete - Ready to serve requests")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise

    yield

    # === SHUTDOWN ===
    try:
        logger.info("🔄 Shutting down DocuMind AI API...")
        if db_manager:
            await db_manager.close()
        logger.info("✅ API shutdown complete")
    except Exception as e:
        logger.error(f"⚠️ Shutdown error: {e}")


# Add WebSocket connection manager class (add after imports, before app initialization)
class ConnectionManager:
    def __init__(self):
        # Map of project_id to set of websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = set()
        self.active_connections[project_id].add(websocket)
        logger.info(f"WebSocket connected for project {project_id}")
    
    def disconnect(self, websocket: WebSocket, project_id: str):
        if project_id in self.active_connections:
            self.active_connections[project_id].discard(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
        logger.info(f"WebSocket disconnected for project {project_id}")
    
    async def broadcast_to_project(self, project_id: str, message: dict):
        """Broadcast message to all connections for a specific project"""
        if project_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to websocket: {e}")
                    disconnected.add(connection)
            
            # Remove disconnected websockets
            for connection in disconnected:
                self.active_connections[project_id].discard(connection)

# Initialize connection manager
manager = ConnectionManager()

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="DocuMind AI API",
    description="Backend API for Document Processing Pipeline with Vector Search",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    # Add common local dev ports (frontend may run on 5174)
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://rag-pipeline-ui-141241159430.europe-west1.run.app",
]

if frontend_url := os.getenv("FRONTEND_URL"):
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # Also allow localhost on any port via regex (useful during local development)
    allow_origin_regex=r"^http://localhost(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    user_id: str
    user_email: EmailStr

class MemberInvite(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(owner|admin|member)$")
    user_id: str

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    project_id: str
    user_id: str
    k: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None

class SignedUrlRequest(BaseModel):
    filename: str
    project_id: str
    user_id: str
    content_type: str


# Add this Pydantic model with your other models
class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    project_id: str
    user_id: str
    conversation_id: Optional[str] = None
    k: int = Field(default=5, ge=1, le=20)  # Number of chunks to retrieve
    temperature: float = Field(default=0.7, ge=0, le=1)

class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    timestamp: str

class DocumentFilter(BaseModel):
    status: Optional[List[str]] = None
    processing_method: Optional[List[str]] = None
    file_type: Optional[List[str]] = None
    uploaded_by: Optional[List[str]] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    min_size_mb: Optional[float] = None
    max_size_mb: Optional[float] = None
    min_pages: Optional[int] = None
    max_pages: Optional[int] = None
    search_text: Optional[str] = None

class BatchOperation(BaseModel):
    operation: str  # 'delete', 'reprocess', 'tag', 'export'
    document_ids: List[str]
    user_id: str
    params: Optional[Dict[str, Any]] = None

class DocumentTag(BaseModel):
    tag: str
    color: Optional[str] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def verify_project_access(project_id: str, user_id: str) -> bool:
    """Verify user has access to project"""
    query = """
        SELECT 1 FROM members 
        WHERE project_id = $1 AND user_id = $2
    """
    result = await db_manager.fetch_one(query, (project_id, user_id))
    return result is not None

async def get_project_or_404(project_id: str, user_id: str):
    """Get project and verify access"""
    has_access = await verify_project_access(project_id, user_id)
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied to this project")

    query = """
        SELECT id, name, description, storage_path, settings, created_at
        FROM projects
        WHERE id = $1 AND deleted_at IS NULL
    """
    project = await db_manager.fetch_one(query, (project_id,))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project

# ============================================================================
# ROOT & HEALTH ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "DocuMind AI API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        await db_manager.fetch_one("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "documind-api",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "vector_store": "healthy" if vector_manager else "not initialized"
    }

@app.middleware("http")
async def _log_options_requests(request: Request, call_next):
    """Log incoming OPTIONS preflight requests for debugging and let CORSMiddleware handle them."""
    if request.method == "OPTIONS":
        origin = request.headers.get("origin")
        acr_method = request.headers.get("access-control-request-method")
        acr_headers = request.headers.get("access-control-request-headers")
        logger.info(f"OPTIONS preflight: path={request.url.path} origin={origin} acr_method={acr_method} acr_headers={acr_headers}")
    return await call_next(request)

# ============================================================================
# PROJECT ENDPOINTS
# ============================================================================

@app.get("/api/projects")
async def list_projects(user_id: str = Query(...)):
    """List all projects for a user"""
    try:
        # Fixed query: removed m.deleted_at check since members table doesn't have it yet
        query = """
            SELECT 
                p.id, p.name, p.description, p.storage_path, 
                p.settings, p.created_at, p.updated_at,
                COUNT(DISTINCT d.id) as doc_count,
                COALESCE(SUM(d.file_size), 0) as storage_bytes,
                COUNT(DISTINCT m.user_id) as members_count
            FROM projects p
            INNER JOIN members m ON p.id = m.project_id
            LEFT JOIN documents d ON p.id = d.project_id AND d.deleted_at IS NULL
            WHERE m.user_id = $1 AND p.deleted_at IS NULL
            GROUP BY p.id
            ORDER BY p.created_at DESC
        """

        rows = await db_manager.fetch_all(query, (user_id,))

        projects = [
            {
                'id': str(row[0]),
                'name': row[1],
                'description': row[2],
                'storage_path': row[3],
                'settings': row[4] or {},
                'created_at': row[5].isoformat() if row[5] else None,
                'updated_at': row[6].isoformat() if row[6] else None,
                'doc_count': row[7],
                'storage_used': round(row[8] / (1024**3), 2),
                'members_count': row[9]
            }
            for row in rows
        ]

        logger.info(f"Listed {len(projects)} projects for user {user_id}")
        return {'projects': projects, 'count': len(projects)}

    except Exception as e:
        logger.error(f"List projects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    try:
        project_id = str(uuid.uuid4())
        storage_path = f"documents/{project_id}"

        query = """
            INSERT INTO projects (id, name, description, storage_path)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, description, storage_path, created_at
        """
        await db_manager.execute_query(
            query,
            (project_id, project.name, project.description, storage_path)
        )

        member_query = """
            INSERT INTO members (project_id, user_id, email, role)
            VALUES ($1, $2, $3, $4)
        """
        await db_manager.execute_query(
            member_query,
            (project_id, project.user_id, project.user_email, 'owner')
        )

        bucket = storage_client.bucket(Config.BUCKET_NAME)
        blob = bucket.blob(f"{storage_path}/.placeholder")
        blob.upload_from_string("")

        logger.info(f"✅ Project created: {project_id}")

        return {
            'id': project_id,
            'name': project.name,
            'description': project.description,
            'storage_path': storage_path,
            'created_at': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Create project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, user_id: str = Query(...)):
    """Soft delete a project (owner only)"""
    try:
        query = """
            SELECT role FROM members 
            WHERE project_id = $1 AND user_id = $2
        """
        result = await db_manager.fetch_one(query, (project_id, user_id))

        if not result or result[0] != 'owner':
            raise HTTPException(status_code=403, detail="Only project owner can delete")

        delete_query = """
            UPDATE projects 
            SET deleted_at = CURRENT_TIMESTAMP 
            WHERE id = $1
        """
        await db_manager.execute_query(delete_query, (project_id,))

        logger.info(f"✅ Project deleted: {project_id}")
        return {'status': 'success', 'message': 'Project deleted'}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# DOCUMENT ENDPOINTS
# ============================================================================

@app.get("/api/documents")
async def list_documents(
    project_id: str = Query(...),
    user_id: str = Query(...)
):
    """List all documents in a project"""
    try:
        await get_project_or_404(project_id, user_id)

        # Using actual column names from your schema
        query = """
            SELECT 
                id, filename, file_size, file_type, page_count,
                processing_method, status, error_message,
                uploaded_by, created_at, processed_at, retry_count,
                gcs_uri, metadata
            FROM documents
            WHERE project_id = $1 AND deleted_at IS NULL
            ORDER BY created_at DESC
        """
        
        rows = await db_manager.fetch_all(query, (project_id,))

        documents = []
        for row in rows:
            # Get chunk count from document_chunks table
            chunk_query = """
                SELECT COUNT(*) FROM document_chunks 
                WHERE document_id = $1
            """
            chunk_result = await db_manager.fetch_one(chunk_query, (str(row[0]),))
            chunk_count = chunk_result[0] if chunk_result else 0
            
            # Get processing logs
            logs_query = """
                SELECT stage, status, duration_ms, error_details, created_at
                FROM processing_logs 
                WHERE document_id = $1
                ORDER BY created_at ASC
            """
            logs_rows = await db_manager.fetch_all(logs_query, (str(row[0]),))
            processing_logs = [
                {
                    'stage': log[0],
                    'status': log[1],
                    'duration_ms': log[2],
                    'error_details': log[3],
                    'timestamp': log[4].isoformat() if log[4] else None
                }
                for log in logs_rows
            ]
            
            # Calculate processing time from logs
            processing_time_ms = sum(log[2] for log in logs_rows if log[2]) if logs_rows else None

            doc = {
                'id': str(row[0]),
                'filename': row[1],
                'file_size': row[2],
                'mime_type': row[3],  # file_type from DB
                'page_count': row[4],
                'processing_method': row[5] or 'standard',
                'status': row[6] or 'pending',
                'error_message': row[7],
                'uploaded_by': row[8],
                'created_at': row[9].isoformat() if row[9] else None,
                'updated_at': row[10].isoformat() if row[10] else None,  # processed_at
                'processing_time_ms': processing_time_ms,
                'chunk_count': chunk_count,
                'gcs_uri': row[12],
                'metadata': row[13] or {},
                'processing_logs': processing_logs
            }
            documents.append(doc)

        logger.info(f"Listed {len(documents)} documents for project {project_id}")
        return {'documents': documents, 'count': len(documents)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/{document_id}")
async def get_document_details(
    document_id: str,
    project_id: str = Query(...),
    user_id: str = Query(...)
):
    """Get detailed information about a document"""
    try:
        await get_project_or_404(project_id, user_id)

        query = """
            SELECT 
                id, filename, file_size, file_type, page_count,
                processing_method, status, error_message,
                uploaded_by, created_at, processed_at,
                gcs_uri, metadata
            FROM documents
            WHERE id = $1 AND project_id = $2 AND deleted_at IS NULL
        """
        
        row = await db_manager.fetch_one(query, (document_id, project_id))

        if not row:
            raise HTTPException(status_code=404, detail="Document not found")

        # Get chunk count
        chunk_query = """
            SELECT COUNT(*) FROM document_chunks 
            WHERE document_id = $1
        """
        chunk_result = await db_manager.fetch_one(chunk_query, (document_id,))
        chunk_count = chunk_result[0] if chunk_result else 0
        
        # Get processing logs
        logs_query = """
            SELECT stage, status, duration_ms, error_details, created_at
            FROM processing_logs 
            WHERE document_id = $1
            ORDER BY created_at ASC
        """
        logs_rows = await db_manager.fetch_all(logs_query, (document_id,))
        processing_logs = [
            {
                'stage': log[0],
                'status': log[1],
                'duration_ms': log[2],
                'error_details': log[3],
                'timestamp': log[4].isoformat() if log[4] else None
            }
            for log in logs_rows
        ]
        
        processing_time_ms = sum(log[2] for log in logs_rows if log[2]) if logs_rows else None

        document = {
            'id': str(row[0]),
            'filename': row[1],
            'file_size': row[2],
            'mime_type': row[3],
            'page_count': row[4],
            'processing_method': row[5] or 'standard',
            'status': row[6] or 'pending',
            'error_message': row[7],
            'uploaded_by': row[8],
            'created_at': row[9].isoformat() if row[9] else None,
            'updated_at': row[10].isoformat() if row[10] else None,
            'processing_time_ms': processing_time_ms,
            'chunk_count': chunk_count,
            'gcs_uri': row[11],
            'metadata': row[12] or {},
            'processing_logs': processing_logs
        }

        logger.info(f"Retrieved document details: {document_id}")
        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get document details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    project_id: str = Query(...),
    user_id: str = Query(...)
):
    """Delete a document and its vectors"""
    try:
        await get_project_or_404(project_id, user_id)

        # Soft delete document
        query = """
            UPDATE documents 
            SET deleted_at = CURRENT_TIMESTAMP 
            WHERE id = $1 AND project_id = $2
        """
        await db_manager.execute_query(query, (document_id, project_id))

        # Delete vectors
        await vector_manager.delete_document_vectors(document_id, project_id)

        logger.info(f"✅ Document deleted: {document_id}")
        return {'status': 'success', 'message': 'Document deleted'}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Advanced document filtering endpoint
@app.post("/api/documents/filter")
async def filter_documents(
    project_id: str = Query(...),
    user_id: str = Query(...),
    filter_params: DocumentFilter = None
):
    """
    Advanced document filtering with multiple criteria
    """
    try:
        await get_project_or_404(project_id, user_id)
        
        # Build dynamic query
        where_clauses = ["project_id = $1", "deleted_at IS NULL"]
        params = [project_id]
        param_count = 1
        
        if filter_params:
            # Status filter
            if filter_params.status:
                param_count += 1
                where_clauses.append(f"status = ANY(${param_count})")
                params.append(filter_params.status)
            
            # Processing method filter
            if filter_params.processing_method:
                param_count += 1
                where_clauses.append(f"processing_method = ANY(${param_count})")
                params.append(filter_params.processing_method)
            
            # File type filter
            if filter_params.file_type:
                param_count += 1
                where_clauses.append(f"file_type = ANY(${param_count})")
                params.append(filter_params.file_type)
            
            # Uploaded by filter
            if filter_params.uploaded_by:
                param_count += 1
                where_clauses.append(f"uploaded_by = ANY(${param_count})")
                params.append(filter_params.uploaded_by)
            
            # Date range filter
            if filter_params.from_date:
                param_count += 1
                where_clauses.append(f"created_at >= ${param_count}")
                params.append(filter_params.from_date)
            
            if filter_params.to_date:
                param_count += 1
                where_clauses.append(f"created_at <= ${param_count}")
                params.append(filter_params.to_date)
            
            # Size filter
            if filter_params.min_size_mb:
                param_count += 1
                where_clauses.append(f"file_size >= ${param_count}")
                params.append(int(filter_params.min_size_mb * 1024 * 1024))
            
            if filter_params.max_size_mb:
                param_count += 1
                where_clauses.append(f"file_size <= ${param_count}")
                params.append(int(filter_params.max_size_mb * 1024 * 1024))
            
            # Page count filter
            if filter_params.min_pages:
                param_count += 1
                where_clauses.append(f"page_count >= ${param_count}")
                params.append(filter_params.min_pages)
            
            if filter_params.max_pages:
                param_count += 1
                where_clauses.append(f"page_count <= ${param_count}")
                params.append(filter_params.max_pages)
            
            # Full-text search
            if filter_params.search_text:
                param_count += 1
                where_clauses.append(f"(filename ILIKE ${param_count} OR error_message ILIKE ${param_count})")
                params.append(f"%{filter_params.search_text}%")
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
            SELECT 
                id, filename, file_size, file_type, page_count,
                processing_method, status, error_message,
                uploaded_by, created_at, processed_at,
                gcs_uri, metadata
            FROM documents
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT 100
        """
        
        rows = await db_manager.fetch_all(query, tuple(params))
        
        documents = []
        for row in rows:
            # Get chunk count
            chunk_query = "SELECT COUNT(*) FROM document_chunks WHERE document_id = $1"
            chunk_result = await db_manager.fetch_one(chunk_query, (str(row[0]),))
            chunk_count = chunk_result[0] if chunk_result else 0
            
            doc = {
                'id': str(row[0]),
                'filename': row[1],
                'file_size': row[2],
                'mime_type': row[3],
                'page_count': row[4],
                'processing_method': row[5] or 'standard',
                'status': row[6] or 'pending',
                'error_message': row[7],
                'uploaded_by': row[8],
                'created_at': row[9].isoformat() if row[9] else None,
                'updated_at': row[10].isoformat() if row[10] else None,
                'chunk_count': chunk_count,
                'gcs_uri': row[11],
                'metadata': row[12] or {}
            }
            documents.append(doc)
        
        logger.info(f"Filtered {len(documents)} documents for project {project_id}")
        return {'documents': documents, 'count': len(documents)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Filter documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Batch operations endpoint
@app.post("/api/documents/batch")
async def batch_operation(
    project_id: str = Query(...),
    operation: BatchOperation = None
):
    """
    Perform batch operations on multiple documents
    """
    try:
        await get_project_or_404(project_id, operation.user_id)
        
        if not operation.document_ids:
            raise HTTPException(status_code=400, detail="No documents specified")
        
        results = {
            'operation': operation.operation,
            'total': len(operation.document_ids),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        if operation.operation == 'delete':
            # Batch delete
            for doc_id in operation.document_ids:
                try:
                    # Soft delete document
                    query = """
                        UPDATE documents 
                        SET deleted_at = CURRENT_TIMESTAMP 
                        WHERE id = $1 AND project_id = $2
                    """
                    await db_manager.execute_query(query, (doc_id, project_id))
                    
                    # Delete vectors
                    await vector_manager.delete_document_vectors(doc_id, project_id)
                    
                    results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({'document_id': doc_id, 'error': str(e)})
        
        elif operation.operation == 'tag':
            # Batch tagging
            tag = operation.params.get('tag') if operation.params else None
            if not tag:
                raise HTTPException(status_code=400, detail="Tag parameter required")
            
            for doc_id in operation.document_ids:
                try:
                    query = """
                        UPDATE documents 
                        SET metadata = COALESCE(metadata, '{}'::jsonb) || 
                                     jsonb_build_object('tags', 
                                         COALESCE(metadata->'tags', '[]'::jsonb) || $1::jsonb)
                        WHERE id = $2 AND project_id = $3
                    """
                    await db_manager.execute_query(
                        query, 
                        (json.dumps([tag]), doc_id, project_id)
                    )
                    results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({'document_id': doc_id, 'error': str(e)})
        
        elif operation.operation == 'export':
            # Batch export metadata
            export_data = []
            for doc_id in operation.document_ids:
                try:
                    query = """
                        SELECT filename, file_type, file_size, page_count,
                               status, processing_method, created_at, uploaded_by
                        FROM documents
                        WHERE id = $1 AND project_id = $2
                    """
                    row = await db_manager.fetch_one(query, (doc_id, project_id))
                    if row:
                        export_data.append({
                            'filename': row[0],
                            'file_type': row[1],
                            'file_size': row[2],
                            'page_count': row[3],
                            'status': row[4],
                            'processing_method': row[5],
                            'created_at': row[6].isoformat() if row[6] else None,
                            'uploaded_by': row[7]
                        })
                        results['success'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({'document_id': doc_id, 'error': str(e)})
            
            results['export_data'] = export_data
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {operation.operation}")
        
        logger.info(f"Batch {operation.operation}: {results['success']}/{results['total']} successful")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch operation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))




# Get filter options (for UI dropdowns)
@app.get("/api/documents/filter-options")
async def get_filter_options(
    project_id: str = Query(...),
    user_id: str = Query(...)
):
    """
    Get available filter options for the UI
    """
    try:
        await get_project_or_404(project_id, user_id)
        
        # Get unique statuses
        status_query = """
            SELECT DISTINCT status FROM documents 
            WHERE project_id = $1 AND deleted_at IS NULL AND status IS NOT NULL
        """
        statuses = await db_manager.fetch_all(status_query, (project_id,))
        
        # Get unique processing methods
        method_query = """
            SELECT DISTINCT processing_method FROM documents 
            WHERE project_id = $1 AND deleted_at IS NULL AND processing_method IS NOT NULL
        """
        methods = await db_manager.fetch_all(method_query, (project_id,))
        
        # Get unique file types
        type_query = """
            SELECT DISTINCT file_type FROM documents 
            WHERE project_id = $1 AND deleted_at IS NULL AND file_type IS NOT NULL
        """
        types = await db_manager.fetch_all(type_query, (project_id,))
        
        # Get unique uploaders
        uploader_query = """
            SELECT DISTINCT uploaded_by FROM documents 
            WHERE project_id = $1 AND deleted_at IS NULL AND uploaded_by IS NOT NULL
        """
        uploaders = await db_manager.fetch_all(uploader_query, (project_id,))
        
        return {
            'statuses': [row[0] for row in statuses],
            'processing_methods': [row[0] for row in methods],
            'file_types': [row[0] for row in types],
            'uploaders': [row[0] for row in uploaders]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get filter options error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Document comparison endpoint
@app.post("/api/documents/compare")
async def compare_documents(
    project_id: str = Query(...),
    user_id: str = Query(...),
    document_ids: List[str] = Query(...)
):
    """
    Compare multiple documents side by side
    """
    try:
        await get_project_or_404(project_id, user_id)
        
        if len(document_ids) < 2 or len(document_ids) > 4:
            raise HTTPException(status_code=400, detail="Compare 2-4 documents")
        
        comparison_data = []
        
        for doc_id in document_ids:
            # Get document details
            doc_query = """
                SELECT id, filename, file_size, file_type, page_count,
                       processing_method, status, created_at, uploaded_by
                FROM documents
                WHERE id = $1 AND project_id = $2 AND deleted_at IS NULL
            """
            doc = await db_manager.fetch_one(doc_query, (doc_id, project_id))
            
            if not doc:
                continue
            
            # Get chunk count
            chunk_query = "SELECT COUNT(*) FROM document_chunks WHERE document_id = $1"
            chunk_result = await db_manager.fetch_one(chunk_query, (doc_id,))
            
            # Get processing stats
            stats_query = """
                SELECT 
                    SUM(duration_ms) as total_duration,
                    COUNT(*) as stage_count
                FROM processing_logs
                WHERE document_id = $1 AND status = 'completed'
            """
            stats = await db_manager.fetch_one(stats_query, (doc_id,))
            
            comparison_data.append({
                'id': str(doc[0]),
                'filename': doc[1],
                'file_size': doc[2],
                'file_type': doc[3],
                'page_count': doc[4],
                'processing_method': doc[5],
                'status': doc[6],
                'created_at': doc[7].isoformat() if doc[7] else None,
                'uploaded_by': doc[8],
                'chunk_count': chunk_result[0] if chunk_result else 0,
                'total_processing_time_ms': stats[0] if stats and stats[0] else 0,
                'processing_stages': stats[1] if stats and stats[1] else 0
            })
        
        return {
            'documents': comparison_data,
            'count': len(comparison_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compare documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# UPLOAD ENDPOINT
# ============================================================================

@app.post("/api/upload/signed-url")
async def get_signed_upload_url(request: SignedUrlRequest):
    """Generate a signed URL for direct GCS upload"""
    try:
        await get_project_or_404(request.project_id, request.user_id)

        if not request.filename or len(request.filename) > 255:
            raise HTTPException(status_code=400, detail="Invalid filename")

        storage_path = f"documents/{request.project_id}/{request.filename}"
        
        bucket = storage_client.bucket(Config.BUCKET_NAME)
        blob = bucket.blob(storage_path)

        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="PUT",
            content_type=request.content_type
        )

        gcs_uri = f"gs://{Config.BUCKET_NAME}/{storage_path}"

        logger.info(f"Generated signed URL for {request.filename}")
        
        return {
            'signed_url': signed_url,
            'gcs_uri': gcs_uri,
            'filename': request.filename
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signed URL generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# MEMBER MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/projects/{project_id}/members")
async def get_project_members(
    project_id: str,
    user_id: str = Query(...)
):
    """Get all members of a project"""
    try:
        await get_project_or_404(project_id, user_id)

        query = """
            SELECT user_id, email, role, created_at
            FROM members
            WHERE project_id = $1
            ORDER BY created_at ASC
        """
        
        rows = await db_manager.fetch_all(query, (project_id,))

        members = [
            {
                'user_id': row[0],
                'email': row[1],
                'role': row[2],
                'created_at': row[3].isoformat() if row[3] else None
            }
            for row in rows
        ]

        logger.info(f"Listed {len(members)} members for project {project_id}")
        return {'members': members, 'count': len(members)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get members error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/{project_id}/members")
async def invite_member(
    project_id: str,
    invite: MemberInvite
):
    """Invite a member to a project"""
    try:
        await get_project_or_404(project_id, invite.user_id)

        # Check if member already exists
        check_query = """
            SELECT 1 FROM members 
            WHERE project_id = $1 AND email = $2
        """
        existing = await db_manager.fetch_one(check_query, (project_id, invite.email))
        
        if existing:
            raise HTTPException(status_code=400, detail="Member already exists")

        # Add member
        query = """
            INSERT INTO members (project_id, user_id, email, role)
            VALUES ($1, $2, $3, $4)
            RETURNING user_id, email, role, created_at
        """
        
        new_user_id = str(uuid.uuid4())
        
        row = await db_manager.fetch_one(
            query,
            (project_id, new_user_id, invite.email, invite.role)
        )

        logger.info(f"✅ Member invited: {invite.email} to project {project_id}")
        
        return {
            'user_id': row[0],
            'email': row[1],
            'role': row[2],
            'created_at': row[3].isoformat() if row[3] else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invite member error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}/members/{member_user_id}")
async def remove_member(
    project_id: str,
    member_user_id: str,
    user_id: str = Query(...)
):
    """Remove a member from a project"""
    try:
        await get_project_or_404(project_id, user_id)

        # Check if requester is owner/admin
        check_query = """
            SELECT role FROM members 
            WHERE project_id = $1 AND user_id = $2
        """
        result = await db_manager.fetch_one(check_query, (project_id, user_id))
        
        if not result or result[0] not in ['owner', 'admin']:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # Hard delete member (no deleted_at column in members yet)
        query = """
            DELETE FROM members 
            WHERE project_id = $1 AND user_id = $2
        """
        await db_manager.execute_query(query, (project_id, member_user_id))

        logger.info(f"✅ Member removed: {member_user_id} from project {project_id}")
        return {'status': 'success', 'message': 'Member removed'}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remove member error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ANALYTICS ENDPOINT
# ============================================================================

@app.get("/api/projects/{project_id}/analytics")
async def get_project_analytics(
    project_id: str,
    user_id: str = Query(...)
):
    """Get analytics for a project"""
    try:
        await get_project_or_404(project_id, user_id)

        query = """
            SELECT 
                COUNT(*) as total_documents,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_documents,
                COUNT(*) FILTER (WHERE status = 'processing') as processing_documents,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_documents,
                COALESCE(SUM(file_size), 0) as total_storage_bytes
            FROM documents
            WHERE project_id = $1 AND deleted_at IS NULL
        """
        
        row = await db_manager.fetch_one(query, (project_id,))
        
        # Get total chunks from document_chunks table
        chunks_query = """
            SELECT COUNT(*) FROM document_chunks 
            WHERE project_id = $1
        """
        chunks_result = await db_manager.fetch_one(chunks_query, (project_id,))
        total_chunks = chunks_result[0] if chunks_result else 0
        
        # Get average processing time from processing_logs
        avg_time_query = """
            SELECT AVG(duration_ms) 
            FROM processing_logs 
            WHERE project_id = $1 AND duration_ms IS NOT NULL
        """
        avg_time_result = await db_manager.fetch_one(avg_time_query, (project_id,))
        avg_processing_time = avg_time_result[0] if avg_time_result and avg_time_result[0] else 0

        analytics = {
            'total_documents': row[0],
            'completed_documents': row[1],
            'processing_documents': row[2],
            'failed_documents': row[3],
            'total_storage_bytes': row[4],
            'total_storage_gb': round(row[4] / (1024**3), 2),
            'avg_processing_time_ms': round(avg_processing_time, 2),
            'total_chunks': total_chunks
        }

        logger.info(f"Retrieved analytics for project {project_id}")
        return analytics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Add after your existing analytics endpoint
@app.get("/api/projects/{project_id}/analytics/detailed")
async def get_detailed_analytics(
    project_id: str,
    user_id: str = Query(...),
    days: int = Query(default=30, ge=1, le=365)
):
    """
    Get detailed analytics with time-series data and trends
    """
    try:
        await get_project_or_404(project_id, user_id)
        
        start_date = datetime.now() - timedelta(days=days)
        
        # 1. Document Statistics
        doc_stats_query = """
            SELECT 
                COUNT(*) as total_documents,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'processing') as processing,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'archived') as archived,
                COALESCE(SUM(file_size), 0) as total_storage_bytes,
                COALESCE(AVG(CASE WHEN status = 'completed' THEN file_size END), 0) as avg_file_size,
                COUNT(DISTINCT uploaded_by) as unique_uploaders
            FROM documents
            WHERE project_id = $1 AND deleted_at IS NULL
        """
        doc_stats = await db_manager.fetch_one(doc_stats_query, (project_id,))
        
        # 2. Processing Method Distribution
        method_dist_query = """
            SELECT 
                processing_method,
                COUNT(*) as count,
                AVG(page_count) as avg_pages
            FROM documents
            WHERE project_id = $1 AND status = 'completed' AND deleted_at IS NULL
            GROUP BY processing_method
        """
        method_dist = await db_manager.fetch_all(method_dist_query, (project_id,))
        
        # 3. File Type Distribution
        type_dist_query = """
            SELECT 
                file_type,
                COUNT(*) as count,
                SUM(file_size) as total_size
            FROM documents
            WHERE project_id = $1 AND deleted_at IS NULL
            GROUP BY file_type
            ORDER BY count DESC
        """
        type_dist = await db_manager.fetch_all(type_dist_query, (project_id,))
        
        # 4. Processing Performance
        perf_query = """
            SELECT 
                stage,
                COUNT(*) as executions,
                AVG(duration_ms) as avg_duration,
                MIN(duration_ms) as min_duration,
                MAX(duration_ms) as max_duration,
                COUNT(*) FILTER (WHERE status = 'failed') as failures
            FROM processing_logs
            WHERE project_id = $1 AND duration_ms IS NOT NULL
            GROUP BY stage
        """
        performance = await db_manager.fetch_all(perf_query, (project_id,))
        
        # 5. Upload Timeline (last N days)
        timeline_query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as uploads,
                COUNT(*) FILTER (WHERE status = 'completed') as successful,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                SUM(file_size) as total_size
            FROM documents
            WHERE project_id = $1 AND created_at >= $2 AND deleted_at IS NULL
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """
        timeline = await db_manager.fetch_all(timeline_query, (project_id, start_date))
        
        # 6. Vector Store Stats
        vector_stats_query = """
            SELECT 
                COUNT(*) as total_vectors,
                COUNT(DISTINCT document_id) as documents_with_vectors,
                AVG(LENGTH(content)) as avg_chunk_size,
                MIN(LENGTH(content)) as min_chunk_size,
                MAX(LENGTH(content)) as max_chunk_size
            FROM document_vectors
            WHERE project_id = $1
        """
        vector_stats = await db_manager.fetch_one(vector_stats_query, (project_id,))
        
        # 7. Top Uploaders
        uploaders_query = """
            SELECT 
                uploaded_by,
                COUNT(*) as upload_count,
                SUM(file_size) as total_uploaded
            FROM documents
            WHERE project_id = $1 AND deleted_at IS NULL
            GROUP BY uploaded_by
            ORDER BY upload_count DESC
            LIMIT 10
        """
        top_uploaders = await db_manager.fetch_all(uploaders_query, (project_id,))
        
        # 8. Recent Activity
        activity_query = """
            SELECT 
                d.id,
                d.filename,
                d.status,
                d.uploaded_by,
                d.created_at,
                d.processed_at,
                EXTRACT(EPOCH FROM (processed_at - created_at)) as processing_duration_seconds
            FROM documents d
            WHERE d.project_id = $1 AND d.deleted_at IS NULL
            ORDER BY d.created_at DESC
            LIMIT 20
        """
        recent_activity = await db_manager.fetch_all(activity_query, (project_id,))
        
        # 9. Error Analysis
        error_query = """
            SELECT 
                error_message,
                COUNT(*) as occurrences,
                MAX(created_at) as last_occurrence
            FROM documents
            WHERE project_id = $1 AND status = 'failed' AND error_message IS NOT NULL
            GROUP BY error_message
            ORDER BY occurrences DESC
            LIMIT 10
        """
        errors = await db_manager.fetch_all(error_query, (project_id,))
        
        # 10. Chunk Distribution
        chunk_dist_query = """
            SELECT 
                chunk_method,
                COUNT(*) as chunk_count,
                AVG(token_count) as avg_tokens
            FROM document_chunks
            WHERE project_id = $1
            GROUP BY chunk_method
        """
        chunk_dist = await db_manager.fetch_all(chunk_dist_query, (project_id,))
        
        # Format response
        return {
            'overview': {
                'total_documents': doc_stats['total_documents'],
                'completed': doc_stats['completed'],
                'processing': doc_stats['processing'],
                'failed': doc_stats['failed'],
                'archived': doc_stats['archived'],
                'success_rate': round((doc_stats['completed'] / doc_stats['total_documents'] * 100) if doc_stats['total_documents'] > 0 else 0, 2),
                'total_storage_bytes': doc_stats['total_storage_bytes'],
                'total_storage_gb': round(doc_stats['total_storage_bytes'] / (1024**3), 2),
                'avg_file_size_mb': round(doc_stats['avg_file_size'] / (1024**2), 2),
                'unique_uploaders': doc_stats['unique_uploaders']
            },
            'processing_methods': [
                {
                    'method': row['processing_method'] or 'unknown',
                    'count': row['count'],
                    'avg_pages': round(row['avg_pages'], 1) if row['avg_pages'] else 0
                }
                for row in method_dist
            ],
            'file_types': [
                {
                    'type': row['file_type'],
                    'count': row['count'],
                    'total_size_mb': round(row['total_size'] / (1024**2), 2)
                }
                for row in type_dist
            ],
            'performance': [
                {
                    'stage': row['stage'],
                    'executions': row['executions'],
                    'avg_duration_ms': round(row['avg_duration'], 2),
                    'min_duration_ms': row['min_duration'],
                    'max_duration_ms': row['max_duration'],
                    'failure_rate': round((row['failures'] / row['executions'] * 100) if row['executions'] > 0 else 0, 2)
                }
                for row in performance
            ],
            'timeline': [
                {
                    'date': row['date'].isoformat(),
                    'uploads': row['uploads'],
                    'successful': row['successful'],
                    'failed': row['failed'],
                    'total_size_mb': round(row['total_size'] / (1024**2), 2) if row['total_size'] else 0
                }
                for row in timeline
            ],
            'vector_store': {
                'total_vectors': vector_stats['total_vectors'],
                'documents_with_vectors': vector_stats['documents_with_vectors'],
                'avg_chunk_size': round(vector_stats['avg_chunk_size'], 2) if vector_stats['avg_chunk_size'] else 0,
                'min_chunk_size': vector_stats['min_chunk_size'],
                'max_chunk_size': vector_stats['max_chunk_size']
            },
            'top_uploaders': [
                {
                    'user': row['uploaded_by'],
                    'upload_count': row['upload_count'],
                    'total_uploaded_mb': round(row['total_uploaded'] / (1024**2), 2)
                }
                for row in top_uploaders
            ],
            'recent_activity': [
                {
                    'id': str(row['id']),
                    'filename': row['filename'],
                    'status': row['status'],
                    'uploaded_by': row['uploaded_by'],
                    'created_at': row['created_at'].isoformat(),
                    'processed_at': row['processed_at'].isoformat() if row['processed_at'] else None,
                    'processing_duration_seconds': round(row['processing_duration_seconds'], 2) if row['processing_duration_seconds'] else None
                }
                for row in recent_activity
            ],
            'errors': [
                {
                    'message': row['error_message'],
                    'occurrences': row['occurrences'],
                    'last_occurrence': row['last_occurrence'].isoformat()
                }
                for row in errors
            ],
            'chunks': [
                {
                    'method': row['chunk_method'],
                    'count': row['chunk_count'],
                    'avg_tokens': round(row['avg_tokens'], 2) if row['avg_tokens'] else 0
                }
                for row in chunk_dist
            ],
            'period_days': days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detailed analytics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Add processing stages timeline endpoint
@app.get("/api/documents/{document_id}/processing-timeline")
async def get_processing_timeline(
    document_id: str,
    project_id: str = Query(...),
    user_id: str = Query(...)
):
    """
    Get detailed processing timeline for a document
    """
    try:
        await get_project_or_404(project_id, user_id)
        
        query = """
            SELECT 
                stage,
                status,
                duration_ms,
                error_details,
                metadata,
                created_at
            FROM processing_logs
            WHERE document_id = $1
            ORDER BY created_at ASC
        """
        
        logs = await db_manager.fetch_all(query, (document_id,))
        
        timeline = [
            {
                'stage': log['stage'],
                'status': log['status'],
                'duration_ms': log['duration_ms'],
                'error_details': log['error_details'],
                'metadata': log['metadata'] or {},
                'timestamp': log['created_at'].isoformat()
            }
            for log in logs
        ]
        
        return {
            'document_id': document_id,
            'timeline': timeline,
            'total_stages': len(timeline)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing timeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SEARCH ENDPOINT
# ============================================================================

@app.post("/api/search")
async def search_documents(request: SearchRequest):
    """Semantic search across documents"""
    try:
        await get_project_or_404(request.project_id, request.user_id)

        results = await vector_manager.search_similar(
            query=request.query,
            project_id=request.project_id,
            k=request.k,
            filter_dict=request.filters
        )

        formatted_results = [
            {
                'content': doc.page_content,
                'metadata': doc.metadata,
                'document_id': doc.metadata.get('document_id'),
                'filename': doc.metadata.get('filename'),
                'chunk_index': doc.metadata.get('chunk_index'),
                'page': doc.metadata.get('page'),
                'similarity': doc.metadata.get('similarity'),
                'processing_method': doc.metadata.get('processing_method')
            }
            for doc in results
        ]

        logger.info(f"✅ Search completed: {len(formatted_results)} results")

        return {
            'query': request.query,
            'results': formatted_results,
            'count': len(formatted_results)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Add this new endpoint after your search endpoint
@app.post("/api/chat")
async def chat_with_documents(request: ChatRequest):
    """
    RAG-powered chat interface with document context
    """
    try:
        await get_project_or_404(request.project_id, request.user_id)

        # Step 1: Retrieve relevant chunks from vector store
        search_results = await vector_manager.search_similar(
            query=request.query,
            project_id=request.project_id,
            k=request.k
        )

        if not search_results:
            return {
                'response': "I couldn't find any relevant information in your documents. Try uploading some documents first or rephrasing your question.",
                'sources': [],
                'conversation_id': request.conversation_id or str(uuid.uuid4())
            }

        # Step 2: Build context from retrieved chunks
        context_parts = []
        sources = []
        
        for idx, doc in enumerate(search_results, 1):
            context_parts.append(f"[Source {idx}]\n{doc.page_content}\n")
            
            sources.append({
                'id': doc.metadata.get('id'),
                'document_id': doc.metadata.get('document_id'),
                'filename': doc.metadata.get('filename', 'Unknown'),
                'chunk_index': doc.metadata.get('chunk_index', 0),
                'page': doc.metadata.get('page'),
                'similarity': doc.metadata.get('similarity', 0),
                'preview': doc.page_content[:200] + '...' if len(doc.page_content) > 200 else doc.page_content
            })

        context = "\n".join(context_parts)

        # Step 3: Generate response using Gemini
        from google import genai
        from google.genai.types import GenerateContentConfig
        
        client = genai.Client(
            vertexai=True,
            project=Config.PROJECT_ID,
            location=Config.REGION
        )

        system_prompt = """You are a helpful AI assistant that answers questions based on the provided document context.

Rules:
1. Answer ONLY based on the provided context
2. If the context doesn't contain the answer, say so clearly
3. Be concise and accurate
4. Reference specific sources when possible (e.g., "According to Source 1...")
5. If asked about multiple topics, address each one
6. Maintain a professional but friendly tone

Context:
{context}

User Question: {query}

Provide a clear, well-structured answer:"""

        prompt = system_prompt.format(context=context, query=request.query)

        response = await client.aio.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config=GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=8000,
            )
        )

        answer = response.text

        # Step 4: Save conversation to database (optional - for history)
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # You can optionally save the conversation here
        # For now, we'll just return it
        
        logger.info(f"✅ Chat completed for project {request.project_id}: {len(sources)} sources used")

        return {
            'response': answer,
            'sources': sources,
            'conversation_id': conversation_id,
            'query': request.query,
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# Add conversation history endpoint
@app.get("/api/chat/history/{project_id}")
async def get_chat_history(
    project_id: str,
    user_id: str = Query(...),
    limit: int = Query(default=50, le=100)
):
    """
    Get chat history for a project
    (For now returns empty - you can implement DB storage later)
    """
    try:
        await get_project_or_404(project_id, user_id)
        
        # TODO: Implement chat history storage in database
        # For now, return empty array
        
        return {
            'conversations': [],
            'count': 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chat history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

# Add WebSocket endpoint (add after your other endpoints)
@app.websocket("/api/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time updates
    Client sends: {"type": "auth", "user_id": "..."}
    Server sends: {"type": "document_update", "data": {...}}
    """
    await manager.connect(websocket, project_id)
    
    try:
        # Wait for authentication
        auth_msg = await websocket.receive_json()
        user_id = auth_msg.get('user_id')
        
        if not user_id:
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        # Verify user has access to project
        try:
            has_access = await verify_project_access(project_id, user_id)
            if not has_access:
                await websocket.close(code=1008, reason="Access denied")
                return
        except Exception as e:
            logger.error(f"Access verification failed: {e}")
            await websocket.close(code=1011, reason="Verification failed")
            return
        
        # Send confirmation
        await websocket.send_json({
            "type": "connected",
            "project_id": project_id,
            "message": "Successfully connected to real-time updates"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (ping/pong, etc.)
                data = await websocket.receive_json()
                
                if data.get('type') == 'ping':
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    finally:
        manager.disconnect(websocket, project_id)


# Add helper function to broadcast document updates
async def broadcast_document_update(project_id: str, document_id: str, status: str, data: dict):
    """
    Broadcast document status update to all connected clients
    Call this from your Cloud Function or processing pipeline
    """
    message = {
        "type": "document_update",
        "document_id": document_id,
        "status": status,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast_to_project(project_id, message)


# Add endpoint to manually trigger updates (for testing)
@app.post("/api/projects/{project_id}/broadcast")
async def test_broadcast(
    project_id: str,
    message: Dict[str, Any],
    user_id: str = Query(...)
):
    """Test endpoint to broadcast messages"""
    try:
        await get_project_or_404(project_id, user_id)
        await manager.broadcast_to_project(project_id, message)
        return {"status": "success", "message": "Broadcast sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Enhanced document chunks endpoint with more details
@app.get("/api/documents/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    project_id: str = Query(...),
    user_id: str = Query(...),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, le=100)
):
    """
    Get paginated chunks for a document with full details
    """
    try:
        await get_project_or_404(project_id, user_id)
        
        offset = (page - 1) * limit
        
        # Get total count
        count_query = """
            SELECT COUNT(*) FROM document_chunks 
            WHERE document_id = $1 AND project_id = $2
        """
        total = await db_manager.fetch_one(count_query, (document_id, project_id))
        total_chunks = total[0] if total else 0
        
        # Get chunks with content
        chunks_query = """
            SELECT 
                dc.id,
                dc.chunk_index,
                dc.chunk_method,
                dc.content_preview,
                dc.token_count,
                dc.metadata,
                dv.content as full_content,
                dv.embedding is not null as has_embedding
            FROM document_chunks dc
            LEFT JOIN document_vectors dv ON dc.id = dv.id
            WHERE dc.document_id = $1 AND dc.project_id = $2
            ORDER BY dc.chunk_index
            LIMIT $3 OFFSET $4
        """
        
        chunks = await db_manager.fetch_all(
            chunks_query, 
            (document_id, project_id, limit, offset)
        )
        
        return {
            'chunks': [
                {
                    'id': str(chunk['id']),
                    'index': chunk['chunk_index'],
                    'method': chunk['chunk_method'],
                    'preview': chunk['content_preview'],
                    'full_content': chunk['full_content'],
                    'token_count': chunk['token_count'],
                    'has_embedding': chunk['has_embedding'],
                    'metadata': chunk['metadata'] or {}
                }
                for chunk in chunks
            ],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_chunks,
                'pages': (total_chunks + limit - 1) // limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get chunks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Add document insights endpoint
@app.get("/api/documents/{document_id}/insights")
async def get_document_insights(
    document_id: str,
    project_id: str = Query(...),
    user_id: str = Query(...)
):
    """
    Get AI-generated insights about the document
    """
    try:
        await get_project_or_404(project_id, user_id)
        
        # Get document details
        doc_query = """
            SELECT filename, file_type, page_count, metadata
            FROM documents
            WHERE id = $1 AND project_id = $2
        """
        doc = await db_manager.fetch_one(doc_query, (document_id, project_id))
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get sample chunks
        chunks_query = """
            SELECT content FROM document_vectors
            WHERE document_id = $1 AND project_id = $2
            ORDER BY chunk_index
            LIMIT 5
        """
        chunks = await db_manager.fetch_all(chunks_query, (document_id, project_id))
        
        if not chunks:
            return {
                'summary': 'No content available for analysis',
                'keywords': [],
                'topics': []
            }
        
        # Generate insights using Gemini
        from google import genai
        from google.genai.types import GenerateContentConfig
        
        client = genai.Client(
            vertexai=True,
            project=Config.PROJECT_ID,
            location=Config.REGION
        )
        
        content_sample = "\n\n".join([chunk['content'][:500] for chunk in chunks])
        
        prompt = f"""Analyze this document and provide:
1. A brief summary (2-3 sentences)
2. Key topics (3-5 topics)
3. Important keywords (5-10 keywords)

Document: {doc['filename']}
Type: {doc['file_type']}
Pages: {doc['page_count']}

Sample content:
{content_sample}

Return as JSON:
{{
    "summary": "brief summary",
    "topics": ["topic1", "topic2"],
    "keywords": ["keyword1", "keyword2"]
}}"""

        try:
            response = await client.aio.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json"
                )
            )
            
            import json
            insights = json.loads(response.text)
            return insights
            
        except Exception as e:
            logger.error(f"Insights generation failed: {e}")
            return {
                'summary': 'Unable to generate insights',
                'keywords': [],
                'topics': []
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "detail": str(exc) if os.getenv("DEBUG") else "An error occurred"
        }
    )

# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info"
    )







