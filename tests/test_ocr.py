"""
tests/test_ocr.py - Tests unitaires pour la détection OCR, documents scannés et masquage intelligent.
"""

import os
import pytest
import fitz

from core.ocr_engine import (
    get_ocr_engine,
    run_ocr_on_page,
    is_page_scanned,
    sample_background_color
)
from core.text_editor import (
    get_page_text_elements,
    replace_text_element,
    search_and_replace_text
)


def test_ocr_engine_initialization():
    engine = get_ocr_engine()
    assert engine is not None


def test_is_page_scanned(sample_scanned_pdf, sample_vector_pdf):
    doc_scanned = fitz.open(sample_scanned_pdf)
    assert is_page_scanned(doc_scanned[0])
    doc_scanned.close()

    doc_vector = fitz.open(sample_vector_pdf)
    assert not is_page_scanned(doc_vector[0])
    doc_vector.close()


def test_sample_background_color(sample_scanned_pdf):
    doc = fitz.open(sample_scanned_pdf)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    # L'image a été créée avec fond (245, 245, 240) -> RGB (0.96, 0.96, 0.94)
    bbox = (50, 50, 150, 80)
    bg_rgb = sample_background_color(pix, bbox, dpi=150)
    doc.close()

    assert len(bg_rgb) == 3
    # Vérifier que la couleur échantillonnée est proche du papier d'origine
    assert 0.90 <= bg_rgb[0] <= 1.0
    assert 0.90 <= bg_rgb[1] <= 1.0


def test_ocr_text_detection_on_scanned_pdf(sample_scanned_pdf):
    elements = get_page_text_elements(sample_scanned_pdf, page_num=0)
    assert len(elements) > 0
    assert all(e.is_ocr for e in elements)

    texts = " ".join(e.text for e in elements)
    # Le scan synthétique contient "FACTURE N° 98765" ou "1250 EUR"
    assert any(keyword in texts for keyword in ["FACTURE", "98765", "1250", "TTC", "EUR", "Statut"])


def test_ocr_search_and_replace_on_scanned_pdf(sample_scanned_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "scanned_replaced.pdf")
    # Tenter de remplacer "FACTURE" par "DEVIS" sur le document scanné
    replaced = search_and_replace_text(
        pdf_path=sample_scanned_pdf,
        output_path=out_pdf,
        search_text="FACTURE",
        replace_text="DEVIS",
        target_page=0
    )
    assert replaced >= 1

    # Vérifier que le document modifié contient désormais le nouveau texte inséré
    doc = fitz.open(out_pdf)
    text = doc[0].get_text()
    assert "DEVIS" in text
    doc.close()
