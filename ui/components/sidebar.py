import streamlit as st
from .api import load_history, clear_history, reset_vectors

def render_sidebar():
    st.sidebar.title("📄 Document")

    document_id = st.sidebar.text_input("Document ID", "DOC_123")

    if st.sidebar.button("Load History"):
        try:
            data = load_history(document_id, st.session_state.user_id)
            st.session_state.chat_messages = data
            st.sidebar.success("Loaded")
        except Exception as e:
            st.sidebar.error(str(e))

    if st.sidebar.button("Clear History"):
        clear_history(document_id, st.session_state.user_id)
        st.session_state.chat_messages = []

    if st.sidebar.button("Reset Document"):
        reset_vectors(document_id, st.session_state.user_id)
        st.session_state.chat_messages = []
        st.session_state.document_indexed = False

    return document_id