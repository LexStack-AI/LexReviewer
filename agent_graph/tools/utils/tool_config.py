"""
Central configuration file for all tool definitions.
This file contains all tool specifications that can be easily maintained and updated.
"""

from typing import Any, Dict, List, Tuple

from models import ToolDefinition, ToolInputSpec, ToolName, ToolOutputSpec

class ToolConfig:
    def __init__(self):
        self.tool_configurations = {
            ToolName.retriever: {
                "display_name": "Document Retriever",
                "description": "Retrieves relevant chunks from the specified target document (primary or any linked document) by matching the semantic meaning of a focused query.",
                "goal_instructions": "Always set document_id to the document you intend to query (primary or a specific linked document). Use a targeted semantic query that clearly expresses one concept; if more are needed, call the tool multiple times.",
                "when_to_use": [
                    "When you need to retrieve information from a document",
                    "When you need to retrieve information from the primary document or from a known linked document (pass that linked document's document_id).",
                    "When previous retrieval attempts failed or returned insufficient results",
                    "When you need to retry with different, focused queries",
                ],
                "usage_guidelines": (
                    "\n**Usage Guidelines for Document Retriever:**\n"
                    "- Always specify the document_id parameter (use the primary document_id or a linked document's ID)\n"
                    "- Use focused, semantic queries in retriever_prompt - one concept per call\n"
                    "- For multiple concepts, make separate tool calls\n"
                    "- The tool returns chunks with chunk_number, text, chunk_id, and document_id\n"
                    "- Cite retrieved chunks using their chunk_number in superscript format"
                ),
                "input_specs": [
                    {
                        "name": "retriever_prompt",
                        "type": "str",
                        "required": True,
                        "description": "A targeted query that semantically matches the type of chunk you want to retrieve. Keep it minimal and focused. For additional concepts, call this tool multiple times with separate queries."
                    },
                    {
                        "name": "document_id",
                        "type": "str",
                        "required": True,
                        "description": "The ID of the document to retrieve chunks from."
                    }
                ],
                "output_specs": [
                    {
                        "name": "retrieved_chunks",
                        "type": "list",
                        "description": "A list of retrieved document chunks. Each chunk contains chunk_id (unique identifier), chunk_number (for citation), document_id (source document), and text (chunk content). Use chunk_number for citations in superscript format."
                    }
                ]
            },
            ToolName.linked_documents_retriever: {
                "display_name": "Linked Documents Retriever",
                "description": "Retrieves relevant documents that are linked to the primary document",
                "input_specs": [],
                "goal_instructions": "",
                "when_to_use": ["""
                    Always allow agent to use this tool when retriever tool is used or when the query or retrieved chunks mentions related documents, amendments, schedules, or cross-references.
                    When the primary document is a dependent type (you MUST also fetch the base/master and any prior amendments): 
                    • SOW / Work Order / PO / Order Form / Change Order / Variation Order → fetch the MSA / Framework Agreement / Master Subscription Agreement / Prime/Head Agreement.
                    • Amendment / Addendum / Supplement / Rider / Side Letter → fetch the amended base agreement AND earlier amendments referenced.
                    • Schedule / Exhibit / Appendix / Annexure / Attachment → fetch the parent agreement referenced.
                    • DPA / SLA or other policy schedules → fetch the governing MSA or subscription/master agreement.
                    When the user query OR any retrieved chunk refers to another document.
                    Mentions of linked doc types: Annex/Annexure, Appendix, Schedule, Exhibit, Attachment, Addendum, Amendment, Rider, Supplementary, Side Letter, Order Form/PO, SOW/Scope of Work, Work/Change Order, DPA, SLA, BAA, Policy/Terms.
                    Cross-reference phrases: 'see', 'refer to', 'as per', 'subject to', 'pursuant to', 'read with', 'incorporated by reference', 'attached hereto', 'referenced herein', 'per Section/Clause X of …'.
                    When the primary document is a framework (MSA/NDA) and details typically live in SOWs/Order Forms/Annexures/Amendments.
                    When a clause is replaced/overridden/updated by another document or the user asks to compare terms across documents.
                """
                ],
                "usage_guidelines": (
                    "\n**Usage Guidelines for Linked Documents Retriever:**\n"
                    "- Call this tool first if the query mentions related documents, amendments, schedules, or cross-references\n"
                    "- This tool retrieves metadata about linked documents (summaries and extracts)\n"
                    "- After retrieving linked documents, use the Document Retriever with specific linked document IDs to get their content\n"
                    "- Check for document dependencies (e.g., SOWs need MSAs, Amendments need base agreements)"
                ),
                "output_specs": [
                    {
                        "name": "linked_documents",
                        "type": "list",
                        "description": "A list of linked documents with their metadata including documentId, summary, and extractsData (key-value pairs of document information). Use these document IDs with the Document Retriever tool to get detailed content from linked documents."
                    }
                ]
            }
        }
        self.tool_definitions = self.build_tool_definitions()
        self.supported_tools = list(self.tool_definitions.keys())

    def build_tool_definition_without_input_specs(self) -> Dict[ToolName, ToolDefinition]:
        """Build tool definitions from configuration without input specs"""
        tool_definitions = {}
        
        for tool_name, config in self.tool_configurations.items():
            tool_definitions[tool_name] = ToolDefinition(
                name=tool_name,
                display_name=config["display_name"],
                description=config["description"],
                goal_instructions=config["goal_instructions"],
                when_to_use=config["when_to_use"],
                usage_guidelines=config.get("usage_guidelines", ""),
                input_specs=[],
                output_specs=[]
            )
        
        return tool_definitions


    def build_tool_definitions(self) -> Dict[ToolName, ToolDefinition]:
        """Build tool definitions from configuration"""
        tool_definitions = {}
        
        for tool_name, config in self.tool_configurations.items():
            # Convert input specs from dict to ToolInputSpec objects
            input_specs = []
            for spec_config in config["input_specs"]:
                input_specs.append(ToolInputSpec(
                    name=spec_config["name"],
                    type=spec_config["type"],
                    required=spec_config["required"],
                    description=spec_config["description"],
                    default=spec_config.get("default", None),
                    item_type=spec_config.get("item_type", None)
                ))

            output_specs = []
            for spec_config in config["output_specs"]:
                output_specs.append(ToolOutputSpec(
                    name=spec_config["name"],
                    type=spec_config["type"],
                    description=spec_config["description"],
                ))
            
            # Create tool definition
            tool_definitions[tool_name] = ToolDefinition(
                name=tool_name,
                display_name=config.get("display_name", tool_name.value.replace("_", " ").title()),
                description=config["description"],
                input_specs=input_specs,
                output_specs=output_specs,
                goal_instructions=config["goal_instructions"],
                when_to_use=config["when_to_use"],
                usage_guidelines=config.get("usage_guidelines", ""),
            )
        
        return tool_definitions

    def build_single_tool_schema(
        self, tool_name: ToolName, tool_def: Any
    ) -> Dict[str, Any]:
        """Build JSON schema for a single tool."""
        properties, required = self.build_tool_properties(tool_def)
        description = self.build_tool_description(tool_def)

        return {
            "name": tool_name.value,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def build_tool_properties(
        self, tool_def: Any
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Build properties and required fields for a tool schema."""
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for input_spec in tool_def.input_specs:
            json_type = self.map_type_to_json_schema(input_spec.type)
            prop: Dict[str, Any] = {
                "type": json_type,
                "description": input_spec.description,
            }
            # For array types, add items property (required by JSON Schema)
            if json_type == "array":
                # Use item_type if specified, otherwise default to "object" for backward compatibility
                item_type = input_spec.item_type or "object"
                prop["items"] = {"type": self.map_type_to_json_schema(item_type)}
            if input_spec.default is not None:
                prop["default"] = input_spec.default
            properties[input_spec.name] = prop
            if input_spec.required:
                required.append(input_spec.name)

        return properties, required

    def build_tool_description(self, tool_def: Any) -> str:
        """Build description string for a tool from its definition."""
        description_lines = [tool_def.description]
        
        if tool_def.goal_instructions:
            description_lines.append(f"Goal: {tool_def.goal_instructions}")
        
        if tool_def.when_to_use:
            when_to_use = "; ".join(tool_def.when_to_use)
            description_lines.append(f"Use when: {when_to_use}")

        return "\n".join(description_lines)

    def map_type_to_json_schema(self, type_name: str) -> str:
        mapping = {
            "str": "string",
            "string": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
        }
        return mapping.get(type_name.lower(), "string")

    def format_available_tools(self) -> str:
        """Format available tools as a bulleted list."""
        return "\n".join(
            f"- {self.tool_definitions[t].display_name} ({t.value})"
            for t in self.supported_tools
            if t in self.tool_definitions
        )