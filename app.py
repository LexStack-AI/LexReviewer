"""FastAPI backend for LexReviewerMCP document chat API.

Exposes endpoints for uploading documents, chatting over documents, and
managing the underlying vector store and chat history.
"""

import asyncio
import traceback
from typing import List
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn

from services.EmbeddingIndexer import EmbeddingIndexer
from services.chat_service import ChatService
from services.RAGIngestPipeline import RAGIngestPipeline
from DocumentReviewer import DocumentReviewer
from observation.provider import ObservationProvider
from models import (
    AskQuestionRequest,
    EditQuestionRequest,
    HistoryResponse,
    DocumentUploadRequest,
    ChatEntry,
)

class ChatController:
    """Owns the FastAPI app instance and wires routes to underlying services."""

    def __init__(self):
        # Single FastAPI application used by the Streamlit UI and any other clients.
        self.app = FastAPI(title="Document Chat API", description="API for chatting with multiple documents")
        self.configure_cors()
        self.register_routes()

        # Initialize observation/telemetry provider (e.g., Sentry, Langfuse).
        self.observation_provider = ObservationProvider()

        # Core domain services: ingestion, chat, vector index management and review.
        self.rag_ingest_pipeline = RAGIngestPipeline()
        self.chat_service = ChatService()
        self.embedding_indexer = EmbeddingIndexer()
        self.document_reviewer = DocumentReviewer()

    def configure_cors(self):
        """Configure CORS so the frontend (Streamlit) can call this API."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allows only backend origins
            allow_credentials=True,
            allow_methods=["GET","POST", "DELETE", "OPTIONS"],  # Allows these methods
            allow_headers=["*"],  # Allows all headers
        )

    def register_routes(self):
        """Register all HTTP routes for document upload, chat, and history."""
        self.app.post("/upload-documents", status_code=201)(self.upload_documents)
        self.app.post("/collection-exists")(self.collection_exists)
        self.app.post("/ask")(self.ask)
        self.app.post("/save-message-in-history")(self.save_message_in_history)
        self.app.post("/revert-history")(self.revert_history)
        self.app.delete("/delete-vector")(self.delete_from_db)
        self.app.delete("/clear-history")(self.clear_history)
        self.app.get("/get-history", response_model=HistoryResponse)(self.get_history)

    async def upload_documents(self, request: DocumentUploadRequest, document_id: str = Header(...)):
        """Upload and index a new document collection if it does not already exist."""
        base64_file = request.file
        
        if not base64_file:
            raise HTTPException(status_code=400, detail="No Document file provided")

        try:
            await self.rag_ingest_pipeline.ingest_document_if_new(document_id, base64_file)
            return "Documents processed successfully"
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error processing Documents: {str(e)}")

    async def ask(self, question_request: AskQuestionRequest, request: Request, document_id: str = Header(...), user_id: str = Header(...), username: str = Header(...)):
        """Stream an answer to a user question over the specified document."""
        try:
            generator = self.document_reviewer.get_streaming_response(question_request, document_id, user_id, username, request)

            return StreamingResponse(
                generator,
                media_type="application/x-ndjson"
            )
        
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

    async def save_message_in_history(self, save_message_request: ChatEntry, document_id: str = Header(...), user_id: str = Header(...)):
        """Persist a single chat turn in the conversation history."""
        try:
            await self.chat_service.save_chat_message(document_id, user_id, save_message_request)
            return "Conversation saved successfully"
        
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

    async def revert_history(self, new_question_request: EditQuestionRequest, document_id: str = Header(...), user_id: str = Header(...)):
        """Edit the last user question by reverting history to a given index."""
        try:
            await self.chat_service.revert_history(document_id, user_id, new_question_request.index)
            return "Conversation history updated successfully"
        
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error editing question: {str(e)}")

    async def delete_from_db(self, document_id: str = Header(...), user_id: str = Header(...)):
        """Delete all vector data and chat history associated with a document."""
        # Delete the vector store
        await self.embedding_indexer.delete_document_data(document_id)
        await self.clear_history(document_id, user_id)
        return "Database has been cleared for the document_id: " + document_id

    async def clear_history(self, document_id: str = Header(...), user_id: str = Header(...)):
        """Clear only the chat history for a given document/user pair."""
        await self.chat_service.clear_chat_history(document_id, user_id)
        
        return "Conversation history cleared successfully"

    async def get_history(self, document_id: str = Header(...), user_id: str = Header(...)):
        """Return the formatted conversation history for the UI."""
        formatted_history = await self.chat_service.get_history(document_id, user_id)
        return HistoryResponse(chatHistory=formatted_history)
    
    async def collection_exists(self, document_ids: List[str] = Header(...)):
        """Check which of the provided document IDs already have indexed data."""
        tasks = [self.embedding_indexer.document_data_exists(cid) for cid in document_ids]
        result = await asyncio.gather(*tasks)
        return result

def create_app():
    controller = ChatController()
    return controller.app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)