from abc import ABC, abstractmethod
from langchain_core.documents import Document
from typing import Dict, List
import logging
import asyncio
 
logger = logging.getLogger(__name__)
 
class ChunkingStrategy(ABC):
    """Base class for chunking strategies"""
   
    @abstractmethod
    async def chunk(self, text: str, metadata: Dict = None) -> List[Document]:
        pass
 
class RecursiveChunker(ChunkingStrategy):
    """Recursive chunking with multiple separators"""
   
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
   
    async def chunk(self, text: str, metadata: Dict = None) -> List[Document]:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
       
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
       
        chunks = splitter.split_text(text)
       
        return [
            Document(
                page_content=chunk,
                metadata={
                    'chunk_index': idx,
                    'chunk_method': 'recursive',
                    'chunk_size': len(chunk),
                    **(metadata or {})
                }
            )
            for idx, chunk in enumerate(chunks)
        ]
 
class SemanticChunker(ChunkingStrategy):
    """Semantic chunking based on sentence embeddings"""
   
    def __init__(self):
        from langchain_experimental.text_splitter import SemanticChunker as LCSemanticChunker
        from langchain_google_vertexai import VertexAIEmbeddings
        from config import Config
       
        self.embeddings = VertexAIEmbeddings(
            model_name=Config.EMBEDDING_MODEL,
            project=Config.PROJECT_ID
        )
        self.splitter = LCSemanticChunker(
            embeddings=self.embeddings,
            breakpoint_threshold_type="percentile"
        )
   
    async def chunk(self, text: str, metadata: Dict = None) -> List[Document]:
        def _sync_chunk():
            return self.splitter.create_documents([text])
       
        loop = asyncio.get_event_loop()
        docs = await loop.run_in_executor(None, _sync_chunk)
       
        for idx, doc in enumerate(docs):
            doc.metadata.update({
                'chunk_index': idx,
                'chunk_method': 'semantic',
                'chunk_size': len(doc.page_content),
                **(metadata or {})
            })
       
        return docs
 
class SentenceChunker(ChunkingStrategy):
    """Sentence-based chunking"""
   
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
        self._nltk_ready = False
   
    def _ensure_nltk_data(self):
        """Ensure NLTK data is available"""
        if self._nltk_ready:
            return
       
        import nltk
        import os
       
        nltk_data_path = '/tmp/nltk_data'
        os.makedirs(nltk_data_path, exist_ok=True)
        nltk.data.path.append(nltk_data_path)
       
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', download_dir=nltk_data_path, quiet=True)
       
        self._nltk_ready = True
   
    async def chunk(self, text: str, metadata: Dict = None) -> List[Document]:
        import nltk
       
        self._ensure_nltk_data()
       
        def _sync_tokenize():
            return nltk.sent_tokenize(text)
       
        loop = asyncio.get_event_loop()
        sentences = await loop.run_in_executor(None, _sync_tokenize)
       
        chunks = []
        current_chunk = []
        current_length = 0
       
        for sentence in sentences:
            sentence_length = len(sentence)
           
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
       
        if current_chunk:
            chunks.append(' '.join(current_chunk))
       
        return [
            Document(
                page_content=chunk,
                metadata={
                    'chunk_index': idx,
                    'chunk_method': 'sentence',
                    'chunk_size': len(chunk),
                    **(metadata or {})
                }
            )
            for idx, chunk in enumerate(chunks)
        ]
 
class ChunkingFactory:
    """Factory for chunking strategies"""
   
    def __init__(self):
        self.strategies = {
            'recursive': RecursiveChunker(),
            'semantic': SemanticChunker(),
            'sentence': SentenceChunker(),
        }
   
    async def chunk_text(
        self,
        text: str,
        method: str = 'recursive',
        metadata: Dict = None
    ) -> List[Document]:
        """Chunk text using specified method"""
       
        strategy = self.strategies.get(method, self.strategies['recursive'])
       
        try:
            return await strategy.chunk(text, metadata)
        except Exception as e:
            logger.warning(f"Chunking with {method} failed: {e}, falling back to recursive")
            return await self.strategies['recursive'].chunk(text, metadata)
 