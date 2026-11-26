"""
app_web.py - Interface Web moderne et modulaire basée sur Streamlit.
Partage un document actif unique entre tous les outils avec mise en cache OCR/rendus.
"""

import os
import sys
import streamlit as st

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from ui.web.assemble_tab import render_merge_tab, render_split_tab
from ui.web.pages_tab import render_pages_tab
from ui.web.state import get_active_document, render_sidebar_document_widget
from ui.web.text_tab import render_text_tab
from ui.web.tools_tab import render_images_tab, render_security_tab, render_watermark_tab

st.set_page_config(
    page_title="PDF Studio Express - Éditeur PDF",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-title { font-size: 2.0rem; font-weight: 700; color: #1e293b; margin-bottom: 0.2rem; }
    .sub-title { font-size: 0.98rem; color: #64748b; margin-bottom: 1.2rem; }
    .stButton>button { border-radius: 8px; font-weight: 600; }
    .badge-font {
        background-color: #f1f5f9; border: 1px solid #cbd5e1;
        padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; color: #334155;
        margin-bottom: 8px;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("## ⚡ **PDF Studio**")
st.sidebar.caption("Éditeur PDF Simple • 100 % Hors-ligne")
st.sidebar.markdown("---")

_EXAMPLE_PDF = os.path.join(_CURRENT_DIR, "exemple_document.pdf")
render_sidebar_document_widget(_EXAMPLE_PDF)

st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Outils :",
    [
        "📑 Pages & Organisation",
        "✏️ Éditer le Texte",
        "➕ Fusionner des PDF",
        "✂️ Découper / Scinder",
        "🏷️ Filigrane & Numéros",
        "🖼️ Images ↔ PDF",
        "🔒 Sécurité & Taille",
    ],
)

file_bytes, file_name = get_active_document()

if menu == "➕ Fusionner des PDF":
    render_merge_tab()
elif not file_bytes:
    st.markdown('<div class="main-title">⚡ Bienvenue dans PDF Studio</div>', unsafe_allow_html=True)
    st.info(
        "👈 Commencez par **importer un PDF** ou cliquer sur **« Charger le document "
        "d'exemple »** dans le panneau à gauche. Vous pourrez ensuite passer d'un outil à "
        "l'autre sans jamais ré-importer votre fichier !"
    )
elif menu == "📑 Pages & Organisation":
    render_pages_tab(file_bytes, file_name)
elif menu == "✏️ Éditer le Texte":
    render_text_tab(file_bytes, file_name)
elif menu == "✂️ Découper / Scinder":
    render_split_tab(file_bytes, file_name)
elif menu == "🏷️ Filigrane & Numéros":
    render_watermark_tab(file_bytes, file_name)
elif menu == "🖼️ Images ↔ PDF":
    render_images_tab(file_bytes, file_name)
elif menu == "🔒 Sécurité & Taille":
    render_security_tab(file_bytes, file_name)
