import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class Config:
    # GCP Settings
    PROJECT_ID: str = os.getenv('GCP_PROJECT_ID')
    REGION: str = os.getenv('GCP_REGION', 'us-central1')
    
    # Cloud SQL (Password Authentication)
    DB_INSTANCE: str = os.getenv('DB_INSTANCE')
    DB_REGION: str = os.getenv('DB_REGION', 'us-central1')
    DB_NAME: str = os.getenv('DB_NAME', 'vectordb')
    # Note: DB_PASSWORD is read from environment variable in database_manager.py
    
    # GCS
    BUCKET_NAME: str = os.getenv('GCS_BUCKET_NAME')
    DOCUMENTS_PREFIX: str = "documents"
    
    # Pub/Sub
    PUBSUB_TOPIC: str = os.getenv('PUBSUB_TOPIC', 'document-processing')
    
    # Embeddings
    EMBEDDING_MODEL: str = os.getenv('EMBEDDING_MODEL', 'text-embedding-005')
    EMBEDDING_DIMENSION: int = 768

    # Gemini Document Understanding Limits
    GEMINI_MAX_PAGES = 1000              # Max pages Gemini can process
    GEMINI_TOKENS_PER_PAGE = 258         # Each page = 258 tokens
    GEMINI_INLINE_LIMIT_MB = 20          # Inline data limit
    GEMINI_INLINE_LIMIT_BYTES = 20 * 1024 * 1024
    GEMINI_FILE_API_LIMIT_MB = 50        # File API limit
    GEMINI_FILE_API_LIMIT_BYTES = 50 * 1024 * 1024
    GEMINI_MAX_RESOLUTION = 3072         # Max image resolution
    
    # File API Settings
    FILE_API_TTL_HOURS = 48              # Files stored for 48 hours
    FILE_API_AUTO_CLEANUP = True         # Auto-delete after processing

    
    # Gemini
    GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
    GEMINI_SUPPORTED_TYPES: set = field(default_factory=lambda: {
        'application/pdf', 'image/jpeg', 'image/png', 'image/webp'
    })
    
    # Vector Store
    VECTOR_TABLE_NAME: str = os.getenv('VECTOR_TABLE_NAME', 'document_vectors')
    
    # Processing Settings
    MAX_RETRIES: int = 3
    MAX_FILE_SIZE_MB: int = 200
    TIMEOUT_SECONDS: int = 540
    
    # Chunking Strategies
    CHUNK_STRATEGIES: Dict = field(default_factory=lambda: {
        'fixed': {'size': 1000, 'overlap': 200},
        'recursive': {'size': 1000, 'overlap': 200},
        'semantic': {'buffer_size': 1, 'breakpoint_type': 'percentile'},
        'sentence': {'chunk_size': 1000},
        'markdown': {'size': 1000, 'overlap': 100},
    })
    
    PROCESSING_METHODS: Dict = field(default_factory=lambda: {
        # PDFs: Try Gemini first (with smart routing), fallback to PyMuPDF
        'application/pdf': ['gemini', 'pymupdf', 'pypdf'],
        
        # Images: Gemini only (best for OCR and understanding)
        'image/jpeg': ['gemini'],
        'image/png': ['gemini'],
        'image/webp': ['gemini'],
        
        # Office Documents: Specific processors
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['docx'],
        'application/msword': ['docx'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['openpyxl'],
        'application/vnd.ms-excel': ['openpyxl'],
        
        # Text files: Simple text processor
        'text/plain': ['text'],
        'text/markdown': ['markdown'],
        'text/html': ['html'],
    })

    # ======= Fallback Strategies =======
    
    # When to skip Gemini and go straight to fallback
    SKIP_GEMINI_IF_PAGES_EXCEED = 1000
    SKIP_GEMINI_IF_SIZE_MB_EXCEED = 50
    
    # Truncation strategy for large PDFs
    TRUNCATE_LARGE_PDFS = True           # Auto-truncate to first N pages
    TRUNCATE_TO_PAGES = 1000             # Truncate to this many pages
    NOTIFY_ON_TRUNCATION = True          # Notify users about truncation
    
    # ======= Performance Optimization =======
    
    # Cache settings for repeated processing
    ENABLE_PROCESSING_CACHE = True
    CACHE_TTL_HOURS = 24
    
    # Parallel processing limits
    MAX_CONCURRENT_GEMINI_CALLS = 10
    MAX_CONCURRENT_PYMUPDF_CALLS = 20