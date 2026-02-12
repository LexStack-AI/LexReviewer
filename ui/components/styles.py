import streamlit as st

def load_styles():
    st.markdown("""
    <style>
        .main {
            padding-top: 1rem;
        }

        .stChatMessage {
            padding: 14px;
            border-radius: 12px;
        }

        .stChatMessage[data-testid="stChatMessage-user"] {
            background-color: #f1f5f9;
        }

        .stChatMessage[data-testid="stChatMessage-assistant"] {
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
        }

        .stButton button {
            border-radius: 8px;
            height: 38px;
        }

        .block-container {
            max-width: 900px;
            padding-top: 2rem;
        }

        .title {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #6b7280;
            margin-bottom: 25px;
        }
    </style>
    """, unsafe_allow_html=True)