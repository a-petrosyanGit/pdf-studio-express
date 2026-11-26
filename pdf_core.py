"""
pdf_core.py - Façade de rétrocompatibilité pour le moteur PDF Studio Express.
Délègue les opérations aux sous-modules spécialisés du package `core/`.
"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

from core import (
    enhancements,
    fonts,
    ocr_engine,
    optimization,
    pages,
    security,
    text_editor,
)
from core.models import (
    PageNumberConfig,
    SearchReplaceRequest,
    TextEditRequest,
    WatermarkConfig,
)


def get_ocr_engine():
    return ocr_engine.get_ocr_engine()


def get_font_kwargs(font_name: str, flags: int = 0) -> Dict[str, Any]:
    return fonts.get_font_kwargs(font_name, flags=flags)


def int_to_rgb(col_int: int) -> Tuple[float, float, float]:
    return fonts.int_to_rgb(col_int)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return fonts.rgb_to_hex(r, g, b)


def get_pdf_info(pdf_path: str, password: str = "") -> Dict[str, Any]:
    meta = pages.get_pdf_metadata(pdf_path, password=password)
    return {
        "is_encrypted": meta.is_encrypted,
        "page_count": meta.page_count,
        "size_bytes": meta.size_bytes,
        "title": meta.title,
        "author": meta.author,
        "is_scanned": meta.is_scanned,
    }


def render_page_thumbnail(
    pdf_path: str,
    page_num: int,
    max_size: Tuple[int, int] = (160, 220),
    password: str = "",
) -> Image.Image:
    return pages.render_page_thumbnail(
        pdf_path, page_num, max_size=max_size, password=password
    )


def render_all_thumbnails(
    pdf_path: str,
    max_size: Tuple[int, int] = (160, 220),
    password: str = "",
) -> List[Image.Image]:
    return pages.render_all_thumbnails(pdf_path, max_size=max_size, password=password)


def save_modified_pdf(
    source_pdf_path: str,
    output_path: str,
    page_configs: List[Dict[str, Any]],
    password: str = "",
) -> None:
    pages.apply_page_modifications(
        source_pdf_path, output_path, page_configs, password=password
    )


def merge_pdfs(file_paths: List[str], output_path: str) -> int:
    return pages.merge_pdfs(file_paths, output_path)


def parse_page_ranges(range_str: str, max_pages: int) -> List[int]:
    return pages.parse_page_ranges(range_str, max_pages)


def split_pdf_by_range(pdf_path: str, range_str: str, output_path: str) -> int:
    return pages.split_pdf_by_range(pdf_path, range_str, output_path)


def split_pdf_all_pages(
    pdf_path: str,
    output_folder: str,
    prefix: str = "page",
) -> List[str]:
    return pages.split_pdf_all_pages(pdf_path, output_folder, prefix=prefix)


def split_pdf_every_n_pages(
    pdf_path: str,
    output_folder: str,
    n: int = 2,
    prefix: str = "part",
) -> List[str]:
    return pages.split_pdf_every_n_pages(pdf_path, output_folder, n=n, prefix=prefix)


def add_watermark_and_numbering(
    pdf_path: str,
    output_path: str,
    **kwargs: Any,
) -> int:
    """Façade compatible : accepte les anciens arguments nommés de filigrane/numérotation."""
    wm_text = kwargs.get("watermark_text", "")
    wm_cfg = (
        WatermarkConfig(
            text=wm_text,
            font_size=kwargs.get("watermark_size", 44),
            color_rgb=kwargs.get("watermark_color", (0.7, 0.7, 0.7)),
            opacity=kwargs.get("watermark_opacity", 0.35),
            angle=kwargs.get("watermark_angle", 45),
            pages=kwargs.get("pages_to_apply"),
        )
        if str(wm_text).strip()
        else None
    )
    num_cfg = (
        PageNumberConfig(
            enabled=True,
            format_str=kwargs.get("number_format", "Page {page} / {total}"),
            position=kwargs.get("number_position", "bottom-center"),
            font_size=kwargs.get("number_size", 10),
            color_rgb=kwargs.get("number_color", (0.4, 0.4, 0.4)),
            pages=kwargs.get("pages_to_apply"),
        )
        if kwargs.get("add_numbers", False)
        else None
    )
    return enhancements.add_watermark_and_numbering(pdf_path, output_path, wm_cfg, num_cfg)


def run_ocr_on_page(page: Any, dpi: int = 150) -> List[Dict[str, Any]]:
    return [e.to_dict() for e in ocr_engine.run_ocr_on_page(page, dpi=dpi)]


def get_page_text_elements(
    pdf_path: str,
    page_num: int,
    force_ocr: bool = False,
) -> List[Dict[str, Any]]:
    return [
        e.to_dict()
        for e in text_editor.get_page_text_elements(
            pdf_path, page_num, force_ocr=force_ocr
        )
    ]


def replace_text_element_in_pdf(
    pdf_path: str,
    output_path: str,
    **kwargs: Any,
) -> bool:
    """Façade compatible pour le remplacement d'un élément textuel."""
    bbox = kwargs["elem_bbox"]
    origin = kwargs.get("elem_origin")
    req = TextEditRequest(
        page_num=kwargs["page_num"],
        elem_bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
        new_text=kwargs["new_text"],
        elem_origin=(origin[0], origin[1]) if origin else None,
        font_name=kwargs.get("font_name", "Helvetica"),
        font_size=kwargs.get("font_size", 12.0),
        font_flags=kwargs.get("font_flags", 0),
        font_color=kwargs.get("font_color", (0.0, 0.0, 0.0)),
        use_white_bg=kwargs.get("use_white_bg", False),
        is_ocr=kwargs.get("is_ocr", False),
        auto_fit=kwargs.get("auto_fit", True),
    )
    return text_editor.replace_text_element(pdf_path, output_path, req)


def search_and_replace_text_in_pdf(
    pdf_path: str,
    output_path: str,
    search_text: str,
    replace_text: str,
    **kwargs: Any,
) -> int:
    """Façade compatible pour la recherche et remplacement."""
    req = SearchReplaceRequest(
        search_text=search_text,
        replace_text=replace_text,
        target_page=kwargs.get("target_page"),
        use_white_bg=kwargs.get("use_white_bg", False),
        auto_fit=kwargs.get("auto_fit", True),
    )
    return text_editor.search_and_replace_text(pdf_path, output_path, req)


def pdf_to_images(
    pdf_path: str,
    output_folder: str,
    fmt: str = "png",
    dpi: int = 150,
) -> List[str]:
    return enhancements.pdf_to_images(pdf_path, output_folder, fmt=fmt, dpi=dpi)


def images_to_pdf(image_paths: List[str], output_path: str) -> int:
    return enhancements.images_to_pdf(image_paths, output_path)


def compress_pdf(pdf_path: str, output_path: str) -> Tuple[int, int]:
    stats = optimization.compress_pdf(pdf_path, output_path)
    return stats.initial_bytes, stats.final_bytes


def protect_pdf(pdf_path: str, output_path: str, password: str) -> None:
    security.protect_pdf(pdf_path, output_path, password)


def unlock_pdf(pdf_path: str, output_path: str, password: str) -> bool:
    return security.unlock_pdf(pdf_path, output_path, password)


def extract_text_from_pdf(
    pdf_path: str,
    output_txt_path: Optional[str] = None,
) -> str:
    return optimization.extract_text_from_pdf(
        pdf_path, output_txt_path=output_txt_path
    )
