from typing import Any, Dict, Tuple

from agent_graph.tools import document_retriever, linked_documents
from services.EmbeddingIndexer import EmbeddingIndexer

class ToolExecutor:
    """Executes external tools and returns content/messages plus metadata for state."""

    def __init__(self, embedding_indexer: EmbeddingIndexer):
        self.embedding_indexer = embedding_indexer

    async def run_document_retriever(
        self, state, tool_arguments: Dict[str, Any], writer=None
    ) -> Tuple[str, Dict[str, Any]]:
        """Execute document retriever tool."""
        return await document_retriever.run_document_retriever(
            state=state,
            tool_arguments=tool_arguments,
            embedding_indexer=self.embedding_indexer,
            writer=writer,
        )

    async def run_linked_documents(
        self, state, tool_arguments: Dict[str, Any], writer=None
    ) -> Tuple[str, Dict[str, Any]]:
        """Execute linked documents retriever tool."""
        return await linked_documents.run_linked_documents(
            state=state, tool_arguments=tool_arguments, writer=writer
        )