"""
core/enhancements.py - Filigranes, numérotation des pages et conversions Images <-> PDF.
"""

import logging
import os
from typing import List, Optional
import pymupdf as fitz

from core.fonts import get_font_kwargs, measure_text_length
from core.models import PageNumberConfig, WatermarkConfig

logger = logging.getLogger(__name__)


def _apply_watermark_to_page(page: fitz.Page, cfg: WatermarkConfig) -> None:
    rect = page.rect
    center = fitz.Point(rect.width / 2, rect.height / 2)
    font_kwargs = get_font_kwargs(cfg.font_name, flags=16)
    text_len = measure_text_length(cfg.text, cfg.font_size, font_kwargs)
    text_point = fitz.Point(center.x - (text_len / 2), center.y)

    extra = {"morph": (center, fitz.Matrix(cfg.angle))} if cfg.angle != 0 else {}
    page.insert_text(
        text_point,
        cfg.text,
        fontsize=cfg.font_size,
        color=cfg.color_rgb,
        **extra,
        **font_kwargs,
    )


def _compute_number_point(
    rect: fitz.Rect,
    text_len: float,
    cfg: PageNumberConfig,
) -> fitz.Point:
    margin = 25.0
    pos_map = {
        "bottom-center": ((rect.width - text_len) / 2, rect.height - margin),
        "bottom-right": (rect.width - text_len - margin, rect.height - margin),
        "bottom-left": (margin, rect.height - margin),
        "top-center": ((rect.width - text_len) / 2, margin + cfg.font_size),
        "top-right": (rect.width - text_len - margin, margin + cfg.font_size),
    }
    x, y = pos_map.get(cfg.position, pos_map["bottom-center"])
    return fitz.Point(x, y)


def _apply_number_to_page(
    page: fitz.Page,
    page_idx: int,
    total: int,
    cfg: PageNumberConfig,
) -> None:
    page_str = cfg.format_str.replace("{page}", str(page_idx + 1)).replace(
        "{total}", str(total)
    )
    font_kwargs = get_font_kwargs("Arial")
    t_len = measure_text_length(page_str, cfg.font_size, font_kwargs)
    pos = _compute_number_point(page.rect, t_len, cfg)
    page.insert_text(
        pos,
        page_str,
        fontsize=cfg.font_size,
        color=cfg.color_rgb,
        **font_kwargs,
    )


def _resolve_target_pages(explicit_pages: Optional[List[int]], total: int) -> set:
    if explicit_pages is not None:
        return set(explicit_pages)
    return set(range(total))


def _apply_page_overlay(
    page: fitz.Page,
    idx: int,
    total: int,
    wm_cfg: Optional[WatermarkConfig],
    num_cfg: Optional[PageNumberConfig],
) -> bool:
    changed = False
    if wm_cfg and wm_cfg.text.strip():
        _apply_watermark_to_page(page, wm_cfg)
        changed = True
    if num_cfg and num_cfg.enabled:
        _apply_number_to_page(page, idx, total, num_cfg)
        changed = True
    return changed


def add_watermark_and_numbering(
    pdf_path: str,
    output_path: str,
    watermark_config: Optional[WatermarkConfig] = None,
    number_config: Optional[PageNumberConfig] = None,
) -> int:
    """Ajoute un filigrane textuel et/ou une numérotation des pages."""
    doc = fitz.open(pdf_path)
    try:
        total = len(doc)
        wm_pages = _resolve_target_pages(
            watermark_config.pages if watermark_config else None, total
        )
        num_pages = _resolve_target_pages(
            number_config.pages if number_config else None, total
        )
        modified_pages = 0
        for i in range(total):
            wm = watermark_config if i in wm_pages else None
            num = number_config if i in num_pages else None
            if _apply_page_overlay(doc[i], i, total, wm, num):
                modified_pages += 1

        doc.save(output_path, garbage=4, deflate=True)
        return modified_pages
    finally:
        doc.close()


def pdf_to_images(
    pdf_path: str,
    output_folder: str,
    fmt: str = "png",
    dpi: int = 150,
) -> List[str]:
    """Convertit toutes les pages d'un PDF en fichiers images haute définition."""
    os.makedirs(output_folder, exist_ok=True)
    doc = fitz.open(pdf_path)
    output_files: List[str] = []
    pad_len = max(2, len(str(len(doc))))
    try:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            out_path = os.path.join(
                output_folder,
                f"page_{str(i + 1).zfill(pad_len)}.{fmt.lower()}",
            )
            pix.save(out_path)
            output_files.append(out_path)
        return output_files
    finally:
        doc.close()


def _insert_image_page(doc: fitz.Document, img_path: str) -> bool:
    try:
        img_doc = fitz.open(img_path)
        pdfbytes = img_doc.convert_to_pdf()
        img_doc.close()
        img_pdf = fitz.open("pdf", pdfbytes)
        doc.insert_pdf(img_pdf)
        img_pdf.close()
        return True
    except Exception as exc:
        logger.warning("Conversion image ignorée (%s) : %s", img_path, exc)
        return False


def images_to_pdf(image_paths: List[str], output_path: str) -> int:
    """Assemble une liste d'images dans un document PDF."""
    if not image_paths:
        raise ValueError("Aucune image spécifiée.")

    doc = fitz.open()
    try:
        count = sum(
            1
            for path in image_paths
            if os.path.exists(path) and _insert_image_page(doc, path)
        )
        if count == 0:
            raise ValueError("Aucune image valide n'a pu être traitée.")
        doc.save(output_path, garbage=4, deflate=True)
        return count
    finally:
        doc.close()
