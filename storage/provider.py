"""Storage abstraction used by services to talk to the MongoDB backend."""

from typing import List

from pymongo.cursor import Cursor
from storage.MongoDB.mongodb import MongoDBClient


class Storage:
    """Thin façade over the concrete MongoDB client, for easier swapping later."""

    def __init__(self):
        self.provider = MongoDBClient()

    def get_chat_history_collection(self):
        return self.provider.get_chat_history_collection()

    def get_doc_store(self):
        return self.provider.get_doc_store()

    def get_chat_history(self, unique_id):
        return self.provider.get_chat_history(unique_id)

    def revert_history(self, unique_id: str, edit_timestamp: str):
        return self.provider.revert_history(unique_id, edit_timestamp)

    async def delete_document_data(self, document_id: str):
        return await self.provider.delete_document_data(document_id)

    async def get_bounding_boxes_map(self, chunk_ids: List[str], document_id: str):
        return await self.provider.get_bounding_boxes_map(chunk_ids, document_id)

    async def get_chunks_for_document(self, document_id: str):
        return await self.provider.get_chunks_for_document(document_id)
