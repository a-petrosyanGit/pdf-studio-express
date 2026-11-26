"""
tests/test_pages.py - Tests unitaires pour les pages, miniatures et assemblages.
"""

import os
from PIL import Image
import pymupdf as fitz

from core.enhancements import (
    add_watermark_and_numbering,
    images_to_pdf,
    pdf_to_images,
)
from core.models import PageConfig, PageNumberConfig, WatermarkConfig
from core.pages import (
    apply_page_modifications,
    get_pdf_metadata,
    merge_pdfs,
    parse_page_ranges,
    render_all_thumbnails,
    render_page_thumbnail,
    split_pdf_all_pages,
    split_pdf_by_range,
    split_pdf_every_n_pages,
)


def test_get_pdf_metadata(sample_vector_pdf):
    meta = get_pdf_metadata(sample_vector_pdf)
    assert meta.page_count == 3
    assert meta.size_bytes > 0
    assert not meta.is_encrypted
    assert not meta.is_scanned


def test_render_thumbnails(sample_vector_pdf):
    thumb = render_page_thumbnail(sample_vector_pdf, page_num=0, max_size=(100, 150))
    assert isinstance(thumb, Image.Image)
    assert thumb.width <= 150
    assert thumb.height <= 200

    all_thumbs = render_all_thumbnails(sample_vector_pdf, max_size=(100, 150))
    assert len(all_thumbs) == 3


def test_apply_page_modifications_reorder_and_rotate(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "reordered.pdf")
    configs = [
        PageConfig(source_page=2, rotation=0),
        PageConfig(source_page=1, rotation=90),
        PageConfig(source_page=0, rotation=0),
    ]
    apply_page_modifications(sample_vector_pdf, out_pdf, configs)

    doc = fitz.open(out_pdf)
    assert len(doc) == 3
    assert doc[1].rotation == 90
    assert doc[0].rotation == 0
    assert "Conclusion" in doc[0].get_text()
    doc.close()


def test_apply_page_modifications_deletion(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "deleted.pdf")
    apply_page_modifications(sample_vector_pdf, out_pdf, [PageConfig(source_page=0)])

    doc = fitz.open(out_pdf)
    assert len(doc) == 1
    assert "Rapport Annuel" in doc[0].get_text()
    doc.close()


def test_merge_pdfs(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "merged.pdf")
    total = merge_pdfs([sample_vector_pdf, sample_vector_pdf], out_pdf)
    assert total == 6

    doc = fitz.open(out_pdf)
    assert len(doc) == 6
    doc.close()


def test_parse_page_ranges():
    assert parse_page_ranges("1-3, 5", max_pages=10) == [0, 1, 2, 4]
    assert parse_page_ranges("2, 2, 4-6", max_pages=10) == [1, 3, 4, 5]
    assert parse_page_ranges("10-15", max_pages=5) == []


def test_split_by_range(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "split_range.pdf")
    count = split_pdf_by_range(sample_vector_pdf, "1, 3", out_pdf)
    assert count == 2

    doc = fitz.open(out_pdf)
    assert len(doc) == 2
    assert "Rapport Annuel" in doc[0].get_text()
    assert "Conclusion" in doc[1].get_text()
    doc.close()


def test_split_all_pages(sample_vector_pdf, test_temp_dir):
    out_dir = os.path.join(test_temp_dir, "split_pages")
    files = split_pdf_all_pages(sample_vector_pdf, out_dir, prefix="test_page")
    assert len(files) == 3
    for path in files:
        assert os.path.exists(path)


def test_split_every_n_pages(sample_vector_pdf, test_temp_dir):
    out_dir = os.path.join(test_temp_dir, "split_n")
    files = split_pdf_every_n_pages(sample_vector_pdf, out_dir, n=2, prefix="bloc")
    assert len(files) == 2


def test_add_watermark_and_numbering(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "watermarked.pdf")
    wm_config = WatermarkConfig(text="CONFIDENTIEL", font_size=36, angle=45)
    num_config = PageNumberConfig(
        enabled=True, format_str="P. {page} / {total}", position="bottom-right"
    )

    modified = add_watermark_and_numbering(sample_vector_pdf, out_pdf, wm_config, num_config)
    assert modified == 3

    doc = fitz.open(out_pdf)
    assert "CONFIDENTIEL" in doc[0].get_text()
    assert "P. 1 / 3" in doc[0].get_text()
    doc.close()


def test_images_and_pdf_conversions(sample_vector_pdf, test_temp_dir):
    img_dir = os.path.join(test_temp_dir, "exported_imgs")
    created_imgs = pdf_to_images(sample_vector_pdf, img_dir, fmt="png", dpi=100)
    assert len(created_imgs) == 3

    rebuilt_pdf = os.path.join(test_temp_dir, "from_imgs.pdf")
    assert images_to_pdf(created_imgs, rebuilt_pdf) == 3

    doc = fitz.open(rebuilt_pdf)
    assert len(doc) == 3
    doc.close()
