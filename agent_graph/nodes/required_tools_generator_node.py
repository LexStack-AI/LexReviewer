import json
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from llm_provider.provider import LlmProvider
from models import AgentState, ToolName
from agent_graph.tools.utils.tool_config import ToolConfig

class ToolListResponse(BaseModel):
    """Structured response containing only a list of tool names."""
    tool_names: List[str] = Field(
        description="List of tool names (exact enum values) that should be used to answer the user's query. Only include tools that are actually needed."
    )

class RequiredToolsGeneratorNode:
    def __init__(self):
        self.tool_config = ToolConfig()
        llm_provider = LlmProvider()
        self.llm = llm_provider.get_required_tools_generator_model(ToolListResponse)

    async def run(self, state: AgentState) -> AgentState:
        """Generate the required tools for the document agent. Returns a list of tool name strings."""
        user_query = state["query"]
        chat_history_summary = state.get("chat_history_summary", "")      
        system_context = self._load_required_tools_generator_context(user_query, chat_history_summary)

        messages = [
            SystemMessage(content=system_context),
            HumanMessage(content="Analyze the user's query and context, then return ONLY a JSON object with a 'tool_names' array containing the exact tool name enum values (e.g., 'retriever', 'linked_documents_retriever', etc') that are needed to answer the query. Do not include any explanation, reasoning, or additional text - only the structured JSON response.")
        ]

        response: ToolListResponse = await self.llm.ainvoke(messages)
        # Extract tool names from structured response
        tool_names = response.tool_names if hasattr(response, 'tool_names') else []
        state["required_tools"] = tool_names
        return state

    def _load_required_tools_generator_context(self, user_query: str, chat_history_summary: str = "") -> str:
        """Load the required tools generator context with detailed tool information."""
        tool_definitions = self.tool_config.build_tool_definition_without_input_specs()
        available_tool_names = [tool.value for tool in ToolName]
        
        # Build tool definitions JSON directly from Pydantic models
        tool_definitions_json = {
            tool_name.value: tool_def.model_dump(exclude={"input_specs", "output_specs"})
            for tool_name, tool_def in tool_definitions.items()
        }
        
        # Build chat history context section
        chat_history_section = ""
        if chat_history_summary:
            chat_history_section = f"""
                ## Previous Conversation Summary:
                {chat_history_summary}
                
                This summary provides context about previous interactions. Consider this when determining which tools are needed, especially if the current query references or builds upon previous conversations.
            """
        
        context = f"""You are an expert tool selection assistant for a document analysis agent. Your task is to analyze the user's query and determine which tools are necessary to answer it effectively.

            ## Available Tools:
            {json.dumps(tool_definitions_json, indent=2, default=str)}

            ## Available Tool Names (use exact values):
            {json.dumps(available_tool_names, indent=2)}

            ## User Context:
            - User Query: "{user_query}"
            
            {chat_history_section}

            ## Analysis Guidelines:

            Carefully review the "Available Tools" section above, which contains detailed information about each tool including:
            - Description: What the tool does
            - When to Use: Specific scenarios and conditions for using each tool
            - Goal Instructions: How to effectively use the tool

            Use this information to determine which tools are necessary based on:
            - The user's query content and intent (PRIMARY factor - what is the user actually asking for?)
            - The previous conversation summary (if provided) to understand context and continuity
            - The specific requirements mentioned in each tool's "When to Use" criteria
            - The relationship between the query and the tool's purpose as described in the tool definitions

            Be selective and only include tools that are actually needed to answer the query effectively.

            ## Response Format:
            You MUST return a JSON object with the following structure:
            {{
                "tool_names": ["tool_name_1", "tool_name_2", ...]
            }}

            CRITICAL REQUIREMENTS:
            - Return ONLY the JSON object, no additional text, explanations, or markdown formatting
            - Use ONLY the exact tool name enum values from the available tool names list above
            - Include only tools that are actually necessary for answering the query
            - Be selective - do not include tools that are not needed
            - The response must be valid JSON that can be parsed directly

            ## Examples:

            Query: "Generate a summary comparing the main document and amendments"
            Response: {{"tool_names": ["linked_documents_retriever", "retriever"]}}

            Query: "Generate a summary highlighting risks of the document"
            Response: {{"tool_names": ["retriever"]}}
            """
        return context
