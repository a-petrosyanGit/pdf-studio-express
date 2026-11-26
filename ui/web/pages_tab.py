"""
ui/web/pages_tab.py - Organiseur visuel de pages pour Streamlit.
Inclut le réordonnancement (◀ ▶), rotation (↺ ↻) et suppression par page.
"""

import io
from PIL import Image
import streamlit as st

from core import pages as core_pages
from core.models import PageConfig
from core.temp_manager import SessionTempManager
from ui.web.state import (
    get_cached_thumbnail_bytes,
    set_active_document,
    sync_page_order_for_bytes,
)


def _apply_page_changes_to_session(file_bytes: bytes, file_name: str) -> None:
    configs = [
        PageConfig(
            source_page=p,
            rotation=st.session_state["pages_rotation"].get(p, 0),
        )
        for p in st.session_state["pages_order"]
    ]
    with SessionTempManager() as tm:
        src = tm.create_temp_file(suffix=".pdf")
        out = tm.create_temp_file(suffix=".pdf")
        with open(src, "wb") as handle:
            handle.write(file_bytes)
        core_pages.apply_page_modifications(src, out, configs)
        with open(out, "rb") as handle:
            new_bytes = handle.read()
    set_active_document(new_bytes, file_name, push_history=True)


def _render_page_card(
    col,
    file_bytes: bytes,
    file_name: str,
    page_pos: int,
    orig_idx: int,
) -> None:
    order = st.session_state["pages_order"]
    rot = st.session_state["pages_rotation"].get(orig_idx, 0)
    thumb_bytes = get_cached_thumbnail_bytes(file_bytes, orig_idx)
    if not thumb_bytes:
        return

    img = Image.open(io.BytesIO(thumb_bytes))
    if rot != 0:
        img = img.rotate(-rot, expand=True)

    with col:
        st.image(img, use_container_width=True)
        st.caption(f"**Page {page_pos + 1}** (#{orig_idx + 1} | {rot}°)")
        b1, b2, b3, b4, b5 = st.columns(5)
        if b1.button("◀", key=f"mvL_{page_pos}", disabled=(page_pos == 0)):
            order[page_pos - 1], order[page_pos] = order[page_pos], order[page_pos - 1]
            st.rerun()
        if b2.button("↺", key=f"rotL_{page_pos}"):
            st.session_state["pages_rotation"][orig_idx] = (rot - 90) % 360
            st.rerun()
        if b3.button("↻", key=f"rotR_{page_pos}"):
            st.session_state["pages_rotation"][orig_idx] = (rot + 90) % 360
            st.rerun()
        if b4.button("▶", key=f"mvR_{page_pos}", disabled=(page_pos == len(order) - 1)):
            order[page_pos + 1], order[page_pos] = order[page_pos], order[page_pos + 1]
            st.rerun()
        if b5.button("🗑️", key=f"del_{page_pos}", disabled=(len(order) <= 1)):
            order.pop(page_pos)
            st.rerun()


def _rotate_all_pages(delta: int) -> None:
    for p in st.session_state["pages_order"]:
        cur = st.session_state["pages_rotation"].get(p, 0)
        st.session_state["pages_rotation"][p] = (cur + delta) % 360


def _render_batch_actions(file_bytes: bytes, file_name: str) -> None:
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("↺ Tout -90°", use_container_width=True):
        _rotate_all_pages(-90)
        st.rerun()
    if c2.button("↻ Tout +90°", use_container_width=True):
        _rotate_all_pages(90)
        st.rerun()
    if c3.button("✓ Appliquer au document", type="primary", use_container_width=True):
        _apply_page_changes_to_session(file_bytes, file_name)
        st.success("Ordre et rotations appliqués au document actif !")
        st.rerun()
    if c4.button("🔄 Réinitialiser", use_container_width=True):
        sync_page_order_for_bytes(file_bytes, reset=True)
        st.rerun()


def render_pages_tab(file_bytes: bytes, file_name: str) -> None:
    """Affiche l'organiseur de pages interactif Streamlit."""
    st.markdown('<div class="main-title">📑 Pages & Organisation</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Déplacez, pivotez ou supprimez des pages puis appliquez '
        'vos changements au document actif.</div>',
        unsafe_allow_html=True,
    )
    _render_batch_actions(file_bytes, file_name)
    st.divider()
    active_pages = st.session_state.get("pages_order", [])
    for start in range(0, len(active_pages), 4):
        cols = st.columns(4)
        for offset in range(4):
            pos = start + offset
            if pos < len(active_pages):
                _render_page_card(cols[offset], file_bytes, file_name, pos, active_pages[pos])
