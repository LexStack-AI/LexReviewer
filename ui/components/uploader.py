"""File upload component for sending PDFs to the backend for indexing."""

import streamlit as st
import base64
from .api import upload_document


def render_uploader(document_id):
    """Render the PDF uploader and trigger backend ingestion."""
    st.subheader("Upload Document")

    file = st.file_uploader("Upload PDF", type=["pdf"])

    if file and st.button("Index Document"):
        # Backend expects a base64-encoded payload instead of raw bytes.
        b64 = base64.b64encode(file.read()).decode()

        with st.spinner("Indexing document..."):
            try:
                upload_document(document_id, b64)

                # Once indexing succeeds we allow the chat component to be used.
                st.session_state.document_indexed = True  # ⭐ enable chat
                st.success("Document indexed successfully. You can now chat.")
            except Exception as e:
                st.error(str(e))