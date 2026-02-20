import logging
import os

from dotenv import load_dotenv

from agent_graph.tools.utils.tool_config import ToolConfig
from models import AgentState, ToolName

logger = logging.getLogger(__name__)

class AgentPromptGeneratorNode:
    def __init__(self):
        load_dotenv()
        self.chatbot_name = os.getenv("CHATBOT_NAME", "LexReviewer")
        self.tool_config = ToolConfig()

    async def run(self, state: AgentState) -> AgentState:
        """Generate the prompt for the document agent based on required tools."""
        required_tools = state.get("required_tools", [])
        
        base_prompt = self._build_base_prompt()
        tool_context = self._build_tool_context(required_tools)
        
        # Build the complete agent prompt
        agent_prompt = self._build_agent_prompt(
            base_prompt=base_prompt,
            tool_context=tool_context,
            document_id=state["document_id"]
        )
        
        state["agent_prompt"] = agent_prompt
        return state

    def _load_legal_answer_prompt(self) -> str:
        fallback = (
            f"You are {self.chatbot_name}, an AI legal assistant trained to behave like a seasoned attorney. "
            "Provide concise, citation-rich answers grounded in retrieved document evidence."
        )

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, "..", "..", "prompts", "legal_answer_prompt.txt")

            with open(os.path.abspath(file_path), "r", encoding="utf-8") as file:
                content = file.read()
        except Exception:
            content = ""

        return content + "\n\n" + fallback

    def _build_tool_context(self, required_tools: list) -> str:
        """Build tool usage context for the required tools only."""
        if not required_tools:
            return "No tools are available for this query."
        
        tool_contexts = []
        tool_definitions = self.tool_config.tool_definitions
        
        for tool_name_str in required_tools:
            try:
                tool_name = ToolName(tool_name_str)
            except ValueError:
                logger.error(f"Invalid tool name: {tool_name_str}")
                continue
            
            tool_def = tool_definitions.get(tool_name)
            if not tool_def:
                logger.error(f"Tool definition not found for tool name: {tool_name}")
                continue

            # Use model_dump_json() to get JSON string representation
            tool_contexts.append(tool_def.model_dump_json(indent=2))
        
        if not tool_contexts:
            return "No valid tools found in required tools list."
        
        return "\n\n".join(tool_contexts)

    def _build_base_prompt(self) -> str:
        # Start of base prompt
        base_prompt = f"""
            You are {self.chatbot_name}, an AI legal assistant trained to behave like a top-tier attorney with over 30 years of experience.

            TONE & BRANDING:
            - Always use a professional, authoritative tone
            - Write in legal English language — no casual or friendly tone
            - Mention “{self.chatbot_name}” branding subtly, only once per response (e.g., “As part of {self.chatbot_name}'s commitment to legal precision…”)

            """ 
        base_prompt += self._load_legal_answer_prompt()
        return base_prompt

    def _build_agent_prompt(
        self, 
        base_prompt: str, 
        tool_context: str,
        document_id: str
    ) -> str:
        """Build the complete agent prompt."""
        prompt = f"""{base_prompt}
        
            ## Document Context:
            Primary Document ID: {document_id}

            ## Available Tools:
            You can call tools when needed. Prefer precise citations and always ground answers in retrieved text.

            {tool_context}

            ## Tool Usage Reminders:
            - Always cite retrieved chunks using their chunk_number in superscript format if you are generating answer yourself, not using the tools.
            - When using multiple tools, coordinate their usage (e.g., retrieve linked documents first, then query their content)
            - Ground all answers in retrieved evidence from the tools
            - Use tool-friendly display names when explaining your reasoning. Do not use the tool name in the reasoning, only the tool display name.
            """
        return prompt