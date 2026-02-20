"""File upload and document ID entry for the LexReviewer document QA experience."""

import base64
import uuid

import streamlit as st

from .api import upload_document, load_history

# Session state keys used by this component (initialized in ui_app if needed):
# - document_id, document_indexed, show_uploader, pdf_base64
# - indexing_in_progress, chat_only_mode


def render_uploader():
    """Render either PDF upload or document ID input; return pdf base64 when from upload path."""
    st.subheader("Upload or open a document")

    mode = st.radio(
        "Choose how to proceed",
        ["Upload a PDF", "Open by document ID"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if mode == "Upload a PDF":
        return _render_upload_flow()
    return _render_document_id_flow()


def _render_upload_flow():
    indexing = st.session_state.get("indexing_in_progress", False)

    if indexing:
        st.info("Indexing in progress… You cannot upload another PDF until this finishes.")
        return st.session_state.get("pdf_base64", "")

    file = st.file_uploader("Upload PDF", type=["pdf"], disabled=indexing)

    if not file:
        return ""

    # Show the Index button only after a file is selected.
    if st.button("Index document", type="primary"):
        b64 = base64.b64encode(file.read()).decode()
        doc_id = str(uuid.uuid4())

        st.session_state.indexing_in_progress = True
        st.session_state.pdf_base64 = b64
        st.session_state.document_id = doc_id

        with st.spinner("Indexing document…"):
            try:
                upload_document(doc_id, b64)
                st.session_state.document_indexed = True
                st.session_state.show_uploader = False
                st.session_state.chat_only_mode = False
                st.session_state.indexing_in_progress = False
                st.success("Document indexed. You can chat below.")
                st.rerun()
            except Exception as e:
                st.session_state.indexing_in_progress = False
                st.error(str(e))

    return st.session_state.get("pdf_base64", "")

def _render_document_id_flow():
    doc_id_input = st.text_input(
        "Document ID",
        placeholder="Paste the document ID to load its chat history",
        key="uploader_doc_id_input",
    )

    user_id_input = st.text_input(
        "User ID",
        placeholder="Paste the user ID to load its chat history",
        key="uploader_user_id_input",
    )

    if not doc_id_input.strip() or not user_id_input.strip():
        return ""

    if st.button("Fetch history"):
        with st.spinner("Loading history…"):
            try:
                data = load_history(doc_id_input.strip(), user_id_input.strip())
                st.session_state.document_id = doc_id_input.strip()
                st.session_state.user_id = user_id_input.strip()
                st.session_state.chat_messages = data
                st.session_state.document_indexed = True
                st.session_state.show_uploader = False
                st.session_state.chat_only_mode = True
                st.session_state.pdf_base64 = ""
                st.success("History loaded. You can continue chatting.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    return ""
