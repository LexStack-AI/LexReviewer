## LexReviewerMCP – Legal Document Chat & RAG Service

LexReviewerMCP is a Python-based backend service that lets you **upload legal PDFs, index them into a retrieval-augmented generation (RAG) pipeline, and chat with those documents**. It focuses on **legal document understanding**, providing answers grounded in the source text, along with **reference positions / bounding boxes** that can be used for highlighting.  
It solves the problem of turning raw legal PDFs into an interactive, citation-aware chat experience, with support for chat history, document-linked retrieval, and observability hooks.  

Key features:

- **PDF ingestion and chunking** via Unstructured.io
- **Vector-based retrieval** backed by Qdrant, plus BM25 keyword search
- **RAG chat endpoint** with streaming responses (NDJSON), including thoughts and references
- **Chat history management** stored in MongoDB
- **Linked document retrieval** through an external HTTP tool
- **Observability integration** via Langfuse and optional Sentry

---

## Tech Stack

### Languages

- **Python**

### Frameworks & Core Libraries

- **FastAPI** – HTTP API layer
- **Uvicorn** – ASGI server
- **Streamlit** – Web UI for document upload and chat (in `ui/`)
- **LangChain / LangChain Community / LangChain Core** – LLM orchestration, retrievers, vector stores, memory
- **LangGraph** – Agent workflow / state machine
- **Rank-BM25** – BM25 keyword-based retriever

### LLM & Embeddings

- **OpenAI** (via `openai` and `langchain-openai`)
  - Chat models (e.g., `gpt-4`, `gpt-4.1-mini`, `gpt-5.2` per config)
  - Embedding model (`text-embedding-3-large`)

### Storage & Retrieval

- **MongoDB**
  - Chat history (`MongoDBChatMessageHistory`)
  - Document store (`MongoDBStore`)
- **Qdrant**
  - Vector store for chunk embeddings (`langchain-qdrant`, `qdrant-client`)
  - Configurable collection, vector size, and filtering by `document_id`

### Document Processing

- **Unstructured.io** (`unstructured-client`)
  - PDF parsing and chunking
  - Output metadata includes positions / bounding boxes

### Observability & Telemetry

- **Langfuse** – Tracing & metrics
- **Sentry** – Error tracking

---

## Project Structure

High-level layout:

```text
LexReviewerMCP/
├── app.py                         # FastAPI app, route definitions, uvicorn entrypoint
├── models.py                      # Pydantic models and TypedDicts for API and agent state
├── DocumentReviewer.py            # LangGraph workflow for document-based QA
├── ui/
│   ├── ui_app.py                  # Streamlit entrypoint for the LexReviewerMCP UI
│   └── components/
│       ├── api.py                 # Thin client for FastAPI endpoints (upload, ask, history, reset)
│       ├── chat.py                # Chat UI, streaming answers and agent thoughts
│       ├── sidebar.py             # Sidebar controls: document ID, load/clear history, reset document
│       ├── uploader.py            # PDF upload + indexing UI
│       └── styles.py              # Global Streamlit CSS tweaks
├── agent_graph/
│   ├── nodes/
│   │   ├── agent_node.py                      # Main agent node with tool execution loop
│   │   ├── agent_prompt_generator_node.py     # Builds the agent's prompt/context
│   │   ├── required_tools_generator_node.py   # Chooses which tools to call
│   │   └── utils/
│   │       └── tool_executor.py               # Utility to call tools from the agent
│   └── tools/
│       ├── document_retriever.py              # Tool to retrieve chunks from Qdrant + MongoDB
│       ├── linked_documents.py                # Tool to fetch linked documents via HTTP
│       └── utils/
│           └── tool_config.py                 # Tool configuration helpers
├── chunker/
│   ├── provider.py                            # Chunker provider abstraction
│   └── Unstructured/
│       └── unstructured.py                    # Unstructured.io-based PDF chunker
├── llm_provider/
│   ├── provider.py                            # LLM provider abstraction
│   └── OpenAI/
│       └── openai.py                          # OpenAI-backed LLM & embeddings
├── observation/
│   ├── provider.py                            # Observation provider abstraction
│   ├── Langfuse/
│   │   └── langfuse.py                        # Langfuse client integration
│   └── Sentry/
│       └── sentry.py                          # Sentry initialization
├── prompts/
│   ├── legal_answer_prompt.txt                # System prompt for legal QA
│   └── chunk_summarizer_context.txt           # Prompt for chunk summarization
├── services/
│   ├── ChatHistorySummarizer.py               # Summarizes long chat histories
│   ├── ChunkSummarizer.py                     # Summarizes chunks prior to indexing
│   ├── EmbeddingIndexer.py                    # Indexes summarized chunks into Qdrant + Mongo
│   ├── PDFChunker.py                          # Uses Unstructured.io to chunk PDFs
│   ├── RAGIngestPipeline.py                   # Orchestrates ingestion: PDF → chunks → summaries → index
│   └── chat_service.py                        # Application-level chat logic and routing to agent
├── storage/
│   ├── provider.py                            # Storage provider abstraction
│   └── MongoDB/
│       └── mongodb.py                         # MongoDB-backed chat history + docstore
├── vector_storage/
│   ├── provider.py                            # Vector storage provider abstraction
│   └── Qdrant/
│       └── qdrant.py                          # Qdrant vector store configuration and access
├── .env.example                               # Example environment configuration
├── requirements.txt                           # Python dependencies (pinned versions)
└── .gitignore
```

