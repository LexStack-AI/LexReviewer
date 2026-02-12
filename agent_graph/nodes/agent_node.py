"""Core LangGraph node that powers the document QA agent with tool calling."""

import json
import os
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.config import get_stream_writer

from agent_graph.nodes.utils.tool_executor import ToolExecutor
from agent_graph.tools.utils.tool_config import ToolConfig
from llm_provider.provider import LlmProvider
from models import AgentState, ToolName
from services.EmbeddingIndexer import EmbeddingIndexer


class AgentNode:
    """Single LangGraph node that orchestrates tool-using reasoning over documents."""

    def __init__(self): 
        load_dotenv()

        # Shared dependencies that tools and the agent will use.
        self.embedding_indexer = EmbeddingIndexer()
        self.tool_config = ToolConfig()
        self.llm_provider = LlmProvider()

        # Toggle to enable/disable model-native reasoning traces without code changes.
        self.agent_reasoning_allowed= bool(os.getenv("AGENT_REASONING_ALLOWED", True))
        self.llm = self.llm_provider.get_agent_model(self.agent_reasoning_allowed)
        
        # Centralized tool executor (re-used across all tool invocations).
        self.tool_executor = ToolExecutor(
            embedding_indexer=self.embedding_indexer,
        )

    async def run(self, state: AgentState) -> AgentState:
        """Execute the document agent with tool-calling support."""
        writer = get_stream_writer()
        messages = self._build_initial_messages(state)
        tool_history = state.get("tool_states", [])
        # Only bind tools that are in the required_tools list
        tool_schemas = self._build_tool_schemas(state.get("required_tools", []))
        llm_with_tools = self.llm.bind_tools(tool_schemas)

        # Main agent loop: alternate between LLM calls and tool executions.
        while True:
            response = await self._process_llm_stream(
                llm_with_tools, messages, writer
            )
            
            if response is None:
                response = AIMessage(content="")
            
            tool_calls = getattr(response, "tool_calls", None) or []
            if tool_calls:
                messages = await self._handle_tool_calls(
                    response, tool_calls, messages, state, tool_history, writer
                )
                continue

            return self._finalize_response(state, response, tool_history, messages)

    async def _process_llm_stream(
        self, llm_with_tools, messages: List[BaseMessage], writer
    ) -> AIMessage | None:
        """Process streaming events from the LLM and extract reasoning + text."""
        streamed_text_parts: List[str] = []
        response: AIMessage | None = None
        done_sent = False

        async for event in llm_with_tools.astream_events(messages):
            if event.get("event") == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                # Forward any model-native reasoning content as "thought" events.
                if self.agent_reasoning_allowed:
                    self.llm_provider.process_reasoning_from_event_data(chunk, writer)
                text_piece = self.llm_provider.extract_text_from_chunk(chunk)
                
                if text_piece:
                    streamed_text_parts.append(text_piece)
                    if not done_sent:
                        # Signal end of reasoning phase; begin streaming response text.
                        writer(json.dumps({"thought": "Done"}) + "\n")
                        done_sent = True
                    writer(json.dumps({"chunk": text_piece}) + "\n")

            elif event.get("event") == "on_chat_model_end":
                output = event["data"]["output"]
                if isinstance(output, AIMessage):
                    response = output

        # Fallback: create response from streamed parts if not captured
        if response is None and streamed_text_parts:
            combined = "".join(streamed_text_parts)
            response = AIMessage(content=combined)

        return response

    async def _handle_tool_calls(
        self,
        response: AIMessage,
        tool_calls: List[Dict[str, Any]],
        messages: List[BaseMessage],
        state: AgentState,
        tool_history: List[Dict[str, Any]],
        writer,
    ) -> List[BaseMessage]:
        """Execute tool calls and append tool messages to conversation."""
        messages.append(response)

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_arguments = tool_call.get("args", {}) or {}

            tool_message_content, tool_state_entry = (
                await self._execute_tool(state, tool_name, tool_arguments, writer)
            )

            if tool_state_entry:
                tool_history.append(tool_state_entry)

            messages.append(
                ToolMessage(
                    content=tool_message_content,
                    name=tool_name,
                    tool_call_id=tool_call.get("id"),
                )
            )

        return messages

    def _finalize_response(
        self,
        state: AgentState,
        response: AIMessage,
        tool_history: List[Dict[str, Any]],
        messages: List[BaseMessage],
    ) -> AgentState:
        """Extract final text from response and update state."""
        final_text = self.llm_provider.extract_text_from_response(response)

        state["final_response"] = final_text
        state["tool_states"] = tool_history
        messages.append(response)
        state["messages"] = messages
        return state

    def _build_initial_messages(self, state: AgentState) -> List[BaseMessage]:
        """Build initial message list with system context and conversation history."""
        system_messages = self._build_system_messages(state)
        human_messages = self._build_human_messages(state)
        return system_messages + human_messages

    def _build_system_messages(self, state: AgentState) -> List[BaseMessage]:
        """Build system messages with context and tool information."""
        # Use the agent_prompt from state (generated by DocumentAgentPromptGeneratorNode)
        agent_prompt = state.get("agent_prompt", "")
        system_messages: List[BaseMessage] = [SystemMessage(content=agent_prompt)]

        if state.get("chat_history_summary"):
            system_messages.append(
                SystemMessage(
                    content=f"Conversation summary so far: {state['chat_history_summary']}"
                )
            )

        return system_messages

    def _build_tool_schemas(self, required_tools: list) -> List[Dict[str, Any]]:
        """Build tool schemas only for the required tools."""
        if not required_tools:
            return []
        
        tool_schemas = []
        for tool_name_str in required_tools:
            try:
                tool_name = ToolName(tool_name_str)
                tool_def = self.tool_config.tool_definitions.get(tool_name)
                if tool_def:
                    schema = self.tool_config.build_single_tool_schema(tool_name, tool_def)
                    tool_schemas.append(schema)
            except ValueError:
                # Skip invalid tool names
                continue
        
        return tool_schemas

    def _build_human_messages(self, state: AgentState) -> List[BaseMessage]:
        """Build human messages from chat history and current query."""
        human_messages: List[BaseMessage] = []
        human_messages.append(HumanMessage(content=f"User query: {state['query']}"))
        return human_messages

    async def _execute_tool(
        self,
        state: AgentState,
        tool_name: str,
        tool_arguments: Dict[str, Any],
        writer,
    ) -> Tuple[str, Dict[str, Any]]:
        try:
            tool_enum = ToolName(tool_name)
        except ValueError:
            message = f"Tool '{tool_name}' is not supported."
            return message, {}

        if tool_enum == ToolName.retriever:
            return await self.tool_executor.run_document_retriever(state, tool_arguments, writer)
        if tool_enum == ToolName.linked_documents_retriever:
            return await self.tool_executor.run_linked_documents(state, tool_arguments, writer)

        return f"Tool '{tool_name}' is registered but not implemented.", {}
