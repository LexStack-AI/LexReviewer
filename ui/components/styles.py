"""Custom CSS for LexReviewerMCP UI: layout, chat, and PDF viewer."""

import streamlit as st


def load_styles():
    """Inject CSS for layout and chat styling."""
    st.markdown("""
    <style>
        /* Hide sidebar for a clean single-panel experience */
        [data-testid="stSidebar"] {
            display: none;
        }
        header [data-testid="stToolbar"] {
            display: none;
        }

        .main {
            padding: 1.5rem 2rem 2rem;
            max-width: 100%;
        }

        .block-container {
            max-width: 100%;
            padding-top: 1rem;
        }

        /* 50:50 columns: fixed height, scrollable, with separate borders */
        [data-testid="column"] {
            max-height: 85vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 1rem;
            margin: 0 0.25rem;
            background: #fff;
        }
        [data-testid="column"]:first-child {
            margin-right: 0.5rem;
        }
        [data-testid="column"]:last-child {
            margin-left: 0.5rem;
        }
        /* Push chat input to bottom of chat column: spacer grows */
        .chat-input-spacer {
            flex: 1 1 auto;
            min-height: 1rem;
        }
        /* Pin chat input at bottom of the chat column (last column) */
        [data-testid="column"]:last-child [data-testid="stChatInput"],
        [data-testid="column"]:last-child .stChatInputContainer,
        [data-testid="column"]:last-child .stChatFloatingInputContainer {
            position: sticky !important;
            bottom: 0 !important;
            background: var(--background-color, #fff) !important;
            z-index: 2;
            margin-top: auto !important;
        }

        /* Chat messages */
        .stChatMessage {
            padding: 14px 16px;
            border-radius: 12px;
            margin-bottom: 8px;
        }
        .stChatMessage[data-testid="stChatMessage-user"] {
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
            border: 1px solid #e2e8f0;
        }
        .stChatMessage[data-testid="stChatMessage-assistant"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }

        /* Buttons */
        .stButton button {
            border-radius: 8px;
            height: 38px;
            font-weight: 500;
            transition: background 0.15s ease;
        }
        # .stButton button:hover {
        #     background-color: #f1f5f9 !important;
        # }

        /* Title and subtitle */
        h1 {
            font-size: 1.75rem !important;
            font-weight: 700 !important;
            margin-bottom: 0.25rem !important;
        }
        .stSubheader {
            color: #64748b !important;
            font-size: 1rem !important;
            margin-bottom: 1.5rem !important;
        }

        /* Uploader section */
        .stRadio > div {
            gap: 0.5rem;
        }
        [data-testid="stFileUploader"] {
            padding: 1rem 0;
        }
        [data-testid="stFileUploader"] section {
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
        }
        [data-testid="stFileUploader"] section:hover {
            border-color: #94a3b8;
        }
    </style>
    """, unsafe_allow_html=True)
