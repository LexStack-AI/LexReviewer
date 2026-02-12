"""Service that owns embedding-based + lexical retrieval and indexing."""

import os
import traceback

from dotenv import load_dotenv
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from storage.provider import Storage
from vector_storage.provider import VectorStorageProvider


class EmbeddingIndexer:
    """Combines vector search and BM25 to retrieve relevant document chunks."""

    def __init__(self):
        load_dotenv()
        self.vector_database_provider = VectorStorageProvider()
        self.storage_client = Storage()
        self.max_number_of_candidates_for_retriever = int(os.getenv("MAX_NUMBER_OF_CANDIDATES_FOR_RETRIEVER", 10))

    async def get_retriever(self, document_id):
        try:
            # Dense retriever over chunk summaries in Qdrant.
            vector_retriever = await self.vector_database_provider.get_multivector_retriever(
                document_id, k_value=self.max_number_of_candidates_for_retriever
            )

            # Lexical BM25 retriever over original chunks stored in Mongo.
            documents = await self.storage_client.get_chunks_for_document(document_id)
            bm25_retriever = BM25Retriever.from_documents(
                documents,
                k=self.max_number_of_candidates_for_retriever
            )

            # Blend lexical and semantic signals for more robust retrieval.
            return EnsembleRetriever(
                retrievers=[bm25_retriever, vector_retriever],
                weights=[0.4, 0.6]
            )

        except Exception as e:
            traceback.print_exc()
            raise e

    async def embed_and_index(self, document_id, chunk_documents: list[Document], summaries: list[str]):
        """Store chunk summaries in Qdrant and full chunks in the doc store."""
        return await self.vector_database_provider.embed_and_index(document_id, chunk_documents, summaries)
        
    async def delete_document_data(self, document_id: str):
        """Remove all vector + chunk data for a document from backing stores."""
        return await self.vector_database_provider.delete_document_data(document_id)

    async def document_data_exists(self, document_id: str) -> bool:
        """Check if any stored chunks exist for this document."""
        return await self.vector_database_provider.document_data_exists(document_id)
        