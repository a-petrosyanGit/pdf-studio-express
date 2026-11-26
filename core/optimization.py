"""
core/optimization.py - Compression Flate et extraction textuelle des PDF.
"""

import os
from typing import Optional
import pymupdf as fitz

from core.models import OptimizationStats
from core.ocr_engine import get_ocr_engine


def compress_pdf(pdf_path: str, output_path: str) -> OptimizationStats:
    """Optimise et compresse un document PDF (garbage=4, deflate, clean)."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")

    initial_size = os.path.getsize(pdf_path)
    doc = fitz.open(pdf_path)
    try:
        doc.save(output_path, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()

    final_size = os.path.getsize(output_path)
    return OptimizationStats(initial_bytes=initial_size, final_bytes=final_size)


def _extract_page_text(page: fitz.Page, use_ocr_fallback: bool) -> str:
    page_text = page.get_text()
    if page_text.strip() or not use_ocr_fallback:
        return page_text

    engine = get_ocr_engine()
    if engine is None:
        return page_text

    pix = page.get_pixmap(dpi=150)
    ocr_res, _ = engine(pix.tobytes("png"))
    if not ocr_res:
        return page_text
    return "\n".join(item[1] for item in ocr_res)


def extract_text_from_pdf(
    pdf_path: str,
    output_txt_path: Optional[str] = None,
    use_ocr_fallback: bool = True,
) -> str:
    """Extrait tout le texte d'un document PDF (avec repli OCR si scanné)."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        pages_text = [
            f"--- PAGE {i + 1} ---\n" + _extract_page_text(page, use_ocr_fallback)
            for i, page in enumerate(doc)
        ]
    finally:
        doc.close()

    result = "\n\n".join(pages_text)
    if output_txt_path:
        with open(output_txt_path, "w", encoding="utf-8") as handle:
            handle.write(result)
    return result
