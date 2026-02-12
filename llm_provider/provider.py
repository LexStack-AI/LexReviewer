"""Abstraction layer over concrete LLM providers (currently OpenAI)."""

from typing import Any, Callable

from langchain_core.messages import AIMessage
from pydantic import BaseModel

from llm_provider.OpenAI.openai import OpenAIProvider


class LlmProvider:
    """Convenience wrapper that exposes a stable interface for agent code."""

    def __init__(self):
        self.llm_provider = OpenAIProvider()
        
    def get_chat_history_summary_model(self):
        return self.llm_provider.get_chat_history_summary_model()

    def get_chunk_summary_model(self):
        return self.llm_provider.get_chunk_summary_model()

    def get_embedding_model(self):
        return self.llm_provider.get_embedding_model()

    def get_required_tools_generator_model(self, output_type: BaseModel):
        return self.llm_provider.get_required_tools_generator_model(output_type)

    def get_agent_model(self, reasoning: bool):
        return self.llm_provider.get_agent_model(reasoning)

    def extract_text_from_chunk(self, chunk: Any) -> str:
        return self.llm_provider.extract_text_from_chunk(chunk)
    
    def extract_text_from_response(self, response: AIMessage) -> str:
        return self.llm_provider.extract_text_from_response(response)

    def process_reasoning_from_event_data(self, chunk: Any, writer: Callable) -> None:
        return self.llm_provider.process_reasoning_from_event_data(chunk, writer)