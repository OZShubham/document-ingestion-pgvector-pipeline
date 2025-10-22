from google import genai
from google.genai.types import GenerateContentConfig, Part
from typing import Dict, Any, Optional
import logging
import io

logger = logging.getLogger(__name__)

class EnhancedGeminiProcessor:
    """
    Enhanced Gemini processor with proper limits handling
    """
    
    # Gemini Limits
    MAX_PAGES = 1000
    TOKENS_PER_PAGE = 258
    INLINE_DATA_LIMIT_MB = 20
    INLINE_DATA_LIMIT_BYTES = 20 * 1024 * 1024
    FILE_API_LIMIT_MB = 50
    FILE_API_LIMIT_BYTES = 50 * 1024 * 1024
    MAX_RESOLUTION = 3072
    
    def __init__(self):
        from config import Config
        self.client = genai.Client(
            vertexai=True,
            project=Config.PROJECT_ID,
            location=Config.REGION
        )
        self.config = Config
    
    def supports(self, mime_type: str) -> bool:
        """Check if file type is supported by Gemini"""
        return mime_type in self.config.GEMINI_SUPPORTED_TYPES
    
    async def process(
        self, 
        file_bytes: bytes, 
        filename: str, 
        mime_type: str = None,
        **kwargs
    ):
        """
        Process document with intelligent handling of Gemini limitations
        """
        from document_processors import ProcessedDocument
        
        file_size = len(file_bytes)
        
        # Step 1: Validate file size
        if file_size > self.FILE_API_LIMIT_BYTES:
            logger.warning(f"File {filename} ({file_size} bytes) exceeds File API limit")
            return ProcessedDocument(
                text="",
                metadata={'file_size': file_size},
                processing_method='gemini',
                error=f"File size {file_size / (1024*1024):.1f}MB exceeds Gemini's 50MB limit"
            )
        
        # Step 2: Check page count (for PDFs)
        page_count = await self._estimate_page_count(file_bytes, mime_type)
        if page_count and page_count > self.MAX_PAGES:
            logger.warning(f"File {filename} has {page_count} pages, exceeds {self.MAX_PAGES} limit")
            
            # Strategy: Process in chunks or use alternative processor
            return await self._handle_large_document(
                file_bytes, filename, mime_type, page_count
            )
        
        # Step 3: Choose processing method based on file size
        if file_size <= self.INLINE_DATA_LIMIT_BYTES:
            # Use inline processing (faster)
            return await self._process_inline(file_bytes, filename, mime_type)
        else:
            # Use File API (for 20MB - 50MB files)
            return await self._process_with_file_api(file_bytes, filename, mime_type)
    
    async def _estimate_page_count(
        self, 
        file_bytes: bytes, 
        mime_type: str
    ) -> Optional[int]:
        """Estimate page count from PDF"""
        if mime_type != 'application/pdf':
            return None
        
        try:
            from pypdf import PdfReader
            pdf = PdfReader(io.BytesIO(file_bytes))
            return len(pdf.pages)
        except Exception as e:
            logger.warning(f"Could not estimate page count: {e}")
            return None
    
    async def _process_inline(
        self, 
        file_bytes: bytes, 
        filename: str, 
        mime_type: str
    ):
        """Process file using inline data (< 20MB)"""
        from document_processors import ProcessedDocument
        import json
        
        extraction_prompt = """Analyze this document thoroughly and extract:
        1. Full text content preserving structure and formatting
        2. All tables in markdown format with headers
        3. Descriptions of images, charts, and diagrams
        4. Document metadata (title, author, date, subject if present)
        5. Logical sections with headings
        6. Page numbers for each section (if applicable)
        
        Return as JSON:
        {
            "text": "full text content",
            "metadata": {"title": "", "author": "", "date": "", "pages": 0},
            "sections": [{"heading": "", "content": "", "page": 0}],
            "tables": [{"content": "", "description": "", "page": 0}],
            "images": [{"description": "", "page": 0}]
        }"""
        
        try:
            logger.info(f"Processing {filename} inline ({len(file_bytes)} bytes)")
            
            response = await self.client.aio.models.generate_content(
                model=self.config.GEMINI_MODEL,
                contents=[
                    extraction_prompt,
                    Part.from_bytes(data=file_bytes, mime_type=mime_type)
                ],
                config=GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json"
                )
            )
            
            result = json.loads(response.text)
            
            return ProcessedDocument(
                text=result.get('text', ''),
                metadata=result.get('metadata', {}),
                sections=result.get('sections', []),
                tables=result.get('tables', []),
                images=result.get('images', []),
                page_count=result.get('metadata', {}).get('pages', 0),
                processing_method='gemini-inline'
            )
            
        except Exception as e:
            logger.error(f"Inline processing failed: {e}")
            return ProcessedDocument(
                text="",
                metadata={},
                processing_method='gemini-inline',
                error=str(e)
            )
    
    async def _process_with_file_api(
        self, 
        file_bytes: bytes, 
        filename: str, 
        mime_type: str
    ):
        """Process file using File API (20MB - 50MB)"""
        from document_processors import ProcessedDocument
        import json
        import asyncio
        
        extraction_prompt = """Analyze this document thoroughly and extract:
        1. Full text content preserving structure
        2. All tables in markdown format
        3. Descriptions of images and charts
        4. Document metadata
        5. Logical sections with headings
        
        Return as JSON with keys: text, metadata, sections, tables, images"""
        
        try:
            logger.info(f"Processing {filename} with File API ({len(file_bytes)} bytes)")
            
            # Upload file to Gemini File API (48 hour storage)
            file_io = io.BytesIO(file_bytes)
            
            # Run in executor since File API is synchronous
            def _sync_upload():
                return self.client.files.upload(
                    file=file_io,
                    config=dict(mime_type=mime_type)
                )
            
            loop = asyncio.get_event_loop()
            uploaded_file = await loop.run_in_executor(None, _sync_upload)
            
            logger.info(f"File uploaded: {uploaded_file.name}")
            
            # Process with Gemini
            response = await self.client.aio.models.generate_content(
                model=self.config.GEMINI_MODEL,
                contents=[uploaded_file, extraction_prompt],
                config=GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json"
                )
            )
            
            result = json.loads(response.text)
            
            # Clean up - delete file from File API
            try:
                def _sync_delete():
                    self.client.files.delete(name=uploaded_file.name)
                
                await loop.run_in_executor(None, _sync_delete)
                logger.info(f"File deleted: {uploaded_file.name}")
            except Exception as e:
                logger.warning(f"Could not delete file: {e}")
            
            return ProcessedDocument(
                text=result.get('text', ''),
                metadata=result.get('metadata', {}),
                sections=result.get('sections', []),
                tables=result.get('tables', []),
                images=result.get('images', []),
                page_count=result.get('metadata', {}).get('pages', 0),
                processing_method='gemini-fileapi'
            )
            
        except Exception as e:
            logger.error(f"File API processing failed: {e}")
            return ProcessedDocument(
                text="",
                metadata={},
                processing_method='gemini-fileapi',
                error=str(e)
            )
    
    async def _handle_large_document(
        self, 
        file_bytes: bytes, 
        filename: str, 
        mime_type: str,
        page_count: int
    ):
        """Handle documents exceeding page limits"""
        from document_processors import ProcessedDocument
        
        logger.warning(f"Document {filename} has {page_count} pages (limit: {self.MAX_PAGES})")
        
        # Strategy 1: Process first N pages only
        if mime_type == 'application/pdf':
            logger.info(f"Processing first {self.MAX_PAGES} pages only")
            
            try:
                # Extract first N pages
                truncated_pdf = await self._extract_pages(
                    file_bytes, 
                    max_pages=self.MAX_PAGES
                )
                
                # Process truncated version
                result = await self._process_with_file_api(
                    truncated_pdf, 
                    filename, 
                    mime_type
                )
                
                # Add warning to metadata
                if result.metadata is None:
                    result.metadata = {}
                
                result.metadata['warning'] = f'Document truncated: only first {self.MAX_PAGES} of {page_count} pages processed'
                result.metadata['total_pages'] = page_count
                result.metadata['processed_pages'] = self.MAX_PAGES
                
                return result
                
            except Exception as e:
                logger.error(f"Could not process truncated document: {e}")
        
        # Strategy 2: Return error and suggest alternative processor
        return ProcessedDocument(
            text="",
            metadata={
                'total_pages': page_count,
                'max_pages': self.MAX_PAGES
            },
            processing_method='gemini',
            error=f"Document has {page_count} pages, exceeds Gemini's {self.MAX_PAGES} page limit. Will fallback to PyMuPDF."
        )
    
    async def _extract_pages(
        self, 
        file_bytes: bytes, 
        max_pages: int
    ) -> bytes:
        """Extract first N pages from PDF"""
        from pypdf import PdfReader, PdfWriter
        import asyncio
        
        def _sync_extract():
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            pdf_writer = PdfWriter()
            
            # Add first max_pages pages
            for i in range(min(max_pages, len(pdf_reader.pages))):
                pdf_writer.add_page(pdf_reader.pages[i])
            
            # Write to bytes
            output = io.BytesIO()
            pdf_writer.write(output)
            return output.getvalue()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_extract)


