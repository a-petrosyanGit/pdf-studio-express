"""
tests/test_ocr.py - Tests unitaires pour la détection OCR et masquage intelligent.
"""

import os
import pymupdf as fitz

from core.models import SearchReplaceRequest
from core.ocr_engine import (
    get_ocr_engine,
    is_page_scanned,
    sample_background_color,
)
from core.text_editor import get_page_text_elements, search_and_replace_text


def test_ocr_engine_initialization():
    assert get_ocr_engine() is not None


def test_is_page_scanned(sample_scanned_pdf, sample_vector_pdf):
    doc_scanned = fitz.open(sample_scanned_pdf)
    assert is_page_scanned(doc_scanned[0])
    doc_scanned.close()

    doc_vector = fitz.open(sample_vector_pdf)
    assert not is_page_scanned(doc_vector[0])
    doc_vector.close()


def test_sample_background_color(sample_scanned_pdf):
    doc = fitz.open(sample_scanned_pdf)
    pix = doc[0].get_pixmap(dpi=150)
    bg_rgb = sample_background_color(pix, (50, 50, 150, 80), dpi=150)
    doc.close()

    assert len(bg_rgb) == 3
    assert 0.90 <= bg_rgb[0] <= 1.0
    assert 0.90 <= bg_rgb[1] <= 1.0


def test_ocr_text_detection_on_scanned_pdf(sample_scanned_pdf):
    elements = get_page_text_elements(sample_scanned_pdf, page_num=0)
    assert len(elements) > 0
    assert all(e.is_ocr for e in elements)

    texts = " ".join(e.text for e in elements)
    assert any(
        kw in texts for kw in ("FACTURE", "98765", "1250", "TTC", "EUR", "Statut")
    )


def test_ocr_search_and_replace_on_scanned_pdf(sample_scanned_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "scanned_replaced.pdf")
    req = SearchReplaceRequest(
        search_text="FACTURE", replace_text="DEVIS", target_page=0
    )
    assert search_and_replace_text(sample_scanned_pdf, out_pdf, req) >= 1

    doc = fitz.open(out_pdf)
    assert "DEVIS" in doc[0].get_text()
    doc.close()
