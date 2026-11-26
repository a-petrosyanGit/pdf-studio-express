"""
tests/test_text_editor.py - Tests pour l'extraction et l'édition de texte.
"""

import os
import pymupdf as fitz

from core.fonts import calculate_fit_fontsize, get_font_kwargs
from core.models import SearchReplaceRequest, TextEditRequest
from core.text_editor import (
    get_page_text_elements,
    replace_text_element,
    search_and_replace_text,
)
import pdf_core


def test_get_page_text_elements(sample_vector_pdf):
    elements = get_page_text_elements(sample_vector_pdf, page_num=0)
    assert len(elements) >= 3

    texts = [e.text for e in elements]
    assert any("Rapport Annuel 2026" in t for t in texts)
    assert any("Avril 2026" in t for t in texts)

    first = elements[0]
    assert first.size > 0
    assert first.bbox[2] > first.bbox[0]
    assert not first.is_ocr


def test_calculate_fit_fontsize():
    font_kwargs = get_font_kwargs("Helvetica")
    short_size = calculate_fit_fontsize("Court", font_kwargs, 100.0, 14.0)
    assert short_size == 14.0

    long_text = (
        "Ceci est une très longue phrase qui dépasse largement la largeur cible"
    )
    fitted = calculate_fit_fontsize(long_text, font_kwargs, 100.0, 14.0, min_size=6.0)
    assert 6.0 <= fitted < 14.0


def test_replace_text_element_auto_fit_longer_text(sample_vector_pdf, test_temp_dir):
    elements = get_page_text_elements(sample_vector_pdf, page_num=0)
    target = next(e for e in elements if "Avril 2026" in e.text)

    out_pdf = os.path.join(test_temp_dir, "replaced_longer.pdf")
    req = TextEditRequest(
        page_num=0,
        elem_bbox=target.bbox,
        new_text="Novembre-Decembre 2026 Edition Exceptionnelle Spéciale",
        elem_origin=target.origin,
        font_name=target.font,
        font_size=target.size,
        font_flags=target.flags,
        font_color=target.color_rgb,
        auto_fit=True,
    )
    assert replace_text_element(sample_vector_pdf, out_pdf, req)

    doc = fitz.open(out_pdf)
    page_text = doc[0].get_text()
    assert "Avril 2026" not in page_text
    assert "Novembre-Decembre" in page_text
    doc.close()


def test_replace_text_element_shorter_text(sample_vector_pdf, test_temp_dir):
    elements = get_page_text_elements(sample_vector_pdf, page_num=0)
    target = next(e for e in elements if "Avril 2026" in e.text)

    out_pdf = os.path.join(test_temp_dir, "replaced_shorter.pdf")
    req = TextEditRequest(
        page_num=0,
        elem_bbox=target.bbox,
        new_text="Mai",
        elem_origin=target.origin,
        font_name=target.font,
        font_size=target.size,
        font_flags=target.flags,
        font_color=target.color_rgb,
    )
    assert replace_text_element(sample_vector_pdf, out_pdf, req)

    doc = fitz.open(out_pdf)
    page_text = doc[0].get_text()
    assert "Avril 2026" not in page_text
    assert "Mai" in page_text
    doc.close()


def test_search_and_replace_text_vector(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "search_replaced.pdf")
    req = SearchReplaceRequest(
        search_text="Avril", replace_text="Octobre", target_page=0
    )
    assert search_and_replace_text(sample_vector_pdf, out_pdf, req) == 1

    doc = fitz.open(out_pdf)
    p0_text = doc[0].get_text()
    assert "Octobre" in p0_text
    assert "Avril" not in p0_text
    doc.close()


def test_search_and_replace_not_found(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "search_not_found.pdf")
    req = SearchReplaceRequest(
        search_text="MotInexistant12345", replace_text="Nouveau", target_page=0
    )
    assert search_and_replace_text(sample_vector_pdf, out_pdf, req) == 0


def test_legacy_facade_compatibility(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "legacy_facade.pdf")
    count = pdf_core.search_and_replace_text_in_pdf(
        sample_vector_pdf,
        out_pdf,
        search_text="Avril",
        replace_text="Décembre",
        target_page=0,
    )
    assert count == 1
