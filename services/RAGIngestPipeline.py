"""End-to-end pipeline: chunk PDF, summarize chunks, and index for retrieval."""

import asyncio
import logging

from langchain_core.documents.base import Document

from services.ChunkSummarizer import ChunkSummarizer
from services.EmbeddingIndexer import EmbeddingIndexer
from services.PDFChunker import PDFChunker

logger = logging.getLogger(__name__)


class RAGIngestPipeline:
    """Coordinates chunking, summarization, and indexing for a new document."""

    def __init__(self):
        self.pdf_chunker = PDFChunker()
        self.chunk_summarizer = ChunkSummarizer()
        self.embedding_indexer = EmbeddingIndexer()

    async def ingest_document_if_new(self, document_id, document_base64):
        """Run the ingest pipeline only if the document has not been indexed yet."""
        document_data_exists = await self.embedding_indexer.document_data_exists(document_id)
        if document_data_exists:
            logger.debug(f"Document data already exists for document: {document_id}")
            return

        # 1) Chunk the raw PDF, 2) summarize each chunk, 3) index into vector + doc stores.
        chunks: list[Document] = await self.pdf_chunker.get_chunks(document_base64, document_id)
        summaries = await self.chunk_summarizer.summarize(chunks, document_id)
        await self.embedding_indexer.embed_and_index(document_id, chunks, summaries)
        logger.debug(f"Ingested document {document_id}")