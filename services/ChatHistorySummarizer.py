"""Utility for collapsing long chat histories into a short text summary."""

import os
from typing import List

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate

from llm_provider.provider import LlmProvider


class ChatHistorySummarizer:
    """Uses an LLM to summarize past messages into a compact conversation summary."""

    def __init__(self):
        load_dotenv()
        self.chatbot_name = os.getenv("CHATBOT_NAME", "SPANMIND")
        self.llm_provider = LlmProvider()
        self.chat_history_summary_model = self.llm_provider.get_chat_history_summary_model()
        self.chat_history_summary_prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                f"You are the Chat History Summarizer for {self.chatbot_name}'s document-chat agent. "
                "Summarize the conversation in plain language, capturing the user's questions and the assistant's answers. "
                "Do not include extra commentary or markdown."
            ),
            ("user", "{chat_history}")
        ])

    async def summarize_chat_history(self, chat_history: List[BaseMessage]) -> str:
        """Convert a list of chat messages into a single summary string."""
        if not chat_history:
            return ""

        # Flatten potentially structured message content into a plain-text transcript.
        history_text = []
        for message in chat_history:
            role = getattr(message, "type", "system")
            content = getattr(message, "content", "")
            if isinstance(content, list):
                content = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            history_text.append(f"{role.upper()}: {content}")

        summary_chain = self.chat_history_summary_prompt | self.chat_history_summary_model
        response = await summary_chain.ainvoke({"chat_history": "\n".join(history_text)})
        return response.content if response and getattr(response, "content", "") else ""