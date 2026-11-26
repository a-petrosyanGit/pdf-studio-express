"""
ui/web/state.py - Gestion d'état unifié et mise en cache haute performance Streamlit.
Permet à tous les onglets de partager le même document actif et l'historique Undo.
"""

import io
import os
from typing import Optional, Tuple
import pymupdf as fitz
from PIL import Image, ImageDraw
import streamlit as st

from core import ocr_engine, pages as core_pages
from core.temp_manager import SessionTempManager


@st.cache_resource
def get_cached_ocr():
    """Initialise et met en cache le moteur RapidOCR."""
    return ocr_engine.get_ocr_engine()


@st.cache_data(max_entries=128)
def get_cached_thumbnail_bytes(
    pdf_bytes: bytes, page_idx: int, size: Tuple[int, int] = (180, 240)
) -> bytes:
    """Met en cache le rendu miniature PNG d'une page."""
    doc = fitz.open("pdf", pdf_bytes)
    try:
        if page_idx < 0 or page_idx >= len(doc):
            return b""
        page = doc[page_idx]
        scale_w = size[0] / max(page.rect.width, 1.0)
        scale_h = size[1] / max(page.rect.height, 1.0)
        scale = min(scale_w, scale_h, 2.0)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


@st.cache_data(max_entries=64)
def get_cached_page_preview(pdf_bytes: bytes, page_idx: int, dpi: int = 140) -> bytes:
    """Met en cache le rendu net d'une page pour l'aperçu d'édition."""
    doc = fitz.open("pdf", pdf_bytes)
    try:
        if page_idx < 0 or page_idx >= len(doc):
            return b""
        return doc[page_idx].get_pixmap(dpi=dpi, alpha=False).tobytes("png")
    finally:
        doc.close()


def draw_highlight_box(
    png_bytes: bytes, bbox: Tuple[float, float, float, float], dpi: int = 140
) -> bytes:
    """Dessine un rectangle de surlignage bleu autour de la zone sélectionnée."""
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    scale = dpi / 72.0
    draw = ImageDraw.Draw(img)
    x0, y0, x1, y1 = [v * scale for v in bbox]
    draw.rectangle([x0 - 3, y0 - 2, x1 + 3, y1 + 2], outline="#2563eb", width=3)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def set_active_document(
    file_bytes: bytes, file_name: str, push_history: bool = False
) -> None:
    """Met à jour le document actif partagé entre tous les outils Web."""
    if push_history and "active_bytes" in st.session_state:
        history = st.session_state.setdefault("doc_history", [])
        history.append(st.session_state["active_bytes"])
    elif not push_history:
        st.session_state["doc_history"] = []

    st.session_state.pop("te_selected_bbox", None)
    st.session_state["active_bytes"] = file_bytes
    st.session_state["active_name"] = file_name
    sync_page_order_for_bytes(file_bytes, reset=True)


def sync_page_order_for_bytes(file_bytes: bytes, reset: bool = False) -> None:
    if not reset and "pages_order" in st.session_state:
        return
    with SessionTempManager() as tm:
        tmp = tm.create_temp_file(suffix=".pdf")
        with open(tmp, "wb") as handle:
            handle.write(file_bytes)
        meta = core_pages.get_pdf_metadata(tmp)
    st.session_state["pages_order"] = list(range(meta.page_count))
    st.session_state["pages_rotation"] = {i: 0 for i in range(meta.page_count)}


def undo_active_document() -> bool:
    """Restaure l'état précédent du document depuis l'historique de session."""
    history = st.session_state.get("doc_history", [])
    if not history:
        return False
    prev_bytes = history.pop()
    st.session_state["doc_history"] = history
    st.session_state["active_bytes"] = prev_bytes
    st.session_state.pop("te_selected_bbox", None)
    sync_page_order_for_bytes(prev_bytes, reset=True)
    return True


def get_active_document() -> Tuple[Optional[bytes], str]:
    """Retourne `(bytes, filename)` du document actuellement chargé."""
    return (
        st.session_state.get("active_bytes"),
        st.session_state.get("active_name", "document.pdf"),
    )


def render_sidebar_document_widget(example_path: str) -> None:
    """Affiche le sélecteur global de document et les actions Undo/Export."""
    uploaded = st.sidebar.file_uploader(
        "📂 Charger votre PDF :", type=["pdf"], key="global_uploader"
    )
    if uploaded is not None:
        raw = uploaded.read()
        if raw != st.session_state.get("last_uploaded_raw"):
            st.session_state["last_uploaded_raw"] = raw
            set_active_document(raw, uploaded.name, push_history=False)

    if st.sidebar.button("📄 Charger le document d'exemple", use_container_width=True):
        if os.path.exists(example_path):
            with open(example_path, "rb") as handle:
                set_active_document(handle.read(), "exemple_document.pdf")
            st.rerun()

    file_bytes, file_name = get_active_document()
    if file_bytes:
        st.sidebar.success(f"Actif : **{file_name}**")
        history = st.session_state.get("doc_history", [])
        if history and st.sidebar.button(
            f"↩ Annuler ({len(history)})", use_container_width=True
        ):
            undo_active_document()
            st.rerun()
        st.sidebar.download_button(
            label="💾 Télécharger le PDF actuel",
            data=file_bytes,
            file_name=f"edite_{file_name}",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
