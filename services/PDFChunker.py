"""Thin wrapper that exposes a PDF-to-chunks interface for the ingest pipeline."""

from typing import List

from langchain_core.documents import Document

from chunker.provider import ChunkerProvider


class PDFChunker:
    """Delegates to the configured chunker provider (currently Unstructured)."""

    def __init__(self):
        self.chunker = ChunkerProvider()

    def get_chunks(self, document_base64: str, document_id: str) -> List[Document]:
        """Return structured text chunks for a base64-encoded PDF document."""
        return self.chunker.get_chunks(document_base64, document_id)