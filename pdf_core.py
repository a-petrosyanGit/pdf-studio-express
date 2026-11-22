"""
pdf_core.py - Façade de rétrocompatibilité pour le moteur PDF Studio Express.
Ce module délègue toutes les opérations aux sous-modules spécialisés du package `core/` :
- core.models : Structures de données typées
- core.temp_manager : Gestion sécurisée des répertoires temporaires
- core.fonts : Découverte multi-plateforme des polices et auto-ajustement
- core.ocr_engine : Reconnaissance optique RapidOCR et échantillonnage de fond
- core.pages : Manipulation de pages, vignettes, filigranes et conversion d'images
- core.text_editor : Remplacement et recherche de texte haute fidélité
- core.security : Chiffrement AES-256 et déverrouillage
- core.optimization : Compression et extraction brute
- core.session : Gestion de session et historique Undo / Redo
"""

import os
import sys

# Assurer la découverte de 'core' quel que soit le répertoire d'exécution
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from typing import List, Dict, Tuple, Optional, Any
from PIL import Image

import core.models as models
import core.temp_manager as temp_manager
import core.fonts as fonts
import core.ocr_engine as ocr_engine
import core.pages as pages
import core.text_editor as text_editor
import core.security as security
import core.optimization as optimization
import core.session as session


# --- Export des fonctions et classes du nouveau cœur ---
from core import *


def get_ocr_engine():
    """Délègue l'accès au singleton OCR."""
    return ocr_engine.get_ocr_engine()


def get_font_kwargs(font_name: str, flags: int = 0) -> Dict[str, Any]:
    """Résolution multi-plateforme des polices."""
    return fonts.get_font_kwargs(font_name, flags=flags)


def int_to_rgb(col_int: int) -> Tuple[float, float, float]:
    return fonts.int_to_rgb(col_int)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return fonts.rgb_to_hex(r, g, b)


def get_pdf_info(pdf_path: str, password: str = "") -> Dict[str, Any]:
    """Retourne les métadonnées sous forme de dictionnaire pour compatibilité ascendante."""
    meta = pages.get_pdf_metadata(pdf_path, password=password)
    return {
        "is_encrypted": meta.is_encrypted,
        "page_count": meta.page_count,
        "size_bytes": meta.size_bytes,
        "title": meta.title,
        "author": meta.author,
        "is_scanned": meta.is_scanned
    }


def render_page_thumbnail(
    pdf_path: str,
    page_num: int,
    max_size: Tuple[int, int] = (160, 220),
    password: str = ""
) -> Image.Image:
    return pages.render_page_thumbnail(pdf_path, page_num, max_size=max_size, password=password)


def render_all_thumbnails(
    pdf_path: str,
    max_size: Tuple[int, int] = (160, 220),
    password: str = ""
) -> List[Image.Image]:
    return pages.render_all_thumbnails(pdf_path, max_size=max_size, password=password)


def save_modified_pdf(
    source_pdf_path: str,
    output_path: str,
    page_configs: List[Dict[str, Any]],
    password: str = ""
) -> None:
    pages.apply_page_modifications(source_pdf_path, output_path, page_configs, password=password)


def merge_pdfs(file_paths: List[str], output_path: str) -> int:
    return pages.merge_pdfs(file_paths, output_path)


def parse_page_ranges(range_str: str, max_pages: int) -> List[int]:
    return pages.parse_page_ranges(range_str, max_pages)


def split_pdf_by_range(pdf_path: str, range_str: str, output_path: str) -> int:
    return pages.split_pdf_by_range(pdf_path, range_str, output_path)


def split_pdf_all_pages(pdf_path: str, output_folder: str, prefix: str = "page") -> List[str]:
    return pages.split_pdf_all_pages(pdf_path, output_folder, prefix=prefix)


def split_pdf_every_n_pages(pdf_path: str, output_folder: str, n: int = 2, prefix: str = "part") -> List[str]:
    return pages.split_pdf_every_n_pages(pdf_path, output_folder, n=n, prefix=prefix)


