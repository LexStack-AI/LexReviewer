"""Summarize individual document chunks using an LLM, with Langfuse tracing."""

import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langfuse import get_client
from langfuse.langchain import CallbackHandler

from llm_provider.provider import LlmProvider


class ChunkSummarizer:
    """Builds a reusable chain that converts raw chunks into concise summaries."""

    def __init__(self):
        try:
            # Directory of the current script
            script_dir = os.path.dirname(os.path.abspath(__file__))

            # Path to the text file one level up that defines the summarization prompt.
            file_path = os.path.abspath(os.path.join(script_dir, "..", "prompts", "chunk_summarizer_context.txt"))

            # Convert to absolute path
            file_path = os.path.abspath(file_path)
            with open(file_path, "r", encoding="utf-8") as file:
                prompt_text = file.read()
                
            summarization_prompt = ChatPromptTemplate.from_template(prompt_text)

            llm_provider = LlmProvider()
            model = llm_provider.get_chunk_summary_model()
            self.summarize_chain = (
                RunnableLambda(lambda chunk: {"chunk": chunk})
                | summarization_prompt
                | model
                | StrOutputParser()
            )
        except FileNotFoundError:
            print("Error: chunk_summarizer_context.txt file not found.")
            self.summarize_chain = None
            raise RuntimeError("Error: chunk_summarizer_context.txt file not found.")
        except Exception as e:
            print(f"Error inititating ChunkSummarizer: {e}")
            self.summarize_chain = None
            raise RuntimeError(f"Error inititating ChunkSummarizer: {e}")
        
    async def summarize(self, chunks, document_id):
        lf = get_client()
        handler = CallbackHandler()  # one handler reused for the whole batch

        try:
            with lf.start_as_current_span(name="document_chunks_summary_batch") as root:
                # set trace-level attributes on the root span's trace
                root.update_trace(
                    tags=["chunk summarization", f"document:{document_id}"],
                    metadata={"document_id": str(document_id), "num_chunks": len(chunks)},
                )

                config = {
                    "callbacks": [handler],
                    "metadata": {
                        "langfuse_tags": ["chunk summarization"]
                    }
                }
                
                results = await self.summarize_chain.abatch(chunks, config=config)

            # ensure telemetry is sent in short-lived workers
            lf.flush()
            return results

        except Exception as e:
            print(f"Error during chunk summarization: {e}")
            lf.flush()
            return ["" for _ in chunks]
