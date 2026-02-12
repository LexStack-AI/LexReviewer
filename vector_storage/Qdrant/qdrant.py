"""Qdrant-backed implementation for vector search and reference position lookup."""

import logging
import os
import traceback
import uuid
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_classic.retrievers import MultiVectorRetriever
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    VectorParams,
)

from llm_provider.provider import LlmProvider
from storage.provider import Storage

logger = logging.getLogger(__name__)


class QdrantDatabaseProvider:
    """Owns the Qdrant collection and bridges it to LangChain retrievers."""

    def __init__(self):
        load_dotenv()
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        qdrant_timeout = int(os.getenv("QDRANT_TIMEOUT", "60"))
        if not qdrant_url or not qdrant_api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set")

        qdrant_args = {
            "url": qdrant_url,
            "api_key": qdrant_api_key,
            "timeout": qdrant_timeout
        }
        self.qdrant_client = QdrantClient(**qdrant_args)
        
        self.qdrant_collection_name = os.getenv("QDRANT_COLLECTION_NAME", "documents")
        self.qdrant_vector_size = int(os.getenv("QDRANT_VECTOR_SIZE", "3072"))
        
        # Lazily create the collection if it does not exist yet.
        if not self.qdrant_client.collection_exists(self.qdrant_collection_name):
            self.create_parent_collection()

        llm_provider = LlmProvider()
        embedding_model = llm_provider.get_embedding_model()
        self.qdrant_vectorstore = QdrantVectorStore.construct_instance(
            collection_name=self.qdrant_collection_name,
            embedding=embedding_model,
            client_options=qdrant_args
        )

        self.storage_client = Storage()
        self.doc_store = self.storage_client.get_doc_store()

    def create_parent_collection(self):
        # Create parent collection in Qdrant with vector + payload index.
        try:
            self.qdrant_client.create_collection(
                collection_name=self.qdrant_collection_name, 
                vectors_config=VectorParams(
                    size=self.qdrant_vector_size, 
                    distance=Distance.COSINE
                )
            )
            # Create payload index for document_id
            self.qdrant_client.create_payload_index(
                collection_name=self.qdrant_collection_name,
                field_name="metadata.document_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info(f"Created collection {self.qdrant_collection_name} with vector size {self.qdrant_vector_size}")
        except Exception as e:
            logger.error(f"Error creating collection {self.qdrant_collection_name}: {e}")
            traceback.print_exc()
            raise e

    async def get_multivector_retriever(self, document_id: str, k_value: int):
        try:
            vector_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.document_id",
                        match=MatchValue(value=str(document_id)),
                    )
                ]
            )

            vector_search_kwargs = {
                "k": k_value,
                "score_threshold": 0.4,
                "filter": vector_filter
            }

            return MultiVectorRetriever(
                vectorstore=self.qdrant_vectorstore,
                docstore=self.doc_store,
                search_kwargs=vector_search_kwargs,
                id_key="doc_id"
            )

        except Exception as e:
            traceback.print_exc()
            raise e

    async def embed_and_index(self, document_id: str, chunk_documents: list[Document], summaries: list[str]):
        try:
            if len(summaries) != len(chunk_documents):
                logger.error("Summaries and chunk documents must have the same length")
                raise ValueError("Summaries and chunk documents must have the same length")

            retriever = MultiVectorRetriever(
                vectorstore=self.qdrant_vectorstore,
                docstore=self.doc_store,
            )

            doc_ids = [str(uuid.uuid4()) for _ in chunk_documents]
            vector_store_data = []

            for i, summary in enumerate(summaries):
                if not summary or not summary.strip():
                    continue

                metadata = {
                    "doc_id": doc_ids[i],
                    "document_id": str(document_id),
                    "chunk_id": chunk_documents[i].id
                }

                document_data = Document(
                    page_content=summary,
                    metadata=metadata
                )
                vector_store_data.append(document_data)

            await retriever.vectorstore.aadd_documents(vector_store_data)
            await retriever.docstore.amset(list(zip(doc_ids, chunk_documents)))
        except Exception as e:
            traceback.print_exc()
            raise e

    async def delete_document_data(self, document_id: str):
        try:
            await self.delete_document_data_from_qdrant(document_id)
            await self.storage_client.delete_document_data(document_id)
        except Exception as e:
            logger.error(f"Error deleting data for document {document_id}: {e}")
            raise e

        logger.info(f"Deletion complete for document: {document_id}")

    async def delete_document_data_from_qdrant(self, document_id: str):
        try:
            if not await self.document_data_exists(document_id):
                logger.info(f"No document data found to delete for document: {document_id} in Qdrant")
                return
            self.qdrant_client.delete(
                collection_name=self.qdrant_collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.document_id",
                            match=MatchValue(value=str(document_id))
                        )
                    ]
                )
            )
            logger.info(f"Deleted data from Qdrant for document {document_id}")
        except Exception as e:
            logger.error(f"Error deleting data from Qdrant: {e}")
            raise e

    async def document_data_exists(self, document_id: str) -> bool:
        if not self.qdrant_client.collection_exists(self.qdrant_collection_name):
            raise ValueError(f"Parent collection {self.qdrant_collection_name} does not exist")

        count = self.qdrant_client.count(
            collection_name=self.qdrant_collection_name,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.document_id",
                        match=MatchValue(value=str(document_id))
                    )
                ]
            ),
            exact=False
        )
        return count.count > 0

    async def get_reference_positions(self, retrieved_chunks: List[Dict[str, Any]], document_id: str) -> List[Dict[str, Any]]:
        """Get reference positions (bounding boxes) for retrieved chunks."""
        if not retrieved_chunks:
            return []

        try:
            chunk_ids = [chunk["chunk_id"] for chunk in retrieved_chunks if "chunk_id" in chunk]
            bounding_boxes_map = await self.storage_client.get_bounding_boxes_map(chunk_ids, document_id)

            enriched_chunks = []
            for chunk in retrieved_chunks:
                chunk_id = chunk.get("chunk_id")
                if not chunk_id:
                    continue
                enriched_chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "chunk_number": chunk.get("chunk_number"),
                        "document_id": chunk.get("document_id", document_id),
                        "bounding_boxes": bounding_boxes_map.get(chunk_id, []),
                    }
                )
            return enriched_chunks
        except Exception as exc:
            print(f"Error getting bounding boxes: {exc}")
            return []