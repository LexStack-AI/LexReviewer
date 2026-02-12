import json
from typing import AsyncGenerator

from fastapi import Request
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from models import AgentState
from agent_graph.nodes.agent_node import AgentNode
from agent_graph.nodes.agent_prompt_generator_node import (
    AgentPromptGeneratorNode,
)
from agent_graph.nodes.required_tools_generator_node import RequiredToolsGeneratorNode
from models import AskQuestionRequest
from observation.provider import ObservationProvider
from services.ChatHistorySummarizer import ChatHistorySummarizer
from storage.provider import Storage

class DocumentReviewer:
    def __init__(self):
        self.chat_history_summarizer = ChatHistorySummarizer()
        self.storage_client = Storage()
        self.obversation_handler = ObservationProvider()

        self.agent_node = AgentNode()
        self.agent_prompt_generator = AgentPromptGeneratorNode()
        self.required_tools_generator = RequiredToolsGeneratorNode()
        self.graph = self._build_graph()

    def _build_graph(self) -> CompiledStateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        workflow.add_node("required_tools_generator", self.required_tools_generator.run)
        workflow.add_node("agent", self.agent_node.run)
        workflow.add_node("agent_prompt_generator", self.agent_prompt_generator.run)
        
        workflow.set_entry_point("required_tools_generator")
        workflow.add_edge("required_tools_generator", "agent_prompt_generator")
        workflow.add_edge("agent_prompt_generator", "agent")
        workflow.add_edge("agent", END)
        return workflow.compile()

    async def get_streaming_response(
        self, 
        question_request: AskQuestionRequest,
        document_id: str,
        user_id: str,
        username: str,
        request: Request,
    ) -> AsyncGenerator[str, None]:
        """Main method to get streaming RAG response"""
        query = question_request.question

        # Setup chat history
        unique_id = f"{user_id}_{document_id}"
        chat_history = self.storage_client.get_chat_history(unique_id)

        chat_history_summary = await self.chat_history_summarizer.summarize_chat_history(chat_history.messages)
        
        # Initialize state
        initial_state = AgentState(
            document_id=document_id,
            query=query,
            chat_history=chat_history.messages,
            chat_history_summary=chat_history_summary,
            tool_states=[],
            messages=[],
            final_response="",
            required_tools=[],
            agent_prompt=""
        )

        try:
            config = self.obversation_handler.get_config(user_id, document_id, username, query)

            # Directly iterate over the async generator instead of wrapping in task
            async for chunk in self.graph.astream(initial_state, config=config, stream_mode="custom"):
                if await request.is_disconnected():
                    return
                yield chunk
                        
        except Exception as e:
            print(f"Error in streaming: {e}")
            yield json.dumps({'error': f'[ERROR] {str(e)}'}) + "\n"