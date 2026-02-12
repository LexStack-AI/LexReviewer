import requests
import json

BACKEND_URL = "http://localhost:8000"

def load_history(document_id, user_id):
    headers = {"document-id": document_id, "user-id": user_id}
    r = requests.get(f"{BACKEND_URL}/get-history", headers=headers)
    r.raise_for_status()
    return r.json().get("chatHistory", [])

def upload_document(document_id, b64_pdf):
    headers = {"document-id": document_id}
    payload = {"file": b64_pdf}
    r = requests.post(f"{BACKEND_URL}/upload-documents", headers=headers, json=payload, timeout=600)
    r.raise_for_status()

def clear_history(document_id, user_id):
    headers = {"document-id": document_id, "user-id": user_id}
    requests.delete(f"{BACKEND_URL}/clear-history", headers=headers)

def reset_vectors(document_id, user_id):
    headers = {"document-id": document_id, "user-id": user_id}
    requests.delete(f"{BACKEND_URL}/delete-vector", headers=headers)

def stream_answer(question, document_id, user_id, username):
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

        full_text = ""
        full_thoughts = ""
        references = []

        for line in r.iter_lines():
            if not line:
                continue

            try:
                event = json.loads(line.decode())
            except:
                continue

            # answer streaming
            if "chunk" in event:
                chunk = event["chunk"]
                if isinstance(chunk, list):
                    chunk = "".join(chunk)
                full_text += chunk

            # ⭐ accumulate thought tokens into single sentence
            if "thought" in event:
                thought = event["thought"]
                if isinstance(thought, list):
                    thought = "".join(thought)
                full_thoughts += thought

            if "reference_positions" in event:
                references = event["reference_positions"]

            yield full_text, full_thoughts, references