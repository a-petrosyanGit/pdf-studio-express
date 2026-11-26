"""
ui/web/tools_tab.py - Filigrane, Images <-> PDF, Sécurité et Optimisation Web.
"""

import io
import os
import zipfile
import streamlit as st

from core import enhancements, optimization, security
from core.models import PageNumberConfig, WatermarkConfig
from core.temp_manager import SessionTempManager
from ui.web.state import set_active_document

_WM_COLORS = {
    "Gris": (0.7, 0.7, 0.7),
    "Rouge": (0.85, 0.2, 0.2),
    "Bleu": (0.2, 0.4, 0.85),
    "Noir": (0.1, 0.1, 0.1),
}

_NUM_POS = {
    "Bas - Centre": "bottom-center",
    "Bas - Droite": "bottom-right",
    "Bas - Gauche": "bottom-left",
    "Haut - Droite": "top-right",
    "Haut - Centre": "top-center",
}


def render_watermark_tab(file_bytes: bytes, file_name: str) -> None:
    """Affiche l'outil filigrane et numérotation appliqué au document actif."""
    st.markdown('<div class="main-title">🏷️ Filigrane & Numéros</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        wm_text = st.text_input("Filigrane :", value="CONFIDENTIEL")
        wm_angle = st.selectbox("Angle :", [45, 0, 90, 315])
        wm_size = st.slider("Taille :", 20, 80, 44)
        wm_color = st.selectbox("Couleur :", list(_WM_COLORS.keys()))
    with col2:
        add_num = st.checkbox("Numéroter les pages", value=True)
        num_fmt = st.selectbox(
            "Format :", ["Page {page} / {total}", "Page {page}", "{page} sur {total}"]
        )
        num_pos = st.selectbox("Position :", list(_NUM_POS.keys()))

    if st.button("🏷️ Appliquer au document actif", type="primary"):
        with SessionTempManager() as tm:
            src = tm.create_temp_file(suffix=".pdf")
            out = tm.create_temp_file(suffix=".pdf")
            with open(src, "wb") as handle:
                handle.write(file_bytes)
            wm_cfg = WatermarkConfig(
                text=wm_text,
                font_size=wm_size,
                color_rgb=_WM_COLORS[wm_color],
                angle=wm_angle,
            )
            num_cfg = PageNumberConfig(
                enabled=add_num,
                format_str=num_fmt,
                position=_NUM_POS[num_pos],
            )
            enhancements.add_watermark_and_numbering(src, out, wm_cfg, num_cfg)
            with open(out, "rb") as handle:
                set_active_document(handle.read(), file_name, push_history=True)
        st.success("Filigrane et numérotation appliqués !")
        st.rerun()


def _render_pdf_to_images_subtab(file_bytes: bytes, file_name: str) -> None:
    fmt = st.selectbox("Format :", ["PNG", "JPEG"])
    dpi = st.select_slider("DPI :", options=[100, 150, 200, 300], value=150)
    if not st.button("🖼️ Exporter en images (ZIP)", type="primary"):
        return

    with SessionTempManager() as tm:
        src = tm.create_temp_file(suffix=".pdf")
        with open(src, "wb") as handle:
            handle.write(file_bytes)
        out_dir = os.path.join(tm.session_dir, "imgs")
        imgs = enhancements.pdf_to_images(src, out_dir, fmt=fmt.lower(), dpi=dpi)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in imgs:
                zf.write(item, arcname=os.path.basename(item))
        st.download_button(
            f"💾 Télécharger ZIP ({len(imgs)} images)",
            data=buf.getvalue(),
            file_name=f"images_{os.path.splitext(file_name)[0]}.zip",
            mime="application/zip",
        )


def _render_images_to_pdf_subtab() -> None:
    uploads = st.file_uploader(
        "Images à assembler en PDF :",
        type=["png", "jpg", "jpeg", "bmp", "webp"],
        accept_multiple_files=True,
    )
    if not uploads or not st.button("📄 Créer le PDF", type="primary"):
        return

    with SessionTempManager() as tm:
        img_paths = []
        for item in uploads:
            ext = os.path.splitext(item.name)[1] or ".png"
            path = tm.create_temp_file(suffix=ext)
            with open(path, "wb") as handle:
                handle.write(item.read())
            img_paths.append(path)
        out_pdf = tm.create_temp_file(suffix=".pdf")
        enhancements.images_to_pdf(img_paths, out_pdf)
        with open(out_pdf, "rb") as handle:
            st.download_button(
                "💾 Télécharger le PDF créé",
                data=handle.read(),
                file_name="images_assemblees.pdf",
                mime="application/pdf",
            )


def render_images_tab(file_bytes: bytes, file_name: str) -> None:
    """Affiche les conversions PDF -> Images et Images -> PDF."""
    st.markdown('<div class="main-title">🖼️ Images ↔ PDF</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["📄 PDF actif vers Images", "🖼️ Images vers PDF"])
    with t1:
        _render_pdf_to_images_subtab(file_bytes, file_name)
    with t2:
        _render_images_to_pdf_subtab()


def _render_protect_column(src: str, file_name: str, tm: SessionTempManager) -> None:
    pw = st.text_input("Mot de passe (AES-256) :", type="password")
    if not st.button("🔒 Chiffrer le PDF", type="primary"):
        return
    if not pw:
        st.error("Saisissez un mot de passe.")
        return
    out = tm.create_temp_file(suffix=".pdf")
    security.protect_pdf(src, out, pw)
    with open(out, "rb") as handle:
        st.download_button(
            "💾 Télécharger PDF protégé",
            data=handle.read(),
            file_name=f"protege_{file_name}",
            mime="application/pdf",
        )


def _render_compress_column(src: str, file_name: str, tm: SessionTempManager) -> None:
    if not st.button("🗜️ Compresser le PDF"):
        return
    out = tm.create_temp_file(suffix=".pdf")
    stats = optimization.compress_pdf(src, out)
    with open(out, "rb") as handle:
        st.success(f"Gain : **{stats.reduction_percentage:.1f}%**")
        st.download_button(
            "💾 Télécharger PDF compressé",
            data=handle.read(),
            file_name=f"compresse_{file_name}",
            mime="application/pdf",
        )


def render_security_tab(file_bytes: bytes, file_name: str) -> None:
    """Affiche le chiffrement AES-256, compression et extraction texte."""
    st.markdown('<div class="main-title">🔒 Sécurité & Taille</div>', unsafe_allow_html=True)
    with SessionTempManager() as tm:
        src = tm.create_temp_file(suffix=".pdf")
        with open(src, "wb") as handle:
            handle.write(file_bytes)

        c1, c2 = st.columns(2)
        with c1:
            _render_protect_column(src, file_name, tm)
        with c2:
            _render_compress_column(src, file_name, tm)

        st.divider()
        if st.button("📝 Extraire le texte en .txt"):
            txt = optimization.extract_text_from_pdf(src)
            st.text_area("Aperçu :", value=txt[:2000], height=180)
            st.download_button(
                "💾 Télécharger .txt",
                data=txt.encode("utf-8"),
                file_name=f"{os.path.splitext(file_name)[0]}_texte.txt",
                mime="text/plain",
            )