**Important components:**

- **`app.py`**: Defines the FastAPI application, registers all routes, and includes a main block that runs `uvicorn` for local development.
- **`DocumentReviewer.py`**: Builds a LangGraph graph that manages the flow:
  - Generate required tools → build agent prompt → run the agent with tool calls.
- **`agent_graph/nodes`**: Implements discrete LangGraph nodes:
  - **`required_tools_generator_node`**: Decides which tools (e.g., retrievers) to call.
  - **`agent_prompt_generator_node`**: Constructs prompts with context, chat history, and instructions.
  - **`agent_node`**: Runs the LLM agent and handles tool invocation.
- **`agent_graph/tools`**:
  - **`document_retriever`**: Retrieves relevant document chunks from Qdrant and Mongo docstore, including metadata such as bounding boxes.
  - **`linked_documents`**: Calls an external service to fetch additional/linked documents.
- **`services`**: Application-level services for:
  - PDF chunking and summarization (`PDFChunker`, `ChunkSummarizer`)
  - Indexing into Qdrant and Mongo (`EmbeddingIndexer`, `RAGIngestPipeline`)
  - Chat management and orchestration (`chat_service`)
- **`storage` / `vector_storage`**: Provider abstractions and concrete implementations for MongoDB and Qdrant.
- **`observation`**: Pluggable observability (Langfuse, Sentry).
- **`prompts`**: Prompt templates used for legal answer formatting and chunk summarization.

---

## Setup Instructions

### Prerequisites

- **Python**: A modern Python 3 interpreter compatible with the packages in `requirements.txt` (e.g., Python 3.10+).
- **MongoDB**:
  - Running instance reachable by `MONGODB_URL`.
- **Qdrant**:
  - Running Qdrant instance reachable by `QDRANT_URL`.
- **Unstructured.io**:
  - Valid **Unstructured API key** (`UNSTRUCTURED_API_KEY`) and network access.
- **OpenAI**:
  - Valid **OpenAI API key** (`OPENAI_API_KEY`) and network access.

### Installation

From the project root:

