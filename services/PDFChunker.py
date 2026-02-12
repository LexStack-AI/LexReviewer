from typing import List

from langchain_core.documents import Document

from chunker.provider import ChunkerProvider

class PDFChunker:
    def __init__(self):
        self.chunker = ChunkerProvider()

    def get_chunks(self, document_base64: str, document_id: str) -> List[Document]:
        return self.chunker.get_chunks(document_base64, document_id)