def add_watermark_and_numbering(
    pdf_path: str,
    output_path: str,
    watermark_text: str = "",
    watermark_color: Tuple[float, float, float] = (0.7, 0.7, 0.7),
    watermark_opacity: float = 0.35,
    watermark_size: int = 44,
    watermark_angle: int = 45,
    add_numbers: bool = False,
    number_format: str = "Page {page} / {total}",
    number_position: str = "bottom-center",
    number_size: int = 10,
    number_color: Tuple[float, float, float] = (0.4, 0.4, 0.4),
    pages_to_apply: Optional[List[int]] = None
) -> int:
    wm_config = None
    if watermark_text.strip():
        wm_config = models.WatermarkConfig(
            text=watermark_text,
            font_size=watermark_size,
            color_rgb=watermark_color,
            opacity=watermark_opacity,
            angle=watermark_angle,
            pages=pages_to_apply
        )

    num_config = None
    if add_numbers:
        num_config = models.PageNumberConfig(
            enabled=True,
            format_str=number_format,
            position=number_position,
            font_size=number_size,
            color_rgb=number_color,
            pages=pages_to_apply
        )

    return pages.add_watermark_and_numbering(pdf_path, output_path, wm_config, num_config)


def run_ocr_on_page(page, dpi: int = 150) -> List[Dict[str, Any]]:
    elements = ocr_engine.run_ocr_on_page(page, dpi=dpi)
    return [e.to_dict() for e in elements]


def get_page_text_elements(pdf_path: str, page_num: int, force_ocr: bool = False) -> List[Dict[str, Any]]:
    elements = text_editor.get_page_text_elements(pdf_path, page_num, force_ocr=force_ocr)
    return [e.to_dict() for e in elements]


def replace_text_element_in_pdf(
    pdf_path: str,
    output_path: str,
    page_num: int,
    elem_bbox: List[float],
    new_text: str,
    elem_origin: Optional[List[float]] = None,
    font_name: str = "Helvetica",
    font_size: float = 12.0,
    font_flags: int = 0,
    font_color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    use_white_bg: bool = False,
    is_ocr: bool = False
) -> bool:
    bbox_tuple = (elem_bbox[0], elem_bbox[1], elem_bbox[2], elem_bbox[3])
    origin_tuple = (elem_origin[0], elem_origin[1]) if elem_origin else None
    return text_editor.replace_text_element(
        pdf_path=pdf_path,
        output_path=output_path,
        page_num=page_num,
        elem_bbox=bbox_tuple,
        new_text=new_text,
        elem_origin=origin_tuple,
        font_name=font_name,
        font_size=font_size,
        font_flags=font_flags,
        font_color=font_color,
        use_white_bg=use_white_bg,
        is_ocr=is_ocr,
        auto_fit=True
    )


def search_and_replace_text_in_pdf(
    pdf_path: str,
    output_path: str,
    search_text: str,
    replace_text: str,
    target_page: Optional[int] = None,
    use_white_bg: bool = False
) -> int:
    return text_editor.search_and_replace_text(
        pdf_path=pdf_path,
        output_path=output_path,
        search_text=search_text,
        replace_text=replace_text,
        target_page=target_page,
        use_white_bg=use_white_bg,
        auto_fit=True
    )


def pdf_to_images(pdf_path: str, output_folder: str, fmt: str = "png", dpi: int = 150) -> List[str]:
    return pages.pdf_to_images(pdf_path, output_folder, fmt=fmt, dpi=dpi)


def images_to_pdf(image_paths: List[str], output_path: str) -> int:
    return pages.images_to_pdf(image_paths, output_path)


def compress_pdf(pdf_path: str, output_path: str) -> Tuple[int, int]:
    stats = optimization.compress_pdf(pdf_path, output_path)
    return stats.initial_bytes, stats.final_bytes


def protect_pdf(pdf_path: str, output_path: str, password: str) -> None:
    security.protect_pdf(pdf_path, output_path, password)


def unlock_pdf(pdf_path: str, output_path: str, password: str) -> bool:
    return security.unlock_pdf(pdf_path, output_path, password)


def extract_text_from_pdf(pdf_path: str, output_txt_path: Optional[str] = None) -> str:
    return optimization.extract_text_from_pdf(pdf_path, output_txt_path=output_txt_path)
