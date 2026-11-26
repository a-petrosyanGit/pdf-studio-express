"""
ui/web/assemble_tab.py - Fusion multi-PDF et découpage pour Streamlit.
"""

import io
import os
import zipfile
import streamlit as st

from core import pages as core_pages
from core.temp_manager import SessionTempManager


def _save_uploaded_pdfs(tm: SessionTempManager, files: list) -> list:
    paths = []
    for item in files:
        path = tm.create_temp_file(suffix=".pdf")
        with open(path, "wb") as handle:
            handle.write(item.read())
        paths.append(path)
    return paths


def render_merge_tab() -> None:
    """Affiche l'outil de fusion de plusieurs fichiers PDF."""
    st.markdown('<div class="main-title">➕ Fusionner plusieurs PDF</div>', unsafe_allow_html=True)
    files = st.file_uploader(
        "Sélectionnez au moins 2 PDF dans l'ordre souhaité :",
        type=["pdf"],
        accept_multiple_files=True,
    )
    if not files or len(files) < 2:
        st.info("Ajoutez au moins 2 fichiers PDF pour activer la fusion.")
        return

    for item in files:
        st.markdown(f"- **{item.name}** ({item.size / 1024:.1f} Ko)")
    if not st.button("🚀 Fusionner les PDF", type="primary"):
        return

    with SessionTempManager() as tm:
        paths = _save_uploaded_pdfs(tm, files)
        out_path = tm.create_temp_file(suffix=".pdf")
        total = core_pages.merge_pdfs(paths, out_path)
        with open(out_path, "rb") as handle:
            out_bytes = handle.read()

    st.success(f"Fusion réussie ({total} pages) !")
    st.download_button(
        "💾 Télécharger le PDF fusionné",
        data=out_bytes,
        file_name="fusion_complete.pdf",
        mime="application/pdf",
    )


def _render_range_split(
    tm: SessionTempManager, src: str, file_name: str, nb_pages: int
) -> None:
    rng = st.text_input("Plages :", value=f"1-{min(2, nb_pages)}")
    if not st.button("✂️ Extraire", type="primary"):
        return
    out = tm.create_temp_file(suffix=".pdf")
    cnt = core_pages.split_pdf_by_range(src, rng, out)
    with open(out, "rb") as handle:
        st.download_button(
            f"💾 Télécharger ({cnt} pages)",
            data=handle.read(),
            file_name=f"extrait_{file_name}",
            mime="application/pdf",
        )


def render_split_tab(file_bytes: bytes, file_name: str) -> None:
    """Affiche l'outil de découpage sur le document actif."""
    st.markdown('<div class="main-title">✂️ Découper / Scinder</div>', unsafe_allow_html=True)
    with SessionTempManager() as tm:
        src = tm.create_temp_file(suffix=".pdf")
        with open(src, "wb") as handle:
            handle.write(file_bytes)
        nb_pages = max(1, core_pages.get_pdf_metadata(src).page_count)
        st.info(f"Document actif : **{file_name}** ({nb_pages} pages)")
        mode = st.radio(
            "Méthode :",
            ["Plages précises (ex: 1-3, 5)", "Une page par PDF (ZIP)", "Blocs de N pages (ZIP)"],
        )
        if mode == "Plages précises (ex: 1-3, 5)":
            _render_range_split(tm, src, file_name, nb_pages)
        else:
            _render_zip_split(tm, src, file_name, nb_pages, mode)


def _render_zip_split(
    tm: SessionTempManager,
    src: str,
    file_name: str,
    nb_pages: int,
    mode: str,
) -> None:
    every_n = (
        st.number_input("Pages par bloc :", min_value=1, max_value=nb_pages, value=2)
        if "Blocs" in mode
        else 1
    )
    if st.button("✂️ Générer l'archive ZIP", type="primary"):
        out_dir = os.path.join(tm.session_dir, "split_out")
        created = (
            core_pages.split_pdf_all_pages(src, out_dir)
            if every_n == 1 and "page par PDF" in mode
            else core_pages.split_pdf_every_n_pages(src, out_dir, n=int(every_n))
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in created:
                zf.write(item, arcname=os.path.basename(item))
        st.download_button(
            f"💾 Télécharger ZIP ({len(created)} fichiers)",
            data=buf.getvalue(),
            file_name=f"decoupe_{os.path.splitext(file_name)[0]}.zip",
            mime="application/zip",
        )