# ==============================================================================
# ENHANCED DOCUMENT PROCESSOR FACTORY WITH SMART FALLBACK
# ==============================================================================

class SmartDocumentProcessorFactory:
    """
    Enhanced factory with intelligent fallback when Gemini fails
    """
    
    def __init__(self):
        self.gemini_processor = EnhancedGeminiProcessor()
        
        # Import other processors
        from document_processors import (
            PyMuPDFProcessor,
            PyPDFProcessor,
            DocxProcessor,
            ExcelProcessor,
            TextProcessor
        )
        
        self.processors = {
            'gemini': self.gemini_processor,
            'pymupdf': PyMuPDFProcessor(),
            'pypdf': PyPDFProcessor(),
            'docx': DocxProcessor(),
            'openpyxl': ExcelProcessor(),
            'text': TextProcessor(),
        }
    
    async def process_document(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        preferred_method: str = None
    ):
        """
        Process document with smart fallback strategies
        """
        from config import Config
        from document_processors import ProcessedDocument
        
        file_size_mb = len(file_bytes) / (1024 * 1024)
        
        logger.info(f"Processing {filename} ({file_size_mb:.1f}MB, {mime_type})")
        
        # Determine available methods
        available_methods = Config.PROCESSING_METHODS.get(mime_type, [])
        
        if not available_methods:
            return ProcessedDocument(
                text="",
                metadata={},
                error=f"Unsupported file type: {mime_type}"
            )
        
        # Smart method selection based on file characteristics
        if mime_type == 'application/pdf':
            # Estimate page count
            try:
                from pypdf import PdfReader
                pdf = PdfReader(io.BytesIO(file_bytes))
                page_count = len(pdf.pages)
                
                logger.info(f"PDF has {page_count} pages")
                
                # Decision tree for PDF processing
                if page_count > EnhancedGeminiProcessor.MAX_PAGES:
                    # Too large for Gemini, use PyMuPDF
                    logger.info("PDF exceeds Gemini page limit, using PyMuPDF")
                    methods_to_try = ['pymupdf', 'pypdf']
                elif file_size_mb > 50:
                    # Too large for Gemini File API
                    logger.info("PDF exceeds Gemini size limit, using PyMuPDF")
                    methods_to_try = ['pymupdf', 'pypdf']
                elif 'gemini' in available_methods:
                    # Gemini first, then fallback
                    methods_to_try = ['gemini', 'pymupdf', 'pypdf']
                else:
                    methods_to_try = available_methods
                    
            except Exception as e:
                logger.warning(f"Could not analyze PDF: {e}")
                methods_to_try = available_methods
        else:
            # For non-PDF files
            if preferred_method and preferred_method in available_methods:
                methods_to_try = [preferred_method] + [
                    m for m in available_methods if m != preferred_method
                ]
            else:
                methods_to_try = available_methods
        
        # Try each method until one succeeds
        last_error = None
        
        for method in methods_to_try:
            processor = self.processors.get(method)
            if not processor or not processor.supports(mime_type):
                continue
            
            try:
                logger.info(f"Trying {method} processor...")
                
                result = await processor.process(
                    file_bytes=file_bytes,
                    filename=filename,
                    mime_type=mime_type
                )
                
                # Check if processing was successful
                if result.error is None and result.text:
                    logger.info(f"✓ Successfully processed with {method}")
                    return result
                
                # If Gemini returned error due to limits, try next method immediately
                if method == 'gemini' and result.error:
                    logger.warning(f"Gemini failed: {result.error}, trying fallback...")
                    last_error = result.error
                    continue
                
                last_error = result.error
                
            except Exception as e:
                logger.error(f"Processor {method} failed: {e}")
                last_error = str(e)
                continue
        
        # All methods failed
        return ProcessedDocument(
            text="",
            metadata={'file_size': len(file_bytes), 'mime_type': mime_type},
            error=f"All processing methods failed. Last error: {last_error}"
        )

