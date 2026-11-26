"""
core/text_editor.py - Moteur d'extraction, recherche et remplacement de texte.
Supporte PDF vectoriels et scannés (OCR) avec auto-ajustement typographique.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz

from core.fonts import calculate_fit_fontsize, get_font_kwargs, int_to_rgb, rgb_to_hex
from core.models import SearchReplaceRequest, TextEditRequest, TextElement
from core.ocr_engine import get_ocr_engine, run_ocr_on_page, sample_background_color


def _line_to_text_element(elem_id: int, line: Dict[str, Any]) -> Optional[TextElement]:
    spans = line.get("spans", [])
    line_text = "".join(s.get("text", "") for s in spans).strip()
    if not line_text or not spans:
        return None

    s0 = spans[0]
    col_rgb = int_to_rgb(s0.get("color", 0))
    bbox = tuple(line.get("bbox", (0.0, 0.0, 0.0, 0.0)))
    origin = tuple(s0.get("origin", (bbox[0], bbox[3] - 2)))
    return TextElement(
        id=elem_id,
        text=line_text,
        font=s0.get("font", "Helvetica"),
        size=round(s0.get("size", 12.0), 1),
        flags=s0.get("flags", 0),
        color_rgb=col_rgb,
        color_hex=rgb_to_hex(*col_rgb),
        bbox=bbox,  # type: ignore[arg-type]
        origin=origin,  # type: ignore[arg-type]
        is_ocr=False,
    )


def _extract_vector_elements(page: fitz.Page) -> List[TextElement]:
    elements: List[TextElement] = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            elem = _line_to_text_element(len(elements), line)
            if elem is not None:
                elements.append(elem)
    return elements


def get_page_text_elements(
    pdf_path: str,
    page_num: int,
    force_ocr: bool = False,
    dpi: int = 150,
) -> List[TextElement]:
    """Extrait les éléments textuels de la page (vectoriel avec repli OCR)."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        if page_num < 0 or page_num >= len(doc):
            return []
        page = doc[page_num]
        elements = [] if force_ocr else _extract_vector_elements(page)
        return elements if elements else run_ocr_on_page(page, dpi=dpi)
    finally:
        doc.close()


def _mask_and_redact(
    page: fitz.Page,
    rect: fitz.Rect,
    req: TextEditRequest,
) -> None:
    if req.is_ocr or req.use_white_bg:
        fill_color = req.bg_color_rgb if req.bg_color_rgb is not None else (1.0, 1.0, 1.0)
        pad_rect = fitz.Rect(rect.x0 - 1.5, rect.y0 - 1.5, rect.x1 + 1.5, rect.y1 + 1.5)
        page.draw_rect(pad_rect, color=fill_color, fill=fill_color)
        return
    page.add_redact_annot(rect, fill=None)
    page.apply_redactions()


def replace_text_element(
    pdf_path: str,
    output_path: str,
    request: TextEditRequest,
) -> bool:
    """Remplace un élément textuel ciblé en ajustant la taille si nécessaire."""
    doc = fitz.open(pdf_path)
    try:
        if request.page_num < 0 or request.page_num >= len(doc):
            raise IndexError(f"Numéro de page invalide : {request.page_num}")

        page = doc[request.page_num]
        rect = fitz.Rect(request.elem_bbox)
        font_kwargs = get_font_kwargs(request.font_name, flags=request.font_flags)

        final_size = request.font_size
        if request.auto_fit and request.new_text:
            final_size = calculate_fit_fontsize(
                request.new_text,
                font_kwargs,
                max(1.0, rect.width),
                request.font_size,
                min_size=request.min_font_size,
            )

        _mask_and_redact(page, rect, request)
        origin = (
            fitz.Point(request.elem_origin[0], request.elem_origin[1])
            if request.elem_origin
            else fitz.Point(rect.x0, rect.y1 - 2)
        )
        if request.new_text:
            page.insert_text(
                origin,
                request.new_text,
                fontsize=final_size,
                color=request.font_color,
                **font_kwargs,
            )

        doc.save(output_path, garbage=4, deflate=True)
        return True
    finally:
        doc.close()


def _iter_spans(page_dict: Dict[str, Any]):
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                yield span


def _find_matching_span(
    page_dict: Dict[str, Any],
    rect: fitz.Rect,
) -> Optional[Dict[str, Any]]:
    return next(
        (s for s in _iter_spans(page_dict) if fitz.Rect(s.get("bbox")).intersects(rect)),
        None,
    )


