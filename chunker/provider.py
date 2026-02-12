from typing import List

from langchain_core.documents import Document

from chunker.Unstructured.unstructured import UnstructuredProvider

class ChunkerProvider:
    def __init__(self):
        self.unstructured_client = UnstructuredProvider()

    async def get_chunks(self, document_base64: str, document_id: str) -> List[Document]:
        return await self.unstructured_client.get_chunks(document_base64, document_id)
