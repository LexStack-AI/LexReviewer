import streamlit as st
import base64
from .api import upload_document

def render_uploader(document_id):
    st.subheader("Upload Document")

    file = st.file_uploader("Upload PDF", type=["pdf"])

    if file and st.button("Index Document"):
        b64 = base64.b64encode(file.read()).decode()

        with st.spinner("Indexing document..."):
            try:
                upload_document(document_id, b64)

                st.session_state.document_indexed = True  # ⭐ enable chat
                st.success("Document indexed successfully. You can now chat.")
            except Exception as e:
                st.error(str(e))