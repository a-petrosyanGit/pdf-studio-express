"""
app_web.py - Interface Web moderne basée sur Streamlit pour PDF Studio Express.
Optimisée pour la vitesse avec mise en cache des ressources lourdes (OCR et rendus),
historique d'annulation (Undo) et gestion robuste de session.
"""

import os
import sys
import io
import tempfile
import zipfile
from typing import Tuple, List, Optional
import streamlit as st
from PIL import Image
import fitz

# Assurer la découverte des modules
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

import core
import pdf_core
from core.temp_manager import SessionTempManager

st.set_page_config(
    page_title="PDF Studio Express - Éditeur PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# CACHE STREAMLIT HAUTE PERFORMANCE
# -------------------------------------------------------------
@st.cache_resource
def get_cached_ocr_engine():
    """Initialise et conserve en cache le moteur RapidOCR entre les requêtes."""
    return core.get_ocr_engine()


@st.cache_data(max_entries=128)
def get_cached_thumbnail_bytes(pdf_bytes: bytes, page_idx: int, size: Tuple[int, int] = (180, 240)) -> bytes:
    """Génère et met en cache la miniature PNG d'une page spécifique."""
    doc = fitz.open("pdf", pdf_bytes)
    if page_idx < 0 or page_idx >= len(doc):
        doc.close()
        return b""
    page = doc[page_idx]
    scale_w = size[0] / max(page.rect.width, 1.0)
    scale_h = size[1] / max(page.rect.height, 1.0)
    scale = min(scale_w, scale_h, 2.0)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


@st.cache_data(max_entries=64)
def get_cached_page_preview(pdf_bytes: bytes, page_idx: int, dpi: int = 140) -> bytes:
    """Génère et met en cache le rendu haute netteté d'une page pour la lecture et édition."""
    doc = fitz.open("pdf", pdf_bytes)
    if page_idx < 0 or page_idx >= len(doc):
        doc.close()
        return b""
    pix = doc[page_idx].get_pixmap(dpi=dpi, alpha=False)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


# Style personnalisé CSS
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    .badge-font {
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# Barre latérale
st.sidebar.markdown("## ⚡ **PDF Studio**")
st.sidebar.caption("Éditeur PDF Simple & Complet")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation :",
    [
        "📑 Organiseur & Pages",
        "✏️ Modifier le Texte",
        "➕ Fusionner des PDF",
        "✂️ Découper / Scinder",
        "🏷️ Filigrane & Numérotation",
        "🖼️ Images & PDF",
        "🔒 Sécurité & Optimisation"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **Astuce** : Double interface disponible ! Raccourci **`Éditeur PDF`** (Desktop) sur votre Bureau Windows.")


# -------------------------------------------------------------
# 1. ORGANISEUR & PAGES
# -------------------------------------------------------------
if menu == "📑 Organiseur & Pages":
    st.markdown('<div class="main-title">📑 Organiseur Visuel de Pages</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Faites pivoter, supprimez et réorganisez les pages de votre document en direct.</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Choisissez un fichier PDF à modifier :", type=["pdf"], key="org_upload")

    file_bytes = None
    file_name = "document.pdf"

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        use_example = st.button("📄 Charger l'exemple")
    
    if use_example:
        example_path = os.path.join(os.path.dirname(__file__), "exemple_document.pdf")
        if os.path.exists(example_path):
            with open(example_path, "rb") as f:
                file_bytes = f.read()
            file_name = "exemple_document.pdf"
            st.session_state["org_file_bytes"] = file_bytes
            st.session_state["org_file_name"] = file_name
    elif uploaded_file is not None:
        file_bytes = uploaded_file.read()
        file_name = uploaded_file.name
        st.session_state["org_file_bytes"] = file_bytes
        st.session_state["org_file_name"] = file_name
    elif "org_file_bytes" in st.session_state:
        file_bytes = st.session_state["org_file_bytes"]
        file_name = st.session_state.get("org_file_name", "document.pdf")

    if file_bytes:
        tm = SessionTempManager()
        tmp_in_path = tm.create_temp_file(suffix=".pdf")
        with open(tmp_in_path, "wb") as f_tmp:
            f_tmp.write(file_bytes)

        try:
            info = pdf_core.get_pdf_info(tmp_in_path)
            total_pages = info["page_count"]
            st.success(f"Document chargé : **{file_name}** ({total_pages} pages)")

            if "pages_order" not in st.session_state or st.session_state.get("current_loaded") != file_name:
                st.session_state["pages_order"] = list(range(total_pages))
                st.session_state["pages_rotation"] = {i: 0 for i in range(total_pages)}
                st.session_state["current_loaded"] = file_name

            act_col1, act_col2, act_col3 = st.columns(3)
            with act_col1:
                if st.button("↺ Pivoter TOUT de -90°"):
                    for p in st.session_state["pages_order"]:
                        st.session_state["pages_rotation"][p] = (st.session_state["pages_rotation"][p] - 90) % 360
                    st.rerun()
            with act_col2:
                if st.button("↻ Pivoter TOUT de +90°"):
                    for p in st.session_state["pages_order"]:
                        st.session_state["pages_rotation"][p] = (st.session_state["pages_rotation"][p] + 90) % 360
                    st.rerun()
            with act_col3:
                if st.button("🔄 Réinitialiser l'ordre et rotations"):
                    st.session_state["pages_order"] = list(range(total_pages))
                    st.session_state["pages_rotation"] = {i: 0 for i in range(total_pages)}
                    st.rerun()

            st.write("---")
            active_pages = st.session_state["pages_order"]

            cols_per_row = 4
            for row_start in range(0, len(active_pages), cols_per_row):
                row_cols = st.columns(cols_per_row)
                for col_idx in range(cols_per_row):
                    page_pos = row_start + col_idx
                    if page_pos < len(active_pages):
                        orig_idx = active_pages[page_pos]
                        rot = st.session_state["pages_rotation"].get(orig_idx, 0)
                        
                        thumb_bytes = get_cached_thumbnail_bytes(file_bytes, orig_idx)
                        if thumb_bytes:
                            thumb_img = Image.open(io.BytesIO(thumb_bytes))
                            if rot != 0:
                                thumb_img = thumb_img.rotate(-rot, expand=True)

                            with row_cols[col_idx]:
                                st.image(thumb_img, use_container_width=True)
                                st.caption(f"**Page {page_pos + 1}** (Origine #{orig_idx + 1} | {rot}°)")
                                
                                c1, c2, c3 = st.columns(3)
                                with c1:
                                    if st.button("↺", key=f"rotL_{page_pos}", help="Tourner -90°"):
                                        st.session_state["pages_rotation"][orig_idx] = (rot - 90) % 360
                                        st.rerun()
                                with c2:
                                    if st.button("↻", key=f"rotR_{page_pos}", help="Tourner +90°"):
                                        st.session_state["pages_rotation"][orig_idx] = (rot + 90) % 360
                                        st.rerun()
                                with c3:
                                    if st.button("🗑️", key=f"del_{page_pos}", help="Supprimer cette page"):
                                        st.session_state["pages_order"].pop(page_pos)
                                        st.rerun()

            st.write("---")
            if st.session_state["pages_order"]:
                tmp_out_path = tm.create_temp_file(suffix=".pdf")
                configs = [
                    {"source_page": p, "rotation": st.session_state["pages_rotation"].get(p, 0)}
                    for p in st.session_state["pages_order"]
                ]
                pdf_core.save_modified_pdf(tmp_in_path, tmp_out_path, configs)

                with open(tmp_out_path, "rb") as f_out:
                    out_bytes = f_out.read()

                st.download_button(
                    label="💾 Télécharger le PDF modifié",
                    data=out_bytes,
                    file_name="modifie_" + file_name,
                    mime="application/pdf",
                    type="primary"
                )
        finally:
            tm.cleanup()


# -------------------------------------------------------------
# 2. MODIFIER LE TEXTE (MÊME POLICE & AUTO-AJUSTEMENT)
# -------------------------------------------------------------
elif menu == "✏️ Modifier le Texte":
    st.markdown('<div class="main-title">✏️ Modifier le Texte Existant (Même Police)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Changez n\'importe quelle phrase ou mot en conservant automatiquement la police d\'origine avec ajustement automatique de taille pour éviter les débordements.</div>', unsafe_allow_html=True)

    up_file = st.file_uploader("Fichier PDF contenant le texte à modifier :", type=["pdf"], key="te_uploader")
    
    file_bytes = None
    file_name = "document.pdf"

    if st.button("📄 Charger le document d'exemple", key="btn_te_ex"):
        example_path = os.path.join(os.path.dirname(__file__), "exemple_document.pdf")
        if os.path.exists(example_path):
            with open(example_path, "rb") as f:
                file_bytes = f.read()
            file_name = "exemple_document.pdf"
            st.session_state["te_file_bytes"] = file_bytes
            st.session_state["te_file_name"] = file_name
            st.session_state["te_history"] = []
    elif up_file is not None:
        file_bytes = up_file.read()
        file_name = up_file.name
        if st.session_state.get("te_current_file") != file_name:
            st.session_state["te_file_bytes"] = file_bytes
            st.session_state["te_file_name"] = file_name
            st.session_state["te_history"] = []
            st.session_state["te_current_file"] = file_name
    elif "te_file_bytes" in st.session_state:
        file_bytes = st.session_state["te_file_bytes"]
        file_name = st.session_state.get("te_file_name", "document.pdf")

    if file_bytes:
        # Bouton d'annulation (Undo)
        history = st.session_state.get("te_history", [])
        if history:
            if st.button(f"↩ Annuler la dernière modification ({len(history)} en historique)"):
                st.session_state["te_file_bytes"] = history.pop()
                st.session_state["te_history"] = history
                st.rerun()

        tm = SessionTempManager()
        tmp_path = tm.create_temp_file(suffix=".pdf")
        with open(tmp_path, "wb") as f_tmp:
            f_tmp.write(file_bytes)

        try:
            info = pdf_core.get_pdf_info(tmp_path)
            total = info["page_count"]
            st.success(f"Document actif : **{file_name}** ({total} pages)")

            cur_page = st.number_input("Sélectionnez la page à modifier :", min_value=1, max_value=total, value=1) - 1

            col_left, col_right = st.columns([1, 1])

            # Rendu visuel net mis en cache
            with col_left:
                st.subheader(f"Aperçu Page {cur_page + 1}")
                prev_bytes = get_cached_page_preview(file_bytes, cur_page)
                if prev_bytes:
                    st.image(prev_bytes, use_container_width=True)

            with col_right:
                t_sub1, t_sub2 = st.tabs(["📝 Modifier une ligne / phrase", "🔍 Rechercher & Remplacer"])

                with t_sub1:
                    force_ocr = st.checkbox("🔍 Forcer le mode OCR (Scan approfondi)", key="chk_f_ocr")
                    elements = pdf_core.get_page_text_elements(tmp_path, cur_page, force_ocr=force_ocr)
                    if not elements:
                        st.info("Aucun texte détecté sur cette page.")
                    else:
                        options = [f"#{e['id'] + 1} : {e['text'][:55]}..." if len(e['text']) > 55 else f"#{e['id'] + 1} : {e['text']}" for e in elements]
                        sel_idx = st.selectbox("Choisissez le texte à modifier :", range(len(options)), format_func=lambda i: options[i])
                        sel_elem = elements[sel_idx]

                        st.markdown(f"""
                        <div class="badge-font">
                            ✨ <b>Police détectée :</b> {sel_elem['font']} &nbsp;|&nbsp; 
                            <b>Taille :</b> {sel_elem['size']} pt &nbsp;|&nbsp; 
                            <b>Couleur :</b> <span style="display:inline-block; width:10px; height:10px; background-color:{sel_elem['color_hex']}; border-radius:2px;"></span> {sel_elem['color_hex']}
                        </div>
                        """, unsafe_allow_html=True)

                        new_text_val = st.text_input("Nouveau texte :", value=sel_elem["text"])
                        use_white = st.checkbox("Masquage opaque (fond blanc/neutre)", value=sel_elem.get("is_ocr", False))

                        if st.button("✏️ Remplacer ce texte (Auto-ajusté)", type="primary"):
                            out_p = tm.create_temp_file(suffix=".pdf")
                            pdf_core.replace_text_element_in_pdf(
                                tmp_path,
                                out_p,
                                page_num=cur_page,
                                elem_bbox=sel_elem["bbox"],
                                new_text=new_text_val,
                                elem_origin=sel_elem["origin"],
                                font_name=sel_elem["font"],
                                font_size=sel_elem["size"],
                                font_flags=sel_elem.get("flags", 0),
                                font_color=sel_elem["color_rgb"],
                                use_white_bg=use_white,
                                is_ocr=sel_elem.get("is_ocr", False)
                            )

                            if "te_history" not in st.session_state:
                                st.session_state["te_history"] = []
                            st.session_state["te_history"].append(file_bytes)

                            with open(out_p, "rb") as rf:
                                st.session_state["te_file_bytes"] = rf.read()
                            st.success("Texte remplacé avec succès avec la même police !")
                            st.rerun()

                with t_sub2:
                    st.write("Recherchez un mot ou montant pour le remplacer automatiquement en conservant le style.")
                    s_find = st.text_input("Texte à rechercher :", placeholder="ex: Avril 2026")
                    s_rep = st.text_input("Remplacer par :", placeholder="ex: Octobre 2026")
                    s_scope = st.radio("Appliquer sur :", ["Cette page uniquement", "Tout le document"])

                    if st.button("🔍 Lancer le remplacement", type="primary"):
                        if not s_find.strip():
                            st.warning("Veuillez saisir le texte à rechercher.")
                        else:
                            out_p = tm.create_temp_file(suffix=".pdf")
                            target_p = cur_page if s_scope == "Cette page uniquement" else None
                            cnt = pdf_core.search_and_replace_text_in_pdf(
                                tmp_path,
                                out_p,
                                search_text=s_find,
                                replace_text=s_rep,
                                target_page=target_p
                            )

                            if cnt > 0:
                                if "te_history" not in st.session_state:
                                    st.session_state["te_history"] = []
                                st.session_state["te_history"].append(file_bytes)

                                with open(out_p, "rb") as rf:
                                    st.session_state["te_file_bytes"] = rf.read()
                                st.success(f"{cnt} occurrence(s) remplacée(s) avec succès avec la même police !")
                                st.rerun()
                            else:
                                st.info(f"Le texte '{s_find}' n'a pas été trouvé.")

                st.write("---")
                st.download_button(
                    label="💾 Télécharger le document avec les textes modifiés",
                    data=st.session_state["te_file_bytes"],
                    file_name="texte_modifie_" + file_name,
                    mime="application/pdf",
                    type="primary"
                )
        finally:
            tm.cleanup()


# -------------------------------------------------------------
# 3. FUSIONNER DES PDF
# -------------------------------------------------------------
elif menu == "➕ Fusionner des PDF":
    st.markdown('<div class="main-title">➕ Fusionner plusieurs PDF</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Combinez plusieurs fichiers PDF en un seul document complet.</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Sélectionnez les fichiers PDF à assembler :",
        type=["pdf"],
        accept_multiple_files=True
    )

    if uploaded_files and len(uploaded_files) >= 2:
        st.write(f"📁 **{len(uploaded_files)} fichiers sélectionnés :**")
        tm = SessionTempManager()
        temp_paths = []
        try:
            for f in uploaded_files:
                st.markdown(f"- **{f.name}** ({f.size / 1024:.1f} Ko)")
                p = tm.create_temp_file(suffix=".pdf")
                with open(p, "wb") as pf:
                    pf.write(f.read())
                temp_paths.append(p)

            if st.button("🚀 Fusionner les PDF", type="primary"):
                out_path = tm.create_temp_file(suffix=".pdf")
                total = pdf_core.merge_pdfs(temp_paths, out_path)
                st.success(f"Fusion réussie ! Document final contenant {total} pages.")

                with open(out_path, "rb") as out_f:
                    data = out_f.read()

                st.download_button(
                    label="💾 Télécharger le PDF fusionné",
                    data=data,
                    file_name="fusion_complete.pdf",
                    mime="application/pdf"
                )
        finally:
            tm.cleanup()
    elif uploaded_files:
        st.info("Veuillez sélectionner au moins 2 fichiers PDF pour effectuer une fusion.")


# -------------------------------------------------------------
# 4. DÉCOUPER / SCINDER
# -------------------------------------------------------------
elif menu == "✂️ Découper / Scinder":
    st.markdown('<div class="main-title">✂️ Découper / Scinder un PDF</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Extrayez des pages spécifiques ou découpez un document volumineux.</div>', unsafe_allow_html=True)

    up_file = st.file_uploader("Fichier PDF à découper :", type=["pdf"])
    if up_file:
        tm = SessionTempManager()
        tmp_path = tm.create_temp_file(suffix=".pdf")
        with open(tmp_path, "wb") as f_tmp:
            f_tmp.write(up_file.read())

        try:
            info = pdf_core.get_pdf_info(tmp_path)
            nb_pages = info["page_count"]
            st.info(f"Le fichier **{up_file.name}** contient **{nb_pages} pages**.")

            mode = st.radio(
                "Méthode de découpage :",
                [
                    "Extraire des plages précises (ex: 1-3, 5)",
                    "Découper chaque page dans un fichier séparé",
                    "Découper par blocs de N pages"
                ]
            )

            if mode == "Extraire des plages précises (ex: 1-3, 5)":
                range_str = st.text_input("Plage de pages à extraire :", value=f"1-{min(2, nb_pages)}")
                if st.button("✂️ Extraire ces pages", type="primary"):
                    out_p = tm.create_temp_file(suffix=".pdf")
                    cnt = pdf_core.split_pdf_by_range(tmp_path, range_str, out_p)
                    with open(out_p, "rb") as f:
                        d = f.read()
                    st.download_button(
                        f"💾 Télécharger les {cnt} pages extraites",
                        data=d,
                        file_name=f"extrait_{up_file.name}",
                        mime="application/pdf"
                    )

            elif mode == "Découper chaque page dans un fichier séparé":
                if st.button("✂️ Découper page par page (Archive ZIP)", type="primary"):
                    out_dir = os.path.join(tm.session_dir, "pages_split")
                    created = pdf_core.split_pdf_all_pages(tmp_path, out_dir, prefix="page")
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for cf in created:
                            zip_file.write(cf, arcname=os.path.basename(cf))
                    zip_buffer.seek(0)

                    st.download_button(
                        label=f"💾 Télécharger l'archive ZIP ({len(created)} fichiers PDF)",
                        data=zip_buffer.getvalue(),
                        file_name=f"pages_{os.path.splitext(up_file.name)[0]}.zip",
                        mime="application/zip"
                    )

            elif mode == "Découper par blocs de N pages":
                n_pages = st.number_input("Nombre de pages par bloc :", min_value=1, max_value=nb_pages, value=2)
                if st.button("✂️ Découper en blocs (Archive ZIP)", type="primary"):
                    out_dir = os.path.join(tm.session_dir, "blocs_split")
                    created = pdf_core.split_pdf_every_n_pages(tmp_path, out_dir, n=int(n_pages), prefix="partie")
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for cf in created:
                            zip_file.write(cf, arcname=os.path.basename(cf))
                    zip_buffer.seek(0)

                    st.download_button(
                        label=f"💾 Télécharger l'archive ZIP ({len(created)} parties)",
                        data=zip_buffer.getvalue(),
                        file_name=f"blocs_{os.path.splitext(up_file.name)[0]}.zip",
                        mime="application/zip"
                    )
        finally:
            tm.cleanup()


# -------------------------------------------------------------
# 5. FILIGRANE & NUMÉROTATION
# -------------------------------------------------------------
elif menu == "🏷️ Filigrane & Numérotation":
    st.markdown('<div class="main-title">🏷️ Filigrane & Numérotation</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Apposez un tampon personnalisé ou numérotez automatiquement vos pages.</div>', unsafe_allow_html=True)

    up_file = st.file_uploader("Fichier PDF cible :", type=["pdf"], key="wm_uploader")
    if up_file:
        tm = SessionTempManager()
        tmp_path = tm.create_temp_file(suffix=".pdf")
        with open(tmp_path, "wb") as f_tmp:
            f_tmp.write(up_file.read())

        try:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Filigrane Texte")
                wm_text = st.text_input("Texte du filigrane :", value="CONFIDENTIEL")
                st.caption("Exemples : CONFIDENTIEL, COPIE, BROUILLON, PAYÉ, ARCHIVE")
                wm_angle = st.selectbox("Angle de rotation :", [45, 0, 90, 315], index=0)
                wm_size = st.slider("Taille du texte :", 20, 80, 44)
                wm_color_name = st.selectbox("Couleur :", ["Gris", "Rouge", "Bleu", "Noir"])

            with col2:
                st.subheader("Numérotation des pages")
                add_num = st.checkbox("Ajouter la numérotation", value=True)
                num_fmt = st.selectbox("Format de numérotation :", ["Page {page} / {total}", "Page {page}", "{page} sur {total}", "{page}"])
                num_pos = st.selectbox("Position :", ["Bas - Centre", "Bas - Droite", "Bas - Gauche", "Haut - Droite", "Haut - Centre"])

            if st.button("🏷️ Appliquer le filigrane & la numérotation", type="primary"):
                col_map = {
                    "Gris": (0.7, 0.7, 0.7),
                    "Rouge": (0.85, 0.2, 0.2),
                    "Bleu": (0.2, 0.4, 0.85),
                    "Noir": (0.1, 0.1, 0.1)
                }
                pos_map = {
                    "Bas - Centre": "bottom-center",
                    "Bas - Droite": "bottom-right",
                    "Bas - Gauche": "bottom-left",
                    "Haut - Droite": "top-right",
                    "Haut - Centre": "top-center"
                }

                out_p = tm.create_temp_file(suffix=".pdf")
                pdf_core.add_watermark_and_numbering(
                    tmp_path,
                    out_p,
                    watermark_text=wm_text,
                    watermark_color=col_map[wm_color_name],
                    watermark_size=wm_size,
                    watermark_angle=wm_angle,
                    add_numbers=add_num,
                    number_format=num_fmt,
                    number_position=pos_map[num_pos]
                )

                with open(out_p, "rb") as f:
                    data = f.read()

                st.success("Filigrane et numérotation appliqués avec succès !")
                st.download_button(
                    label="💾 Télécharger le PDF résultat",
                    data=data,
                    file_name="tampon_" + up_file.name,
                    mime="application/pdf"
                )
        finally:
            tm.cleanup()


# -------------------------------------------------------------
# 6. IMAGES & PDF
# -------------------------------------------------------------
elif menu == "🖼️ Images & PDF":
    st.markdown('<div class="main-title">🖼️ Convertisseur Images & PDF</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Passez facilement de vos documents PDF à des images, et vice-versa.</div>', unsafe_allow_html=True)

    sub_tab1, sub_tab2 = st.tabs(["📄 PDF vers Images", "🖼️ Images vers PDF"])

    with sub_tab1:
        pdf_file = st.file_uploader("PDF à transformer en images :", type=["pdf"], key="p2i_up")
        if pdf_file:
            fmt = st.selectbox("Format d'image souhaité :", ["PNG", "JPEG"])
            dpi = st.select_slider("Qualité d'export (DPI) :", options=[100, 150, 200, 300], value=150)
            if st.button("🖼️ Exporter toutes les pages en images", type="primary"):
                tm = SessionTempManager()
                tmp_path = tm.create_temp_file(suffix=".pdf")
                with open(tmp_path, "wb") as f_tmp:
                    f_tmp.write(pdf_file.read())
                try:
                    out_dir = os.path.join(tm.session_dir, "images_out")
                    img_files = pdf_core.pdf_to_images(tmp_path, out_dir, fmt=fmt.lower(), dpi=dpi)
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for img_f in img_files:
                            zip_file.write(img_f, arcname=os.path.basename(img_f))
                    zip_buffer.seek(0)

                    st.success(f"{len(img_files)} images générées avec succès !")
                    st.download_button(
                        label=f"💾 Télécharger les images (Archive ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name=f"images_{os.path.splitext(pdf_file.name)[0]}.zip",
                        mime="application/zip"
                    )
                finally:
                    tm.cleanup()

    with sub_tab2:
        img_files = st.file_uploader(
            "Sélectionnez une ou plusieurs images à assembler en PDF :",
            type=["png", "jpg", "jpeg", "bmp", "webp"],
            accept_multiple_files=True
        )
        if img_files:
            st.write(f"📷 **{len(img_files)} image(s) sélectionnée(s)**")
            if st.button("📄 Créer le PDF", type="primary"):
                tm = SessionTempManager()
                tmp_imgs = []
                try:
                    for img_f in img_files:
                        ext = os.path.splitext(img_f.name)[1] or ".png"
                        p = tm.create_temp_file(suffix=ext)
                        with open(p, "wb") as pf:
                            pf.write(img_f.read())
                        tmp_imgs.append(p)

                    out_p = tm.create_temp_file(suffix=".pdf")
                    cnt = pdf_core.images_to_pdf(tmp_imgs, out_p)
                    with open(out_p, "rb") as f:
                        pdf_data = f.read()

                    st.success(f"PDF créé avec succès avec {cnt} image(s) !")
                    st.download_button(
                        label="💾 Télécharger le document PDF créé",
                        data=pdf_data,
                        file_name="images_assemblees.pdf",
                        mime="application/pdf"
                    )
                finally:
                    tm.cleanup()


# -------------------------------------------------------------
# 7. SÉCURITÉ & OPTIMISATION
# -------------------------------------------------------------
elif menu == "🔒 Sécurité & Optimisation":
    st.markdown('<div class="main-title">🔒 Sécurité & Optimisation</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Chiffrez, déverrouillez, réduisez la taille et extrayez le texte de vos PDF.</div>', unsafe_allow_html=True)

    sec_file = st.file_uploader("Fichier PDF cible :", type=["pdf"], key="sec_up")
    if sec_file:
        tm = SessionTempManager()
        tmp_path = tm.create_temp_file(suffix=".pdf")
        with open(tmp_path, "wb") as f_tmp:
            f_tmp.write(sec_file.read())

        try:
            col_sec1, col_sec2 = st.columns(2)

            with col_sec1:
                st.subheader("🔒 Verrouiller avec mot de passe (AES-256)")
                pw = st.text_input("Mot de passe souhaité :", type="password")
                if st.button("Chiffrer le PDF", type="primary"):
                    if not pw:
                        st.error("Veuillez saisir un mot de passe.")
                    else:
                        out_p = tm.create_temp_file(suffix=".pdf")
                        pdf_core.protect_pdf(tmp_path, out_p, pw)
                        with open(out_p, "rb") as f:
                            d = f.read()
                        st.success("PDF protégé par chiffrement AES-256 avec succès !")
                        st.download_button("💾 Télécharger le PDF protégé", data=d, file_name="protege_" + sec_file.name)

            with col_sec2:
                st.subheader("⚡ Compresser & Optimiser")
                if st.button("🗜️ Compresser le PDF"):
                    out_p = tm.create_temp_file(suffix=".pdf")
                    init_sz, fin_sz = pdf_core.compress_pdf(tmp_path, out_p)
                    gain = ((init_sz - fin_sz) / max(init_sz, 1)) * 100
                    with open(out_p, "rb") as f:
                        d = f.read()
                    st.success(f"Compression effectuée ! Gain : **{gain:.1f}%** ({init_sz/1024:.1f} Ko ➜ {fin_sz/1024:.1f} Ko)")
                    st.download_button("💾 Télécharger le PDF compressé", data=d, file_name="compresse_" + sec_file.name)

            st.write("---")
            st.subheader("📝 Extraire tout le texte")
            if st.button("Extraire le texte en .txt"):
                txt = pdf_core.extract_text_from_pdf(tmp_path)
                st.text_area("Aperçu du texte extrait :", value=txt[:2000] + ("..." if len(txt) > 2000 else ""), height=200)
                st.download_button(
                    label="💾 Télécharger le fichier texte (.txt)",
                    data=txt.encode("utf-8"),
                    file_name=os.path.splitext(sec_file.name)[0] + "_texte.txt",
                    mime="text/plain"
                )
        finally:
            tm.cleanup()