```bash
# Create and activate a virtual environment (recommended)
python -m venv .venv
# On Windows PowerShell
.venv\Scripts\Activate.ps1
# On Unix-like shells
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Use `.env` at the project root (see `.env.example` for a complete list). Key variables include:

- **Application & prompts**
  - `CHATBOT_NAME` – Name used in prompts (default: `LexReviewer`).
  - `AGENT_MODEL` – Default agent model when reasoning is disabled (e.g., `gpt-4`).
  - `REASNONING_AGENT_MODEL` – Agent model when reasoning is enabled (`gpt-5.2` by default; note the variable name typo).
  - `AGENT_REASONING_ALLOWED` – `"true"`/`"false"` to enable or disable reasoning mode.

- **Linked documents**
  - `LINKED_DOCUMENT_FETCH_URL` – Base URL for the linked documents retriever tool.

- **Unstructured.io (chunking)**
  - `UNSTRUCTURED_API_KEY` – Required for PDF chunking.
  - Several `UNSTRUCTURED_*` options (max chars, overlap, strategy, etc.) to tune chunking behavior.

- **OpenAI**
  - `OPENAI_API_KEY` – Required.
  - `OPENAI_CHAT_SUMMARY_MODEL` – Model for chat history summarization (default `gpt-4.1-mini`).
  - `OPENAI_CHUNK_SUMMARY_MODEL` – Model for chunk summarization (default `gpt-4.1-mini`).
  - `REQUIRED_TOOLS_GENERATOR_MODEL` – Model for deciding required tools.
  - `OPENAI_EMBEDDING_MODEL_NAME` – Embedding model name (`text-embedding-3-large` default).

- **MongoDB**
  - `MONGODB_URL` – Connection string (default `mongodb://localhost:27017`).
  - `MONGODB_DATABASE` – Database name (default `lexstack`).
  - `MONGODB_CHAT_HISTORY_COLLECTION_NAME` – Chat history collection (default `chat_history`).
  - `MONGODB_DOC_STORE_COLLECTION_NAME` – Document store collection (default `doc_store`).

- **Qdrant**
  - `QDRANT_URL` – Qdrant endpoint URL.
  - `QDRANT_API_KEY` – Qdrant API key (if required by your instance).
  - `QDRANT_TIMEOUT` – Request timeout (seconds, default `60`).
  - `QDRANT_COLLECTION_NAME` – Collection name (default `documents`).
  - `QDRANT_VECTOR_SIZE` – Vector dimensionality (default `3072`).

- **Observability (optional)**
  - `SENTRY_DSN` – Sentry DSN for error tracking.
  - `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST` – Langfuse configuration.

Create your `.env` by copying the example:

```bash
cp .env.example .env
# Then edit .env with your own keys and URLs
```

---

## How to Run the Application

### Local Development

From the project root, after installing dependencies and configuring `.env`:

```bash
python app.py
```

`app.py` will start a Uvicorn server, typically on `http://0.0.0.0:8000` with `reload=True` for development.

### Run the Streamlit UI

With the backend running, you can start the Streamlit-based chat UI from the project root:

```bash
streamlit run ui/ui_app.py
```

This opens a browser UI where you can:

- Enter a **Document ID** and manage history/reset actions from the sidebar.
- Upload and index a PDF.
- Chat with the indexed document using the built-in chat interface.

### Running with Uvicorn Directly

As an alternative (especially for production-like runs):

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

You can adjust the host and port as needed. Additional Uvicorn options (workers, logging) are up to your deployment environment.


---

## Usage Guide

### Overview of User Workflow

You can interact with the system in two ways:

- **Via HTTP API** directly (e.g., `curl`, Postman, or another backend).
- **Via the built-in Streamlit UI** in `ui/`.

1. **Upload a document (PDF)**  
   Use `/upload-documents` to send a base64-encoded PDF along with a `document-id`.  
   The backend will:
   - Chunk the document via Unstructured.io.
   - Optionally summarize chunks.
   - Create embeddings and index them into Qdrant.
   - Store full content and metadata (including bounding boxes) in MongoDB.

2. **Ask questions about the document**  
   Use `/ask` with the same `document-id`, plus user identifiers, to start a chat.  
   The endpoint streams results (NDJSON) containing:
   - Answer text chunks
   - Thought snippets (agent reasoning commentary)
   - Reference positions that can be mapped back to document regions.

3. **Manage chat history**  
   Use the history-related endpoints to:
   - List history (`/get-history`)
   - Revert to a certain history entry (`/revert-history`)
   - Clear history (`/clear-history`)
   - Save or modify messages (`/save-message-in-history`)

