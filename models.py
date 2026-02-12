"""Shared Pydantic and TypedDict models used across the backend and agent graph."""

from enum import Enum
from typing import List, Optional
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from pydantic import BaseModel
from pydantic import BaseModel
from typing_extensions import NotRequired
    
class EditQuestionRequest(BaseModel):
    index: int

class BoundingBox(BaseModel):
    leftPosition: float
    topPosition: float
    highlightWidth: float
    highlightHeight: float
    pageWidth: float
    pageHeight: float
    pageNumber: int

class ReferencePosition(BaseModel):
    chunk_id: str
    chunk_number: int
    document_id: str
    bounding_boxes: List[BoundingBox]

class ChatEntry(BaseModel):
    question: str
    answer: str
    thoughts: Optional[List[str]] = None
    reference_positions: List[ReferencePosition]

class HistoryResponse(BaseModel):
    chatHistory: List[ChatEntry]

class DocumentUploadRequest(BaseModel):
    file: str  # Base64-encoded file

class AskQuestionRequest(BaseModel):
    question: str

# Type definitions for retrieve contexts
class Chunk(BaseModel):
    text: str
    chunk_id: str
    chunk_number: int
    document_id: str

class ErrorChunk(BaseModel):
    error: str

class LinkedDocumentsResponse(BaseModel):
    documentIds: List[str]

class ToolName(str, Enum):
    retriever = "retriever"
    linked_documents_retriever = "linked_documents_retriever"

class Tool_State(TypedDict):
    tool_name: ToolName
    tool_input: Dict[str, Any]
    tool_result: NotRequired[Optional[Dict[str, Any]]]

class AgentState(TypedDict):
    document_id: str
    query: str
    chat_history: List[BaseMessage]
    chat_history_summary: str
    tool_states: List[Tool_State]
    messages: List[BaseMessage]
    final_response: str
    required_tools: List[ToolName]
    agent_prompt: str

class ToolInputSpec(BaseModel):
    """Specification for a tool input parameter"""
    name: str
    type: str
    required: bool
    description: str
    default: Any = None
    item_type: Optional[str] = None  # For array types, specifies the type of items (e.g., "str", "object")

class ToolOutputSpec(BaseModel):
    """Specification for a tool output parameter"""
    name: str
    type: str
    description: str

class ToolDefinition(BaseModel):
    """Complete tool definition with metadata"""
    name: ToolName
    display_name: str
    description: str
    input_specs: List[ToolInputSpec]
    output_specs: List[ToolOutputSpec]
    goal_instructions: str
    when_to_use: List[str]
    usage_guidelines: str = ""