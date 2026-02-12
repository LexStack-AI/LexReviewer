"""Linked documents retriever tool implementation."""
import os
from typing import Any, Callable, Dict, Optional, Tuple

import httpx

from models import ToolName, LinkedDocumentsResponse

async def run_linked_documents(
    state: Dict[str, Any], tool_arguments: Dict[str, Any], writer: Optional[Callable] = None
) -> Tuple[str, Dict[str, Any]]:
    """Retrieve linked documents for a given document ID."""
    document_id = tool_arguments.get("document_id") or state["document_id"]
    backend_url = os.getenv("LINKED_DOCUMENT_FETCH_URL", "")
    if not backend_url:
        message = "LINKED_DOCUMENT_FETCH_URL environment variable is not set. Unable to retrieve linked documents."
        tool_state = {
            "tool_name": ToolName.linked_documents_retriever,
            "tool_input": {"document_id": document_id},
            "tool_result": {"error": "Missing LINKED_DOCUMENT_FETCH_URL"},
        }
        return message, tool_state
    
    timeout = float(os.getenv("LINKED_DOCUMENT_TIMEOUT", "30"))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{backend_url}?documentId={document_id}")
            response.raise_for_status()
            linked_data_json = response.json()
    except Exception as exc:
        error_message = f"Linked document retrieval failed: {exc}"
        tool_state = {
            "tool_name": ToolName.linked_documents_retriever,
            "tool_input": {"document_id": document_id},
            "tool_result": {"error": str(exc)},
        }
        return error_message, tool_state

    linked_data = LinkedDocumentsResponse.model_validate(linked_data_json)
    linked_document_ids = linked_data.documentIds

    tool_state = {
        "tool_name": ToolName.linked_documents_retriever,
        "tool_input": {"document_id": document_id},
        "tool_result": {
            "linked_documents": linked_document_ids
        },
    }

    if not linked_document_ids:
        return "No linked documents were found.", tool_state

    tool_message_content = (
        f"Retrieved {len(linked_document_ids)} linked documents for primary document {document_id}:\n"
    )
    return tool_message_content, tool_state

