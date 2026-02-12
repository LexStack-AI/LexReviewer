import os

from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

class LangfuseObservation:
    def __init__(self) -> None:
        load_dotenv()
        required_env_vars = ["LANGFUSE_SECRET_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_HOST"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            pass

        Langfuse(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            host=os.getenv("LANGFUSE_HOST")
        )

    def get_languse_config(self, user_id: str, document_id: str, username: str, query: str):
        langfuse_handler = CallbackHandler()
        return {
            "recursion_limit": 20,
            "callbacks": [langfuse_handler],
            "metadata": {
                "langfuse_user_id": user_id,
                "langfuse_tags": ["user query", document_id, user_id, username]
            },
            "run_name": query
        }