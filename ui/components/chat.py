"""Streamlit chat interface for asking questions over the indexed document."""

import streamlit as st
from .api import stream_answer


def render_chat(document_id):
    """Render the full chat experience including history and streaming replies."""

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # ⭐ BLOCK CHAT IF NOT INDEXED
    # We explicitly prevent chatting until the backend has indexed a document
    # to avoid confusing "no context" responses and wasted API calls.
    if not st.session_state.get("document_indexed", False):
        st.info("📄 Upload and index a document to start chatting.")
        st.chat_input("Ask something about the document", disabled=True)
        return

    # Render previous conversation so the user sees full context.
    for msg in st.session_state.chat_messages:
        with st.chat_message("user"):
            st.markdown(msg["question"])

        with st.chat_message("assistant"):
            if msg.get("thoughts"):
                with st.expander("🧠 Agent Thinking", expanded=False):
                    st.markdown(msg["thoughts"])

            st.markdown(msg["answer"])

    # New question input from the user.
    question = st.chat_input("Ask something about the document")

    if not question:
        return

    with st.chat_message("user"):
        st.markdown(question)

    # Stream model answer and reasoning tokens into the UI.
    with st.chat_message("assistant"):
        thoughts_expander = st.expander("🧠 Agent Thinking", expanded=False)
        with thoughts_expander:
            thoughts_placeholder = st.empty()
        answer_box = st.empty()

        final_answer = ""
        final_thoughts = ""
        final_refs = []

        for text, thoughts, refs in stream_answer(
            question,
            document_id,
            st.session_state.user_id,
            st.session_state.username,
        ):
            final_answer = text
            final_thoughts = thoughts
            final_refs = refs

            answer_box.markdown(text or "Thinking...")
            thoughts_placeholder.markdown(final_thoughts)

    # Persist the full turn so it shows up on the next render.
    st.session_state.chat_messages.append({
        "question": question,
        "answer": final_answer,
        "thoughts": final_thoughts,
        "reference_positions": final_refs,
    })