4. **Manage document index**  
   Use `/collection-exists` to check if a document (or several) has already been indexed.  
   Use `/delete-vector` to remove the indexed vectors and history for a document.

### Using the built-in Streamlit UI

The Streamlit UI (`ui/ui_app.py`) wires these workflows into an interactive web app:

- **Document selection & history controls** (`ui/components/sidebar.py`):
  - Set the active `document_id`.
  - **Load History** – calls `GET /get-history` and populates the chat view.
  - **Clear History** – calls `DELETE /clear-history` and clears the local chat state.
  - **Reset Document** – calls `DELETE /delete-vector` to remove vectors and history for the current document.

- **Document upload & indexing** (`ui/components/uploader.py`):
  - Upload a PDF via file picker.
  - On **Index Document**, encodes the file to base64 and calls `POST /upload-documents`.
  - On success, sets `st.session_state.document_indexed = True`, which unlocks the chat panel.

- **Chat with the document** (`ui/components/chat.py` + `ui/components/api.py`):
  - Renders previous Q&A pairs from `st.session_state.chat_messages`.
  - Uses a `st.chat_input` to send questions.
  - Streams answers via `POST /ask` (NDJSON):
    - Accumulates `chunk` events into the answer text.
    - Accumulates `thought` events into a single **“Agent Thinking”** expander.
    - Ignores `reference_positions` in the UI for now but keeps them available in the stored messages.

### Example: Upload Document

```bash
curl -X POST http://localhost:8000/upload-documents \
  -H "Content-Type: application/json" \
  -H "document-id: DOC_123" \
  -d '{
        "file": "<BASE64_ENCODED_PDF_CONTENT>"
      }'
```

- **Headers**:
  - `document-id`: A string you choose to identify this document (e.g., `case_2024_01`).

### Example: Ask a Question (Streaming)

```bash
curl -N -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "document-id: DOC_123" \
  -H "user-id: USER_1" \
  -H "username: alice" \
  -d '{
        "question": "What are the main obligations of the tenant under this lease?"
      }'
```

- **Response**: NDJSON stream with lines like:

```json
{"chunk": "The tenant must pay rent on time..."}
{"thought": ["Checking", "clauses", "related", "to", "payment", "and", "maintenance."]}
{"reference_positions": [{ "page": 3, "x1": ..., "y1": ..., "x2": ..., "y2": ... }]}
{"chunk": "Additionally, the tenant is responsible for utilities..."}
```

You can consume this stream in your frontend to render a progressively updating answer, legal reasoning snippets, and highlight positions in the document.

### Example: Get Chat History

```bash
curl -X GET "http://localhost:8000/get-history" \
  -H "document-id: DOC_123" \
  -H "user-id: USER_1"
```

- Returns:
  - A structure (e.g., `HistoryResponse`) with a list of chat entries, each including the question, answer, thoughts, and reference positions.

### Example: Check If a Document Is Indexed

```bash
curl -X POST http://localhost:8000/collection-exists \
  -H "Content-Type: application/json" \
  -H "document-ids: DOC_123" \
  -d '{}'
```

> Note: `collection-exists` uses a header list (`document_ids: List[str] = Header(...)`), which may require passing multiple header values depending on your HTTP client.

---

## Architecture Overview

### High-Level Flow

```text
+------------------+       +-------------------+       +----------------+
|   Client / UI    | --->  |   FastAPI (app)   | --->  |   LangGraph    |
+------------------+       +-------------------+       +----------------+
         |                          |                             |
         | /upload-documents        |                             |
         |------------------------->|                             |
         |                          |    PDFChunker + RAGIngest   |
         |                          |----> Chunk + Summarize ---->|
         |                          |                             |
         | /ask                     |                             |
         |------------------------->|    DocumentReviewer (graph) |
         |                          |----> Tools: retriever,      |
         |                          |     linked_documents        |
         |                          |                             |
         |  NDJSON stream (answer,  |<----------------------------|
         |  thoughts, references)   |                             |
```

