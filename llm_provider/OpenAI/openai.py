"""LLM and embedding provider implementation backed by OpenAI models."""

import asyncio
import json
import os
from typing import Any, Callable, Dict, List

from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI
from pydantic import BaseModel


class OpenAIProvider:
    """Factory for chat, embedding and reasoning models configured via env vars."""

    def __init__(self):
        load_dotenv()
        # We rely entirely on environment variables so deployment remains 12-factor.
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        
        self.openai_client = OpenAI(api_key=self.openai_api_key)

    def get_chat_history_summary_model(self):
        """Model used to summarize long chat histories into short context."""
        return ChatOpenAI(model=os.getenv("OPENAI_CHAT_SUMMARY_MODEL", "gpt-4.1-mini"), temperature=int(os.getenv("OPENAI_CHAT_SUMMARY_MODEL_TEMPRETURE", 0.5)))

    def get_chunk_summary_model(self):
        """Model used to summarize individual document chunks."""
        return ChatOpenAI(model=os.getenv("OPENAI_CHUNK_SUMMARY_MODEL", "gpt-4.1-mini"), temperature=int(os.getenv("OPENAI_CHUNK_SUMMARY_MODEL_TEMPRETURE", 0.5)))

    def get_required_tools_generator_model(self, output_type: BaseModel):
        """Model that predicts which tools are needed, with structured output."""
        return ChatOpenAI(
            model=os.getenv("REQUIRED_TOOLS_GENERATOR_MODEL", "gpt-4.1-mini"),
        ).with_structured_output(output_type)

    def get_agent_model(self, reasoning: bool):
        """Return the main agent model, optionally enabling reasoning traces."""
        if reasoning:
            return ChatOpenAI(
                model=os.getenv("REASONING_AGENT_MODEL", "gpt-5.2"),
                use_responses_api=True,
                reasoning={"effort": "high", "summary": "auto"},
            )
        else:
            return ChatOpenAI(
                model=os.getenv("AGENT_MODEL", "gpt-4")
            )

    def get_embedding_model(self):
        """Embedding model used for indexing and retrieval."""
        embedding_model_name=os.getenv("OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large")
        return OpenAIEmbeddings(model=embedding_model_name)

    def extract_text_from_chunk(self, chunk: Any) -> str:
        """Extract plain text from stream chunk content (handles many formats)."""
        content = getattr(chunk, "content", "")
        
        if isinstance(content, str):
            return content
        
        if isinstance(content, list):
            # OpenAI responses API may return [{"type":"text","text": "..."} , ...]
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_value = part.get("text")
                    if isinstance(text_value, str):
                        parts.append(text_value)
            return "".join(parts)
        
        return ""

    def extract_text_from_response(self, response: AIMessage) -> str:
        """Extract final text content from a completed AIMessage."""
        content = response.content
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            # Join only text parts to avoid structured payloads
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_value = part.get("text")
                    if isinstance(text_value, str):
                        text_parts.append(text_value)
            return "".join(text_parts)

        return str(content)

    def process_reasoning_from_event_data(self, chunk: Any, writer: Callable) -> None:
        """Extract reasoning traces from streaming events and forward to client.

        The OpenAI Responses API can emit structured "reasoning" content; we
        normalize that into simple `{"thought": ...}` JSON lines that the
        frontend understands and renders in a dedicated panel.
        """
        content = getattr(chunk, "content", [])
        
        if not isinstance(content, list) or len(content) == 0:
            return

        for content_item in content:
            if not isinstance(content_item, dict):
                continue

            type = content_item.get("type", "")
            if type != "reasoning":
                continue

            summary = content_item.get("summary", [])
            if not isinstance(summary, list) or len(summary) == 0:
                continue

            for summary_item in summary:
                if not isinstance(summary_item, dict):
                    continue

                text = summary_item.get("text", "")
                if not text:
                    continue

                # Stream reasoning chunk immediately
                writer(json.dumps({"thought": text}) + "\n")