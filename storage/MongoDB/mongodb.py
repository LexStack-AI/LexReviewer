import asyncio
from datetime import datetime
import json
import logging
import os
from typing import List

from dotenv import load_dotenv
from langchain_community.storage.mongodb import MongoDBStore
from langchain_core.documents import Document
from langchain_mongodb import MongoDBChatMessageHistory
from pymongo import MongoClient

logger = logging.getLogger(__name__)
class MongoDBClient:
    def __init__(self):
        load_dotenv()
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.mongodb_database = os.getenv("MONGODB_DATABASE", "lexstack")
        self.mongodb_chat_history_collection = os.getenv("MONGODB_CHAT_HISTORY_COLLECTION_NAME", "chat_history")
        self.mongodb_doc_store_collection = os.getenv("MONGODB_DOC_STORE_COLLECTION_NAME", "doc_store")
        self.client = MongoClient(self.mongodb_url)
        self.db = self.client[self.mongodb_database]
        self.chat_history_collection = self.db[self.mongodb_chat_history_collection]
        self.doc_store_collection = self.db[self.mongodb_doc_store_collection]

    def get_chat_history_collection(self):
        return self.chat_history_collection

    def get_doc_store_collection(self):
        return self.doc_store_collection

    def get_chat_history(self, unique_id: str):
        return MongoDBChatMessageHistory(
            connection_string=self.mongodb_url,
            database_name=self.mongodb_database,
            collection_name=self.mongodb_chat_history_collection,
            session_id=unique_id
        )

    def get_doc_store(self) -> MongoDBStore:
        return MongoDBStore(
            connection_string=self.mongodb_url,
            db_name=self.mongodb_database,
            collection_name=self.mongodb_doc_store_collection,
        )

    async def _fetch(self, chunk_ids: List[str], document_id: str):
        return list(
            self.doc_store_collection.find(
                {"value.id": {"$in": chunk_ids}, "value.metadata.document_id": document_id}
            )
        )

    async def _fetch_chunks_of_document(self, document_id: str):
        return list(
            self.doc_store_collection.find({"value.metadata.document_id": document_id})
        )

    async def get_bounding_boxes_map(self, chunk_ids: List[str], document_id: str):
        docs = await self._fetch(chunk_ids, document_id)
        bounding_boxes_map = {}
        for doc in docs:
            chunk_id = doc["value"]["id"]
            bounding_boxes = doc["value"].get("metadata", {}).get("bounding_boxes", [])
            bounding_boxes_map[chunk_id] = bounding_boxes

        return bounding_boxes_map

    async def get_chunks_for_document(self, document_id: str):
        docs = await self._fetch_chunks_of_document(document_id)
        documents = [
            Document(
                page_content=doc["value"].get("page_content", ""),
                id=doc["value"].get("id", ""),
                metadata=doc["value"].get("metadata", {})
            )
            for doc in docs
        ]
        return documents


    async def get_doc_ids_from_mongodb(self, document_id: str) -> list[str]: 
        """
        Retrieves ALL unique doc_ids associated with a document_id directly from 
        the MongoDB collection, ensuring complete coverage.
        """
        docs = await self._fetch_chunks_of_document(document_id)
        return [str(doc["_id"]) for doc in docs]

    async def delete_document_data(self, document_id: str):
        try:
            doc_ids_to_delete = await self.get_doc_ids_from_mongodb(document_id)
            if not doc_ids_to_delete or len(doc_ids_to_delete) == 0:
                logger.info(f"No document data found to delete for document: {document_id} in MongoDB")
                return
            await self.get_doc_store().amdelete(keys=doc_ids_to_delete)
            logger.info(f"Deleted data from MongoDB for document {document_id}")
        except Exception as e:
            logger.error(f"Error deleting data from MongoDB: {e}")
            raise e

    def revert_history(self, unique_id: str, edit_timestamp: str):
        collection = self.client[self.mongodb_database][self.chat_history_collection]
        to_delete_ids = []

        # Find those document ids from mongo where it's timestamp is equal to or greater than currently edited message
        for doc in collection.find({"SessionId": unique_id}):
            try:
                history_json = json.loads(doc["History"])
                ts_str = history_json["data"]["additional_kwargs"]["metadata"]["timestamp"]
                ts = datetime.fromisoformat(ts_str)
                
                if ts >= edit_timestamp:
                    to_delete_ids.append(doc["_id"])

            except Exception as e:
                print(f"Skipping invalid doc: {e}")
                
        if to_delete_ids:
            collection.delete_many({"_id": {"$in": to_delete_ids}})
