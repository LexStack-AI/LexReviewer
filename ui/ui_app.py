"""Streamlit frontend for the LexStackMCP document QA experience."""

import uuid

from random_username.generate import generate_username
import streamlit as st

from components.chat import render_chat
from components.pdf import render_pdf
from components.styles import load_styles
from components.uploader import render_uploader

st.set_page_config(page_title="LexStackMCP", layout="wide")

load_styles()

st.markdown('<h1 style="padding-top: 3rem;">LexStackMCP</h1>', unsafe_allow_html=True)

# Session identifiers
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user-{str(uuid.uuid4())}"
if "username" not in st.session_state:
    st.session_state.username = str(generate_username(1)[0])

if "document_id" in st.session_state:
    st.text(f"Document ID: {st.session_state.document_id}")
if "user_id" in st.session_state:
    st.text(f"User ID: {st.session_state.user_id}")
if "username" in st.session_state:
    st.text(f"User Name: {st.session_state.username}")

# Document and upload state
if "document_indexed" not in st.session_state:
    st.session_state.document_indexed = False
if "show_uploader" not in st.session_state:
    st.session_state.show_uploader = True
if "pdf_base64" not in st.session_state:
    st.session_state.pdf_base64 = ""
if "indexing_in_progress" not in st.session_state:
    st.session_state.indexing_in_progress = False
if "chat_only_mode" not in st.session_state:
    st.session_state.chat_only_mode = False

# Main content
if st.session_state.get("show_uploader", True):
    render_uploader()
else:
    # Document is indexed: show PDF (if we have it) and chat
    has_pdf = st.session_state.get("pdf_base64") and not st.session_state.get("chat_only_mode", False)

    if has_pdf:
        col_pdf, col_chat = st.columns([1, 1])
        with col_pdf:
            render_pdf(st.session_state.pdf_base64)
        with col_chat:
            render_chat()
    else:
        render_chat()