def _style_from_span(
    span: Optional[Dict[str, Any]],
    rect: fitz.Rect,
) -> Tuple[str, int, float, Tuple[float, float, float], float]:
    if not span:
        return ("Helvetica", 0, 12.0, (0.0, 0.0, 0.0), rect.y1 - 2)
    return (
        span.get("font", "Helvetica"),
        span.get("flags", 0),
        span.get("size", 12.0),
        int_to_rgb(span.get("color", 0)),
        span.get("origin", (rect.x0, rect.y1 - 2))[1],
    )


def _replace_vector_on_page(page: fitz.Page, req: SearchReplaceRequest) -> int:
    rects = page.search_for(req.search_text)
    if not rects:
        return 0

    page_dict = page.get_text("dict")
    replaced = 0
    for rect in rects:
        span = _find_matching_span(page_dict, rect)
        font_name, flags, font_size, col_rgb, baseline_y = _style_from_span(span, rect)
        font_kwargs = get_font_kwargs(font_name, flags=flags)

        final_size = font_size
        if req.auto_fit and req.replace_text:
            final_size = calculate_fit_fontsize(
                req.replace_text, font_kwargs, max(1.0, rect.width), font_size
            )

        page.add_redact_annot(rect, fill=(1, 1, 1) if req.use_white_bg else None)
        page.apply_redactions()
        if req.replace_text:
            page.insert_text(
                fitz.Point(rect.x0, baseline_y),
                req.replace_text,
                fontsize=final_size,
                color=col_rgb,
                **font_kwargs,
            )
        replaced += 1
    return replaced


def _replace_ocr_match(
    page: fitz.Page,
    pix: fitz.Pixmap,
    box: List[List[float]],
    ocr_txt: str,
    req: SearchReplaceRequest,
) -> None:
    scale = 150 / 72.0
    xs = [pt[0] for pt in box]
    ys = [pt[1] for pt in box]
    x0, y0, x1, y1 = min(xs) / scale, min(ys) / scale, max(xs) / scale, max(ys) / scale
    pattern = re.compile(re.escape(req.search_text), re.IGNORECASE)
    new_line = pattern.sub(req.replace_text, ocr_txt)

    bg_rgb = sample_background_color(pix, (x0, y0, x1, y1), dpi=150)
    page.draw_rect(
        fitz.Rect(x0 - 2, y0 - 1.5, x1 + 2, y1 + 1.5),
        color=bg_rgb,
        fill=bg_rgb,
    )

    init_size = max(8.0, round((y1 - y0) * 0.75, 1))
    font_kwargs = get_font_kwargs("Arial")
    final_size = (
        calculate_fit_fontsize(new_line, font_kwargs, max(1.0, x1 - x0), init_size)
        if req.auto_fit
        else init_size
    )
    page.insert_text(
        fitz.Point(x0, y1 - 2),
        new_line,
        fontsize=final_size,
        color=(0.1, 0.1, 0.1),
        **font_kwargs,
    )


def _replace_ocr_on_pages(pages: List[fitz.Page], req: SearchReplaceRequest) -> int:
    engine = get_ocr_engine()
    if engine is None:
        return 0

    search_lower = req.search_text.lower().strip()
    total = 0
    for page in pages:
        pix = page.get_pixmap(dpi=150)
        ocr_res, _ = engine(pix.tobytes("png"))
        for box, ocr_txt, _ in ocr_res or []:
            if search_lower in ocr_txt.lower():
                _replace_ocr_match(page, pix, box, ocr_txt, req)
                total += 1
    return total


def search_and_replace_text(
    pdf_path: str,
    output_path: str,
    request: SearchReplaceRequest,
) -> int:
    """Recherche et remplace toutes les occurrences (vectoriel puis repli OCR)."""
    if not request.search_text.strip():
        raise ValueError("Le texte à rechercher ne peut pas être vide.")

    doc = fitz.open(pdf_path)
    try:
        pages = [doc[request.target_page]] if request.target_page is not None else list(doc)
        total = sum(_replace_vector_on_page(page, request) for page in pages)
        if total == 0:
            total = _replace_ocr_on_pages(pages, request)
        doc.save(output_path, garbage=4, deflate=True)
        return total
    finally:
        doc.close()
