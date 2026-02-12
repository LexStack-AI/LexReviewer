import streamlit as st
from components.styles import load_styles
from components.sidebar import render_sidebar
from components.uploader import render_uploader
from components.chat import render_chat

st.set_page_config(page_title="LexStackMCP", layout="wide")

load_styles()

st.markdown('<div class="title">LexStackMCP</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Legal Document Intelligence</div>', unsafe_allow_html=True)

if "user_id" not in st.session_state:
    st.session_state.user_id = "demo-user"

if "username" not in st.session_state:
    st.session_state.username = "demo"

if "document_indexed" not in st.session_state:
    st.session_state.document_indexed = False

document_id = render_sidebar()

render_uploader(document_id)

st.divider()

render_chat(document_id)