### Components and Data Flow

- **Ingestion pipeline (`RAGIngestPipeline`, `PDFChunker`, `ChunkSummarizer`, `EmbeddingIndexer`)**:
  1. Take a PDF uploaded via `/upload-documents`.
  2. Use Unstructured.io to chunk the document; metadata contains layout and bounding boxes.
  3. Optionally summarize chunks to create more compact index entries.
  4. Compute embeddings using OpenAI.
  5. Store:
     - Embeddings in Qdrant with `document_id` metadata.
     - Full chunks and metadata in MongoDB docstore.

- **Retrieval layer (`document_retriever`, `linked_documents`)**:
  - **Document retriever**:
    - Combines Qdrant vector search and BM25 keyword search.
    - Uses `document_id` to restrict results.
    - Fetches full chunk content and bounding boxes from MongoDB.
  - **Linked documents tool**:
    - Calls an external HTTP service (URL from `LINKED_DOCUMENT_FETCH_URL`) to fetch related documents that can also be used in responses.

- **Agent layer (`DocumentReviewer`, `agent_graph/nodes`)**:
  - A LangGraph graph manages the conversation state (`AgentState`).
  - **Required tools generator node** selects which tools to call (e.g., document retriever, linked document retriever).
  - **Agent prompt generator node** composes prompts that:
    - Include the user question
    - Inject context from tools
    - Follow the legal-answer prompt template
  - **Agent node** runs the OpenAI-backed LLM, possibly in reasoning mode, and streams out partial answers, thoughts, and references.

- **Chat history (`storage/MongoDB`, `services/chat_service`)**:
  - Uses `MongoDBChatMessageHistory` with session IDs like `"{user_id}_{document_id}"`.
  - Enables:
    - Persisted multi-turn conversations
    - Summarization of older turns to keep context manageable

- **Observability (`observation`)**:
  - Langfuse integration can trace key steps (summarization, retrieval, answering).
  - Sentry can capture exceptions and performance data.

There is **no separate frontend** in this repo; it is purely a backend API intended to be consumed by a client (web app, desktop app, etc.).

---

## Available Scripts and Commands

There are no custom CLI scripts or `pyproject.toml` console entry points in the repository. The main commands are:

- **Run the API (development)**:

  ```bash
  python app.py
  ```

- **Run the API with Uvicorn**:

  ```bash
  uvicorn app:app --host 0.0.0.0 --port 8000
  ```

You may create your own wrapper scripts or process manager configuration (e.g., `systemd`, `supervisord`, container entrypoints) as needed.

---

## API Endpoints

The following endpoints are defined in `app.py` (all paths relative to the API root):

- **`POST /upload-documents`**
  - **Headers**:
    - `document-id`: ID for the document being uploaded.
  - **Body** (`DocumentUploadRequest`):
    - `file: str` – Base64-encoded PDF.
  - **Behavior**:
    - Triggers ingestion pipeline to chunk, summarize, embed, and index the document.

- **`POST /collection-exists`**
  - **Headers**:
    - `document-ids`: One or more document IDs (list semantics via headers).
  - **Body**:
    - Currently not used for payload (header-based identifiers).
  - **Behavior**:
    - Checks if vector/index data exists for the given document IDs.

- **`POST /ask`**
  - **Headers**:
    - `document-id`
    - `user-id`
    - `username`
  - **Body** (`AskQuestionRequest`):
    - `question: str`
  - **Response**:
    - **Content-Type**: `application/x-ndjson`
    - Streams events with:
      - `chunk` – parts of the answer.
      - `thought` – agent reasoning or intermediate commentary.
      - `reference_positions` – list of reference positions/bounding boxes.
      - `error` – error messages if any.

- **`POST /save-message-in-history`**
  - **Headers**:
    - `document-id`
    - `user-id`
  - **Body**:
    - Contains message/history data (structured via models in `models.py`).
  - **Behavior**:
    - Persists or updates entries in the chat history for the given user and document.

