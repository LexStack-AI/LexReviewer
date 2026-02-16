"""Thin HTTP client used by the Streamlit UI to talk to the FastAPI backend."""

from typing import Any, List
import requests
import json

# Base URL for the backend API. In production this can be configured/overridden.
BACKEND_URL = "http://localhost:8000"

def load_history(document_id, user_id):
    """Fetch previous chat turns for a given document/user pair."""
    headers = {"document-id": document_id, "user-id": user_id}
    r = requests.get(f"{BACKEND_URL}/get-history", headers=headers)
    r.raise_for_status()
    return r.json().get("chatHistory", [])

def save_message(document_id: str, user_id: str, question: str, answer: str, thoughts: List[str] | str | None, reference_positions: List[Any]):
    """Saves the chat message in history."""
    headers = {"document-id": document_id, "user-id": user_id}
    if isinstance(thoughts, str):
        thoughts = [thoughts]
    body = {
        "question": question,
        "answer": answer,
        "thoughts": thoughts,
        "reference_positions": reference_positions
    }
    r = requests.post(f"{BACKEND_URL}/save-message-in-history", headers=headers, json=body)
    r.raise_for_status()

def upload_document(document_id, b64_pdf):
    """Send a base64-encoded PDF to the backend for ingestion and indexing."""
    headers = {"document-id": document_id}
    payload = {"file": b64_pdf}
    r = requests.post(f"{BACKEND_URL}/upload-documents", headers=headers, json=payload, timeout=600)
    r.raise_for_status()


def clear_history(document_id, user_id):
    """Clear all stored chat history for the current document/user."""
    headers = {"document-id": document_id, "user-id": user_id}
    requests.delete(f"{BACKEND_URL}/clear-history", headers=headers)


def reset_vectors(document_id, user_id):
    """Delete vector index data and chat history for the current document."""
    headers = {"document-id": document_id, "user-id": user_id}
    requests.delete(f"{BACKEND_URL}/delete-vector", headers=headers)


def stream_answer(question, document_id, user_id, username):
    """Generator that yields incrementally streamed answer/thoughts from backend.

    The backend responds with newline-delimited JSON events; we accumulate the
    assistant answer, reasoning trace, and reference positions so the UI can
    render a progressively updating chat message.
    """
    headers = {
        "document-id": document_id,
        "user-id": user_id,
        "username": username,
        "Content-Type": "application/json",
    }

    payload = {"question": question}

    with requests.post(
        f"{BACKEND_URL}/ask",
        headers=headers,
        json=payload,
        stream=True,
    ) as r:

        r.raise_for_status()

        # We keep running aggregates instead of yielding raw deltas so that
        # the Streamlit UI can simply re-render the full text each tick.
        full_text = ""
        full_thoughts = ""
        references = []

        for line in r.iter_lines():
            if not line:
                continue

            try:
                event = json.loads(line.decode())
            except:
                # Ignore malformed lines instead of breaking the entire stream.
                continue

            # Answer token streaming from the agent.
            if "chunk" in event:
                chunk = event["chunk"]
                if isinstance(chunk, list):
                    chunk = "".join(chunk)
                full_text += chunk

            # ⭐ Accumulate intermediate "thinking" tokens into a single string.
            if "thought" in event:
                thought = event["thought"]
                if isinstance(thought, list):
                    thought = "".join(thought)
                full_thoughts += thought

            # Last seen reference positions (e.g., chunk/page indices).
            if "reference_positions" in event:
                references = event["reference_positions"]

            yield full_text, full_thoughts, references