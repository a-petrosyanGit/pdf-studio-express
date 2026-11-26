"""
tests/test_ui_smoke.py - Tests d'intégration légers des modules UI et façade legacy.
"""

import os
import importlib


def test_gui_and_web_modules_import():
    modules = (
        "app_gui",
        "ui.theme",
        "ui.gui.async_runner",
        "ui.gui.base_view",
        "ui.gui.pages_view",
        "ui.gui.text_view",
        "ui.gui.assemble_view",
        "ui.gui.watermark_view",
        "ui.gui.tools_view",
        "ui.web.state",
        "ui.web.pages_tab",
        "ui.web.text_tab",
        "ui.web.assemble_tab",
        "ui.web.tools_tab",
    )
    for mod_name in modules:
        mod = importlib.import_module(mod_name)
        assert mod is not None


def test_legacy_facade_watermark_and_replace(sample_vector_pdf, test_temp_dir):
    import pdf_core

    wm_out = os.path.join(test_temp_dir, "legacy_wm.pdf")
    modified = pdf_core.add_watermark_and_numbering(
        sample_vector_pdf,
        wm_out,
        watermark_text="TEST",
        add_numbers=True,
    )
    assert modified == 3

    elems = pdf_core.get_page_text_elements(sample_vector_pdf, 0)
    target = next(e for e in elems if "Avril 2026" in e["text"])
    rep_out = os.path.join(test_temp_dir, "legacy_rep.pdf")
    ok = pdf_core.replace_text_element_in_pdf(
        sample_vector_pdf,
        rep_out,
        page_num=0,
        elem_bbox=target["bbox"],
        new_text="Juin 2026",
        elem_origin=target["origin"],
    )
    assert ok is True
