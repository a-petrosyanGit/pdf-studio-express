"""
core - Package modulaire de traitement de documents PDF pour PDF Studio Express.
Architecture en couches et principes SOLID :
- models : Dataclasses typées
- temp_manager : Gestionnaire sécurisé de fichiers temporaires
- fonts : Résolution typographique multiplateforme et auto-ajustement
- ocr_engine : Détection OCR (RapidOCR) et échantillonnage de fond
- pages : Manipulation structurelle, miniatures, fusion, scission, filigranes
- text_editor : Remplacement et recherche de texte haute fidélité
- security : Chiffrement AES-256 et déverrouillage
- optimization : Compression Flate et extraction textuelle
- session : Gestionnaire d'état et d'historique partagé
"""

from core.models import (
    PDFMetadata,
    PageConfig,
    TextElement,
    WatermarkConfig,
    PageNumberConfig,
    OptimizationStats,
)
from core.temp_manager import SessionTempManager, default_temp_manager
from core.fonts import (
    get_font_kwargs,
    calculate_fit_fontsize,
    measure_text_length,
    int_to_rgb,
    rgb_to_hex,
    hex_to_rgb,
)
from core.ocr_engine import (
    get_ocr_engine,
    sample_background_color,
    run_ocr_on_page,
    is_page_scanned,
)
from core.pages import (
    get_pdf_metadata,
    render_page_thumbnail,
    render_all_thumbnails,
    apply_page_modifications,
    merge_pdfs,
    split_pdf_by_range,
    split_pdf_all_pages,
    split_pdf_every_n_pages,
    add_watermark_and_numbering,
    pdf_to_images,
    images_to_pdf,
    parse_page_ranges,
)
from core.text_editor import (
    get_page_text_elements,
    replace_text_element,
    search_and_replace_text,
)
from core.security import (
    protect_pdf,
    unlock_pdf,
    verify_pdf_password,
)
from core.optimization import (
    compress_pdf,
    extract_text_from_pdf,
)
from core.session import DocumentSession

__all__ = [
    "PDFMetadata",
    "PageConfig",
    "TextElement",
    "WatermarkConfig",
    "PageNumberConfig",
    "OptimizationStats",
    "SessionTempManager",
    "default_temp_manager",
    "get_font_kwargs",
    "calculate_fit_fontsize",
    "int_to_rgb",
    "rgb_to_hex",
    "hex_to_rgb",
    "get_ocr_engine",
    "sample_background_color",
    "run_ocr_on_page",
    "is_page_scanned",
    "get_pdf_metadata",
    "render_page_thumbnail",
    "render_all_thumbnails",
    "apply_page_modifications",
    "merge_pdfs",
    "split_pdf_by_range",
    "split_pdf_all_pages",
    "split_pdf_every_n_pages",
    "add_watermark_and_numbering",
    "pdf_to_images",
    "images_to_pdf",
    "parse_page_ranges",
    "get_page_text_elements",
    "replace_text_element",
    "search_and_replace_text",
    "protect_pdf",
    "unlock_pdf",
    "verify_pdf_password",
    "compress_pdf",
    "extract_text_from_pdf",
    "DocumentSession",
]