- **`POST /revert-history`**
  - **Headers**:
    - `document-id`
    - `user-id`
  - **Body** (`EditQuestionRequest`-like):
    - `index: int` – History index to revert to.
  - **Behavior**:
    - Truncates chat history back to the specified index.

- **`DELETE /delete-vector`**
  - **Headers**:
    - `document-id`
    - `user-id`
  - **Behavior**:
    - Deletes vector index data in Qdrant and associated document/chat store data for that document.

- **`DELETE /clear-history`**
  - **Headers**:
    - `document-id`
    - `user-id`
  - **Behavior**:
    - Clears chat history for the given user and document.

- **`GET /get-history`**
  - **Headers**:
    - `document-id`
    - `user-id`
  - **Response** (`HistoryResponse`):
    - `chatHistory: List[ChatEntry]` where each entry includes question, answer, thoughts, and reference positions.

> Note: Exact field names and structures are defined in `models.py`. This README describes their roles at a high level.

---

## Database and Storage Details

### MongoDB

- **Collections** (configurable via env):
  - `MONGODB_CHAT_HISTORY_COLLECTION_NAME` (default: `chat_history`)
  - `MONGODB_DOC_STORE_COLLECTION_NAME` (default: `doc_store`)
- **Usage**:
  - **Chat history**:
    - Stores user conversations keyed by session ID (`user_id` + `document_id`).
    - Used by chat services and history summarizer to maintain conversational context.
  - **Docstore**:
    - Stores full chunk texts and all relevant metadata (e.g., bounding boxes, page, section).
    - Acts as the source of truth when reconstructing context for answers.

### Qdrant

- **Collection**:
  - Name from `QDRANT_COLLECTION_NAME` (default `documents`).
- **Vector configuration**:
  - Dimensionality from `QDRANT_VECTOR_SIZE` (default `3072`).
  - Distance metric and other settings configured in `vector_storage/Qdrant/qdrant.py`.
- **Usage**:
  - Stores embeddings of (optionally summarized) document chunks.
  - Filters results by `document_id` metadata.
  - Combined with BM25 retriever for robust retrieval.

### Unstructured.io

- **Service**:
  - Unstructured API is used to parse and chunk PDFs.
- **Metadata**:
  - Output includes layout details such as bounding boxes that are persisted in MongoDB and surfaced via `reference_positions` in the chat responses.

---

## Deployment Instructions

To deploy this service, you will typically:

- Provision or connect to:
  - A **MongoDB** instance.
  - A **Qdrant** instance.
  - Accessible **OpenAI** and **Unstructured.io** APIs.
- Configure environment variables (using `.env` or your platform’s secret manager).
- Run the app with a production-grade ASGI server, for example:

  ```bash
  uvicorn app:app --host 0.0.0.0 --port 8000
  ```

- Place a reverse proxy (e.g., Nginx) or API gateway in front, handle TLS termination, rate limiting, authentication, and logging as fit for your environment.

Scaling, containerization, and orchestration are left to your infrastructure/platform choices.

---

## Contribution Guidelines

- **Set up the environment**:
  - Clone the repository and configure Python, MongoDB, Qdrant, and all relevant environment variables.
- **Create a feature branch**:
  - `git checkout -b feature/your-feature-name`
- **Make changes with care**:
  - Follow existing module boundaries (`services`, `agent_graph`, `storage`, `vector_storage`).
  - Keep configuration in environment variables rather than hard-coding secrets or endpoints.
  - Maintain type hints and use existing models (`models.py`) where possible.
- **Testing**:
  - There are currently **no automated tests** in this repository.
  - Add tests (e.g., using `pytest`) where appropriate if you introduce complex logic.
  - At minimum, exercise modified endpoints with local requests (e.g., via `curl` or Postman).
- **Submit changes**:
  - Commit with clear messages.
  - Open a pull request describing:
    - What you changed.
    - Why it is needed.
    - Any new configuration or environment variables introduced.

Please coordinate with the project maintainers for coding style and review expectations if this is part of a larger organization.

---
