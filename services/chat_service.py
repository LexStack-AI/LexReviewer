"""Service for persisting, reading, and editing chat histories."""

from datetime import datetime, timezone
from http.client import HTTPException

from langchain_classic.schema import AIMessage, HumanMessage

from models import ChatEntry
from storage.provider import Storage


class ChatService:
    """High-level wrapper around storage for chat history operations."""

    def __init__(self):
        self.storage = Storage()

    async def save_chat_message(self, document_id: str, user_id: str, chat_entry: ChatEntry):
        """Append a single user/assistant turn to the chat history."""
        try:
            question = chat_entry.question
            answer = chat_entry.answer
            reference_positions = chat_entry.reference_positions
            thoughts = chat_entry.thoughts

            # We key history by (user, document) to support multiple users per doc.
            unique_id = f"{user_id}_{document_id}"
            chat_history = self.storage.get_chat_history(unique_id)
            
            current_time = datetime.now(timezone.utc).isoformat()
            # Persist the user message with an ISO timestamp for later edits.
            chat_history.add_message(
                HumanMessage(
                    content=question,
                    additional_kwargs={
                        "metadata": {
                            "timestamp": current_time
                        }
                    },
                )
            )

            # Persist the assistant message, including references and thoughts.
            chat_history.add_message(
                AIMessage(
                    content=answer,
                    additional_kwargs={
                        "metadata": {
                            "reference_positions": reference_positions,
                            "timestamp": current_time,
                            "thoughts": thoughts,
                        }
                    }
                )
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving chat in chat history: {str(e)}")
     
    async def clear_chat_history(self, document_id, user_id):
        """Delete all stored messages for a given (user, document) pair."""
        try:
            unique_id = f"{user_id}_{document_id}"
            chat_history = self.storage.get_chat_history(unique_id)
            
            # Clear chat history in the underlying Mongo-backed store.
            await chat_history.aclear()
            return {"message": f"Chat history for document {document_id} and user {user_id} cleared successfully."}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error clearing chat history: {str(e)}")
        
    async def get_history(self, document_id: str, user_id: str):
        """Return chat history in the flattened format expected by the UI."""
        try:
            # Directly access MongoDB chat history and flatten into QA pairs.
            unique_id = f"{user_id}_{document_id}"
            chat_history = self.storage.get_chat_history(unique_id)

            history = chat_history.messages
            formatted_history = []
            for i in range(0, len(history) - 1, 2):
                if isinstance(history[i], HumanMessage) and isinstance(history[i + 1], AIMessage):
                    question = history[i].content
                    ai_msg = history[i + 1]

                    metadata: dict = ai_msg.additional_kwargs.get("metadata", {})
                    reference_positions = metadata.get("reference_positions", [])
                    thoughts = metadata.get("thoughts", [])
                    entry = {
                        "question": question,
                        "answer": ai_msg.content,
                        "reference_positions": reference_positions,
                        "thoughts": thoughts,
                    }
                    formatted_history.append(entry)
            return formatted_history

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching chat history: {str(e)}")

    async def revert_history(self, document_id: str, user_id: str, message_index: int):
        """Truncate chat history so that a previous user question can be edited."""
        try:
            unique_id = f"{user_id}_{document_id}"
            chat_history = self.storage.get_chat_history(unique_id)
            
            messages = chat_history.messages
            if len(messages) < 2 or message_index * 2 >= len(messages):
                raise HTTPException(status_code=404, detail="Message not found")
            
            # Each QA pair is 2 messages in the raw list (Human, then AI).
            # Convert the logical message_index into an index into that list.
            actual_index = (message_index * 2)
            if not isinstance(messages[actual_index], HumanMessage):
                raise HTTPException(status_code=400, detail="Selected message is not a user message")
            
            # Parse the message we're editing to get its timestamp
            edit_message = messages[actual_index]
            metadata: dict = edit_message.additional_kwargs.get("metadata", {})
            edit_timestamp = metadata.get("timestamp", "")
            
            if not edit_timestamp:
                # fallback to old way to clearing history and readding messages
                await chat_history.aclear()
        
                # Re-add all messages up to the edited one (excluding the one being edited)
                for message in messages[:actual_index]:
                    chat_history.add_message(message)
                
                return
            
            if isinstance(edit_timestamp, str):
                edit_timestamp = datetime.fromisoformat(edit_timestamp)
            
            self.storage.revert_history(unique_id, edit_timestamp)
        except Exception as e:
            print(f"Error during message editing: {e}")