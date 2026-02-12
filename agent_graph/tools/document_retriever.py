"""Document retriever tool implementation."""
import json
from typing import Any, Callable, Dict, Optional, Tuple

from models import ToolName
from services.EmbeddingIndexer import EmbeddingIndexer
from vector_storage.provider import VectorStorageProvider

async def run_document_retriever(
    state: Dict[str, Any],
    tool_arguments: Dict[str, Any],
    embedding_indexer: EmbeddingIndexer,
    writer: Optional[Callable] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Retrieve document chunks using embedding search."""
    retriever_prompt = tool_arguments.get("retriever_prompt") or state["query"]
    document_id = tool_arguments.get("document_id") or state["document_id"]

    try:
        retriever = await embedding_indexer.get_retriever(document_id)
        results = await retriever.ainvoke(retriever_prompt)
    except Exception as exc:
        error_message = f"Retriever failed: {exc}"
        tool_state = {
            "tool_name": ToolName.retriever,
            "tool_input": {"retriever_prompt": retriever_prompt, "document_id": document_id},
            "tool_result": {"error": str(exc)},
        }
        return error_message, tool_state

    last_number = get_last_chunk_number(state)
    chunk_number = 1 if last_number < 0 else last_number + 1

    chunk_dicts = []
    messages_for_llm = []
    for idx, doc in enumerate(results):
        current_number = chunk_number + idx
        text = doc.page_content if hasattr(doc, "page_content") else str(doc)
        chunk_dicts.append(
            {
                "chunk_id": getattr(doc, "id", f"chunk-{idx}"),
                "chunk_number": current_number,
                "document_id": document_id,
                "text": text,
            }
        )
        messages_for_llm.append(
            f"[Chunk {current_number} | Document {document_id}] {text}"
        )

    vector_storage_client = VectorStorageProvider()
    reference_positions = await vector_storage_client.get_reference_positions(chunk_dicts, document_id)

    # Stream reference positions directly from the tool if writer is provided
    if reference_positions and writer:
        writer(json.dumps({"reference_positions": reference_positions}) + "\n")

    tool_state = {
        "tool_name": ToolName.retriever,
        "tool_input": {"retriever_prompt": retriever_prompt, "document_id": document_id},
        "tool_result": {"retrieved_chunks": chunk_dicts},
    }

    summary_header = (
        f"Retrieved {len(chunk_dicts)} chunks from document {document_id} "
        f"for prompt '{retriever_prompt}'."
    )
    tool_message_content = summary_header + "\n\n" + "\n\n".join(messages_for_llm)
    return tool_message_content.strip(), tool_state

def get_last_chunk_number(state: Dict[str, Any]) -> int:
    """Get the last chunk number from tool states."""
    last_number = -1
    for tool_state in state.get("tool_states", []):
        tool_result = tool_state.get("tool_result") if isinstance(tool_state, dict) else None
        if not tool_result:
            continue
        retrieved = tool_result.get("retrieved_chunks")
        if not retrieved:
            continue
        for chunk in retrieved:
            if isinstance(chunk, dict):
                num = chunk.get("chunk_number", -1)
            else:
                num = getattr(chunk, "chunk_number", -1)
            last_number = max(last_number, num)
    return last_number