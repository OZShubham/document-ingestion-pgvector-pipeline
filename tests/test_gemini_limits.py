# tests/test_gemini_limits.py

import pytest
import asyncio
from gemini_processor import (
    EnhancedGeminiProcessor,
    SmartDocumentProcessorFactory
)
from pypdf import PdfWriter
import io

@pytest.fixture
def processor():
    return EnhancedGeminiProcessor()

@pytest.fixture
def factory():
    return SmartDocumentProcessorFactory()

def create_test_pdf(num_pages: int) -> bytes:
    """Create a test PDF with specified number of pages"""
    writer = PdfWriter()
    for i in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()

class TestGeminiLimits:
    """Test Gemini limits handling"""
    
    @pytest.mark.asyncio
    async def test_small_pdf_uses_inline(self, processor):
        """Test that small PDFs use inline processing"""
        pdf_bytes = create_test_pdf(10)  # 10 pages
        
        result = await processor.process(
            file_bytes=pdf_bytes,
            filename='test_small.pdf',
            mime_type='application/pdf'
        )
        
        assert result.processing_method == 'gemini-inline'
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_large_pdf_uses_file_api(self, processor):
        """Test that 20-50MB PDFs use File API"""
        # Create a 25MB PDF (mock)
        pdf_bytes = b'0' * (25 * 1024 * 1024)
        
        result = await processor.process(
            file_bytes=pdf_bytes,
            filename='test_large.pdf',
            mime_type='application/pdf'
        )
        
        # Should use File API or fail with size error
        assert result.processing_method in ['gemini-fileapi', 'gemini']
    
    @pytest.mark.asyncio
    async def test_huge_pdf_returns_error(self, processor):
        """Test that PDFs > 50MB return error"""
        # Create a 60MB PDF (mock)
        pdf_bytes = b'0' * (60 * 1024 * 1024)
        
        result = await processor.process(
            file_bytes=pdf_bytes,
            filename='test_huge.pdf',
            mime_type='application/pdf'
        )
        
        assert result.error is not None
        assert '50MB' in result.error
    
    @pytest.mark.asyncio
    async def test_too_many_pages_truncates(self, processor):
        """Test that PDFs with > 1000 pages are truncated"""
        pdf_bytes = create_test_pdf(1500)  # 1500 pages
        
        result = await processor.process(
            file_bytes=pdf_bytes,
            filename='test_many_pages.pdf',
            mime_type='application/pdf'
        )
        
        # Should have warning about truncation
        assert result.metadata is not None
        assert 'warning' in result.metadata
        assert 'truncated' in result.metadata['warning'].lower()
    
    @pytest.mark.asyncio
    async def test_factory_skips_gemini_for_huge_pdf(self, factory):
        """Test that factory skips Gemini for files that are too large"""
        pdf_bytes = create_test_pdf(1500)  # 1500 pages
        
        result = await factory.process_document(
            file_bytes=pdf_bytes,
            filename='test_huge.pdf',
            mime_type='application/pdf'
        )
        
        # Should use PyMuPDF, not Gemini
        assert result.processing_method in ['pymupdf', 'pypdf']
        assert 'gemini' not in result.processing_method

if __name__ == '__main__':
    pytest.main([__file__, '-v'])