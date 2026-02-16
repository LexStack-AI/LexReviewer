"""Single-page PDF viewer with page navigation."""

import base64
from ctypes import alignment
import io

import streamlit as st
from pypdf import PdfReader, PdfWriter


def _get_page_count(base64_pdf: str) -> int:
    raw = base64.b64decode(base64_pdf)
    reader = PdfReader(io.BytesIO(raw))
    return len(reader.pages)


def _get_single_page_base64(base64_pdf: str, page_index: int) -> str:
    """Return base64 of a PDF containing only the page at page_index (0-based)."""
    raw = base64.b64decode(base64_pdf)
    reader = PdfReader(io.BytesIO(raw))
    writer = PdfWriter()
    writer.add_page(reader.pages[page_index])
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return base64.b64encode(out.read()).decode()


def render_pdf(base64_pdf: str, height_px: int = 720):
    """Render a single page of the PDF with previous/next controls."""
    if not base64_pdf or len(base64_pdf) == 0:
        return

    key_prefix = "pdf_viewer"
    if f"{key_prefix}_total_pages" not in st.session_state:
        try:
            st.session_state[f"{key_prefix}_total_pages"] = _get_page_count(base64_pdf)
        except Exception:
            st.session_state[f"{key_prefix}_total_pages"] = 1

    total = max(1, st.session_state[f"{key_prefix}_total_pages"])
    current_key = f"{key_prefix}_current_page"
    if current_key not in st.session_state:
        st.session_state[current_key] = 0

    current = st.session_state[current_key]
    current = max(0, min(current, total - 1))
    st.session_state[current_key] = current

    # Page controls
    col_prev, col_label, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("← Previous", key="pdf_prev", disabled=(current <= 0)):
            st.session_state[current_key] = current - 1
            st.rerun()
    with col_label:
        st.markdown(
            f"<p style='text-align: center; margin: 0.5rem 0; color: #64748b;'>Page {current + 1} of {total}</p>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Next →", key="pdf_next", disabled=(current >= total - 1)):
            st.session_state[current_key] = current + 1
            st.rerun()

    try:
        single_b64 = _get_single_page_base64(base64_pdf, current)
    except Exception:
        single_b64 = base64_pdf

    pdf_display = f"""
        <iframe
            src="data:application/pdf;base64,{single_b64}"
            width="100%"
            height="{height_px}"
            type="application/pdf"
            style="border: 1px solid #e2e8f0; border-radius: 8px;">
        </iframe>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)
