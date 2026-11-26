"""
ui/web/text_tab.py - Éditeur de texte interactif Web (surlignage, filtre, OCR).
"""

import streamlit as st

from core import pages as core_pages, text_editor
from core.models import SearchReplaceRequest, TextEditRequest, TextElement
from core.temp_manager import SessionTempManager
from ui.web.state import (
    draw_highlight_box,
    get_cached_ocr,
    get_cached_page_preview,
    set_active_document,
)


def _execute_line_replace(
    tmp_path: str,
    file_name: str,
    cur_page: int,
    elem: TextElement,
) -> None:
    new_val = st.text_input("Nouveau texte :", value=elem.text, key=f"val_{cur_page}_{elem.id}")
    white_bg = st.checkbox("Masquage fond opaque", value=elem.is_ocr)
    if not st.button("✏️ Remplacer (Auto-ajusté)", type="primary"):
        return

    with SessionTempManager() as tm:
        out_p = tm.create_temp_file(suffix=".pdf")
        req = TextEditRequest(
            page_num=cur_page,
            elem_bbox=elem.bbox,
            new_text=new_val,
            elem_origin=elem.origin,
            font_name=elem.font,
            font_size=elem.size,
            font_flags=elem.flags,
            font_color=elem.color_rgb,
            use_white_bg=white_bg,
            is_ocr=elem.is_ocr,
            bg_color_rgb=elem.bg_color_rgb,
        )
        text_editor.replace_text_element(tmp_path, out_p, req)
        with open(out_p, "rb") as handle:
            set_active_document(handle.read(), file_name, push_history=True)
    st.success("Texte remplacé !")
    st.rerun()


def _render_single_edit_subtab(
    tmp_path: str,
    file_name: str,
    cur_page: int,
    elements: list,
) -> None:
    if not elements:
        st.session_state.pop("te_selected_bbox", None)
        st.info("Aucun texte détecté sur cette page.")
        return

    filter_q = st.text_input("🔎 Filtrer les lignes :", placeholder="Tapez un mot...").strip()
    filtered = [e for e in elements if not filter_q or filter_q.lower() in e.text.lower()]
    if not filtered:
        st.session_state.pop("te_selected_bbox", None)
        st.warning("Aucune ligne ne correspond à ce filtre.")
        return

    labels = [
        f"#{e.id + 1} : {e.text[:50]}..." if len(e.text) > 50 else f"#{e.id + 1} : {e.text}"
        for e in filtered
    ]
    idx = st.selectbox("Ligne à modifier :", range(len(labels)), format_func=lambda i: labels[i])
    elem = filtered[idx]
    st.session_state["te_selected_bbox"] = elem.bbox

    st.markdown(
        f'<div class="badge-font">✨ <b>{elem.font}</b> • {elem.size} pt • '
        f'<span style="color:{elem.color_hex};">■</span> {elem.color_hex}</div>',
        unsafe_allow_html=True,
    )
    _execute_line_replace(tmp_path, file_name, cur_page, elem)


def _render_search_replace_subtab(tmp_path: str, file_name: str, cur_page: int) -> None:
    s_find = st.text_input("Texte à rechercher :", placeholder="ex: Avril 2026")
    s_rep = st.text_input("Remplacer par :", placeholder="ex: Octobre 2026")
    scope = st.radio("Périmètre :", ["Cette page uniquement", "Tout le document"])

    if not st.button("🔍 Remplacer partout", type="primary"):
        return
    if not s_find.strip():
        st.warning("Saisissez le texte à rechercher.")
        return
    with SessionTempManager() as tm:
        out_p = tm.create_temp_file(suffix=".pdf")
        req = SearchReplaceRequest(
            search_text=s_find,
            replace_text=s_rep,
            target_page=cur_page if scope == "Cette page uniquement" else None,
        )
        cnt = text_editor.search_and_replace_text(tmp_path, out_p, req)
        if cnt > 0:
            with open(out_p, "rb") as handle:
                set_active_document(handle.read(), file_name, push_history=True)
            st.success(f"{cnt} occurrence(s) remplacée(s) !")
            st.rerun()
        else:
            st.info(f"« {s_find} » introuvable.")


def _render_preview_column(file_bytes: bytes, cur_page: int) -> None:
    st.subheader(f"Aperçu Page {cur_page + 1}")
    prev_png = get_cached_page_preview(file_bytes, cur_page)
    bbox = st.session_state.get("te_selected_bbox")
    if prev_png and bbox:
        prev_png = draw_highlight_box(prev_png, bbox)
    if prev_png:
        st.image(prev_png, use_container_width=True)


def render_text_tab(file_bytes: bytes, file_name: str) -> None:
    """Affiche l'éditeur de texte interactif avec prévisualisation surlignée."""
    st.markdown('<div class="main-title">✏️ Éditer le Texte Existant</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Remplacez du texte vectoriel ou scanné (OCR) '
        "tout en conservant fidèlement la police et l'alignement.</div>",
        unsafe_allow_html=True,
    )

    get_cached_ocr()
    with SessionTempManager() as tm:
        tmp_path = tm.create_temp_file(suffix=".pdf")
        with open(tmp_path, "wb") as handle:
            handle.write(file_bytes)
        total = max(1, core_pages.get_pdf_metadata(tmp_path).page_count)
        cur_page = st.number_input("Page à éditer :", min_value=1, max_value=total, value=1) - 1

        col_left, col_right = st.columns([1, 1])
        with col_right:
            force_ocr = st.checkbox("🔍 Forcer scan OCR (document numérisé)")
            elements = text_editor.get_page_text_elements(tmp_path, cur_page, force_ocr=force_ocr)
            t1, t2 = st.tabs(["📝 Modifier une ligne", "🔍 Rechercher & Remplacer"])
            with t1:
                _render_single_edit_subtab(tmp_path, file_name, cur_page, elements)
            with t2:
                _render_search_replace_subtab(tmp_path, file_name, cur_page)
        with col_left:
            _render_preview_column(file_bytes, cur_page)
