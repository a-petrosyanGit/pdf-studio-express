"""
tests/test_text_editor.py - Tests unitaires pour l'extraction et l'édition de texte (avec auto-ajustement).
"""

import os
import pytest
import fitz

from core.text_editor import (
    get_page_text_elements,
    replace_text_element,
    search_and_replace_text
)
from core.fonts import calculate_fit_fontsize, get_font_kwargs


def test_get_page_text_elements(sample_vector_pdf):
    elements = get_page_text_elements(sample_vector_pdf, page_num=0)
    assert len(elements) >= 3

    texts = [e.text for e in elements]
    assert any("Rapport Annuel 2026" in t for t in texts)
    assert any("Avril 2026" in t for t in texts)

    # Vérification des propriétés typographiques extraites
    first = elements[0]
    assert first.size > 0
    assert first.bbox[2] > first.bbox[0]
    assert not first.is_ocr


def test_calculate_fit_fontsize():
    font_kwargs = get_font_kwargs("Helvetica")
    target_width = 100.0
    initial_size = 14.0

    # Texte court : doit conserver initial_size
    short_size = calculate_fit_fontsize("Court", font_kwargs, target_width, initial_size)
    assert short_size == initial_size

    # Texte très long : doit réduire la taille
    long_text = "Ceci est une très longue phrase qui va obligatoirement dépasser la largeur cible"
    fitted_size = calculate_fit_fontsize(long_text, font_kwargs, target_width, initial_size, min_size=6.0)
    assert fitted_size < initial_size
    assert fitted_size >= 6.0


def test_replace_text_element_auto_fit_longer_text(sample_vector_pdf, test_temp_dir):
    elements = get_page_text_elements(sample_vector_pdf, page_num=0)
    target_elem = next(e for e in elements if "Avril 2026" in e.text)

    out_pdf = os.path.join(test_temp_dir, "replaced_longer.pdf")
    long_replacement = "Novembre-Decembre 2026 Edition Exceptionnelle Spéciale"

    success = replace_text_element(
        pdf_path=sample_vector_pdf,
        output_path=out_pdf,
        page_num=0,
        elem_bbox=target_elem.bbox,
        new_text=long_replacement,
        elem_origin=target_elem.origin,
        font_name=target_elem.font,
        font_size=target_elem.size,
        font_flags=target_elem.flags,
        font_color=target_elem.color_rgb,
        auto_fit=True
    )
    assert success

    doc = fitz.open(out_pdf)
    page_text = doc[0].get_text()
    assert "Avril 2026" not in page_text
    assert "Novembre-Decembre" in page_text
    doc.close()


def test_replace_text_element_shorter_text(sample_vector_pdf, test_temp_dir):
    elements = get_page_text_elements(sample_vector_pdf, page_num=0)
    target_elem = next(e for e in elements if "Avril 2026" in e.text)

    out_pdf = os.path.join(test_temp_dir, "replaced_shorter.pdf")
    short_replacement = "Mai"

    success = replace_text_element(
        pdf_path=sample_vector_pdf,
        output_path=out_pdf,
        page_num=0,
        elem_bbox=target_elem.bbox,
        new_text=short_replacement,
        elem_origin=target_elem.origin,
        font_name=target_elem.font,
        font_size=target_elem.size,
        font_flags=target_elem.flags,
        font_color=target_elem.color_rgb,
        auto_fit=True
    )
    assert success

    doc = fitz.open(out_pdf)
    page_text = doc[0].get_text()
    assert "Avril 2026" not in page_text
    assert "Mai" in page_text
    doc.close()


def test_search_and_replace_text_vector(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "search_replaced.pdf")
    replaced_count = search_and_replace_text(
        pdf_path=sample_vector_pdf,
        output_path=out_pdf,
        search_text="Avril",
        replace_text="Octobre",
        target_page=0
    )
    assert replaced_count == 1

    doc = fitz.open(out_pdf)
    p0_text = doc[0].get_text()
    assert "Octobre" in p0_text
    assert "Avril" not in p0_text
    doc.close()


def test_search_and_replace_not_found(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "search_not_found.pdf")
    replaced_count = search_and_replace_text(
        pdf_path=sample_vector_pdf,
        output_path=out_pdf,
        search_text="MotInexistant12345",
        replace_text="Nouveau",
        target_page=0
    )
    assert replaced_count == 0
