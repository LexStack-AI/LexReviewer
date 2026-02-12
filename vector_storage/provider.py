"""Abstraction over the concrete vector database (Qdrant)."""

from typing import Any, Dict, List

from langchain_core.documents import Document

from vector_storage.Qdrant.qdrant import QdrantDatabaseProvider


class VectorStorageProvider:
    """Expose a stable interface that services can use regardless of backend."""

    def __init__(self):
        self.provider = QdrantDatabaseProvider()

    async def get_multivector_retriever(self, document_id: str, k_value: int):
        return await self.provider.get_multivector_retriever(document_id, k_value)

    async def embed_and_index(self, document_id: str, chunk_documents: list[Document], summaries: list[str]):
        return await self.provider.embed_and_index(document_id, chunk_documents, summaries)

    async def delete_document_data(self, document_id: str):
        return await self.provider.delete_document_data(document_id)

    async def document_data_exists(self, document_id: str) -> bool:
        return await self.provider.document_data_exists(document_id)

    async def get_reference_positions(self, retrieved_chunks: List[Dict[str, Any]], document_id: str) -> List[Dict[str, Any]]:
        return await self.provider.get_reference_positions(retrieved_chunks, document_id)