"""
core/optimization.py - Optimisation, compression et extraction textuelle des documents PDF.
Nettoie les objets orphelins, compresse les flux de données et exporte le texte brut.
"""

import os
from typing import Optional, Tuple
import fitz

from core.models import OptimizationStats
from core.ocr_engine import get_ocr_engine


def compress_pdf(pdf_path: str, output_path: str) -> OptimizationStats:
    """
    Optimise et compresse un document PDF en purgeant les objets inutilisés (garbage=4),
    en activant la compression Flate (deflate=True) et en nettoyant la syntaxe (clean=True).
    """
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


def extract_text_from_pdf(
    pdf_path: str,
    output_txt_path: Optional[str] = None,
    use_ocr_fallback: bool = True
) -> str:
    """
    Extrait l'intégralité du texte d'un document PDF.
    Si une page ne comporte aucun texte vectoriel et use_ocr_fallback=True,
    exécute l'OCR RapidOCR pour transcrire le document scanné.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")

    doc = fitz.open(pdf_path)
    full_text = []
    engine = None

    try:
        for i, page in enumerate(doc):
            page_text = page.get_text()
            if not page_text.strip() and use_ocr_fallback:
                if engine is None:
                    engine = get_ocr_engine()
                if engine:
                    pix = page.get_pixmap(dpi=150)
                    ocr_res, _ = engine(pix.tobytes("png"))
                    if ocr_res:
                        page_text = "\n".join(item[1] for item in ocr_res)

            full_text.append(f"--- PAGE {i + 1} ---\n" + page_text)
    finally:
        doc.close()

    result = "\n\n".join(full_text)
    if output_txt_path:
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(result)

    return result
