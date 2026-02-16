"""Streamlit chat interface for asking questions over the indexed document."""

import streamlit as st

from .api import stream_answer, reset_vectors, clear_history, save_message


def _reset_document():
    """Reset document state and clear history so user returns to uploader."""
    doc_id = st.session_state.get("document_id")
    user_id = st.session_state.get("user_id")
    if doc_id and user_id:
        try:
            reset_vectors(doc_id, user_id)
            _clear_history()
        except Exception:
            pass
    st.session_state.chat_messages = []
    st.session_state.pop("document_id", None)
    st.session_state.document_indexed = False
    st.session_state.show_uploader = True
    st.session_state.pdf_base64 = ""
    st.session_state.chat_only_mode = False
    # Clear PDF viewer page state so next document gets fresh page count
    for key in list(st.session_state.keys()):
        if key.startswith("pdf_viewer_"):
            del st.session_state[key]
    st.rerun()

def _clear_history():
    """Reset document state and clear history so user returns to uploader."""
    doc_id = st.session_state.get("document_id")
    user_id = st.session_state.get("user_id")
    if doc_id and user_id:
        try:
            clear_history(doc_id, user_id)
        except Exception:
            pass
    st.session_state.chat_messages = []

def render_chat():
    """Render the full chat experience: messages in scrollable area, input at bottom, reset top-right."""

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if not st.session_state.get("document_indexed", False):
        st.info("Upload and index a document, or open by document ID, to start chatting.")
        st.chat_input("Ask something about the document", disabled=True)
        return

    # Top-right: reset document and clear history (side by side)
    _, reset_col, clear_col = st.columns([2, 1, 1])
    with reset_col:
        if st.button("Reset document", type="secondary"):
            _reset_document()
            return
    with clear_col:
        if st.button("Clear history", type="secondary"):
            _clear_history()

    # Messages area (scrollable via CSS)
    for msg in st.session_state.chat_messages:
        with st.chat_message("user"):
            st.markdown(msg.get("question", ""))

        with st.chat_message("assistant"):
            thoughts = msg.get("thoughts")
            if thoughts:
                if isinstance(thoughts, list):
                    thoughts = "\n".join(str(t) for t in thoughts)
                with st.expander("Agent thinking", expanded=False):
                    st.markdown(thoughts)
            st.markdown(msg.get("answer", ""))

    # Spacer so messages push up and input stays at bottom of chat column
    st.markdown("<div class='chat-input-spacer'></div>", unsafe_allow_html=True)
    question = st.chat_input("Ask something about the document")

    if not question:
        return

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        thoughts_expander = st.expander("Agent thinking", expanded=False)
        with thoughts_expander:
            thoughts_placeholder = st.empty()
        answer_box = st.empty()

        final_answer = ""
        final_thoughts = ""
        final_refs = []

        for text, thoughts, refs in stream_answer(
            question,
            st.session_state.document_id,
            st.session_state.user_id,
            st.session_state.username,
        ):
            final_answer = text
            final_thoughts = thoughts
            final_refs = refs
            answer_box.markdown(text or "Thinking...")
            thoughts_placeholder.markdown(final_thoughts)

    st.session_state.chat_messages.append({
        "question": question,
        "answer": final_answer,
        "thoughts": final_thoughts,
        "reference_positions": final_refs,
    })

    save_message(
        st.session_state.document_id,
        st.session_state.user_id,
        question,
        final_answer,
        final_thoughts,
        final_refs
    )