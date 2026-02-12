"""Streamlit frontend for the LexStackMCP document QA experience."""

import streamlit as st
from components.styles import load_styles
from components.sidebar import render_sidebar
from components.uploader import render_uploader
from components.chat import render_chat

# Configure the Streamlit page and overall layout once at startup.
st.set_page_config(page_title="LexStackMCP", layout="wide")

load_styles()

st.markdown('<div class="title">LexStackMCP</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Legal Document Intelligence</div>', unsafe_allow_html=True)

# Seed basic user/session identifiers for demo usage.
if "user_id" not in st.session_state:
    st.session_state.user_id = "demo-user"

if "username" not in st.session_state:
    st.session_state.username = "demo"

# Tracks whether the current document has been successfully indexed.
if "document_indexed" not in st.session_state:
    st.session_state.document_indexed = False

# Sidebar controls return the active document identifier.
document_id = render_sidebar()

# Main area: upload/index flow followed by chat interface.
render_uploader(document_id)

st.divider()

render_chat(document_id)