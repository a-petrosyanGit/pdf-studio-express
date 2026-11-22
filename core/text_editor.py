"""
core/text_editor.py - Moteur d'extraction, recherche et remplacement de texte haute fidélité.
Gère à la fois les documents vectoriels et scannés (OCR) avec auto-ajustement typographique
(auto-fitting) pour éviter tout chevauchement ou débordement lors des modifications.
"""

import os
import re
from typing import List, Tuple, Optional, Any, Dict
import fitz

from core.models import TextElement
from core.fonts import get_font_kwargs, int_to_rgb, rgb_to_hex, calculate_fit_fontsize
from core.ocr_engine import run_ocr_on_page, get_ocr_engine, sample_background_color


def get_page_text_elements(
    pdf_path: str,
    page_num: int,
    force_ocr: bool = False,
    dpi: int = 150
) -> List[TextElement]:
    """
    Extrait l'ensemble des éléments textuels de la page spécifiée.
    Pour les documents vectoriels, récupère police, style, taille, couleur et boîte englobante.
    Bascule automatiquement sur RapidOCR si aucun texte vectoriel n'est présent ou si force_ocr=True.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")

    doc = fitz.open(pdf_path)
    if page_num < 0 or page_num >= len(doc):
        doc.close()
        return []

    page = doc[page_num]
    elements: List[TextElement] = []
    elem_id = 0

    if not force_ocr:
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
                if not line_text:
                    continue

                spans = line.get("spans", [])
                s0 = spans[0] if spans else {}
                col_rgb = int_to_rgb(s0.get("color", 0))
                col_hex = rgb_to_hex(*col_rgb)
                bbox = tuple(line.get("bbox", (0.0, 0.0, 0.0, 0.0)))
                origin = tuple(s0.get("origin", (bbox[0], bbox[3] - 2)))

                elem = TextElement(
                    id=elem_id,
                    text=line_text,
                    font=s0.get("font", "Helvetica"),
                    size=round(s0.get("size", 12.0), 1),
                    flags=s0.get("flags", 0),
                    color_rgb=col_rgb,
                    color_hex=col_hex,
                    bbox=bbox,  # type: ignore
                    origin=origin,  # type: ignore
                    is_ocr=False
                )
                elements.append(elem)
                elem_id += 1

    # Bascule automatique OCR pour documents scannés / images
    if len(elements) == 0:
        elements = run_ocr_on_page(page, dpi=dpi)

    doc.close()
    return elements


def replace_text_element(
    pdf_path: str,
    output_path: str,
    page_num: int,
    elem_bbox: Tuple[float, float, float, float],
    new_text: str,
    elem_origin: Optional[Tuple[float, float]] = None,
    font_name: str = "Helvetica",
    font_size: float = 12.0,
    font_flags: int = 0,
    font_color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    use_white_bg: bool = False,
    is_ocr: bool = False,
    bg_color_rgb: Optional[Tuple[float, float, float]] = None,
    auto_fit: bool = True,
    min_font_size: float = 6.0
) -> bool:
    """
    Remplace un élément textuel ciblé par son rectangle englobant.
    Ajuste automatiquement la taille de police si le nouveau texte est plus long
    que l'espace d'origine pour éviter tout débordement.
    """
    doc = fitz.open(pdf_path)
    if page_num < 0 or page_num >= len(doc):
        doc.close()
        raise IndexError(f"Numéro de page invalide : {page_num}")

    page = doc[page_num]
    rect = fitz.Rect(elem_bbox)
    orig_width = max(1.0, rect.width)

    font_kwargs = get_font_kwargs(font_name, flags=font_flags)

    # 1. Calcul d'auto-ajustement de la taille de police si demandé
    final_font_size = font_size
    if auto_fit and new_text:
        final_font_size = calculate_fit_fontsize(
            text=new_text,
            font_kwargs=font_kwargs,
            target_width=orig_width,
            initial_size=font_size,
            min_size=min_font_size
        )

    # 2. Masquage / Rédaction de l'ancien texte
    if is_ocr or use_white_bg:
        fill_color = bg_color_rgb if (bg_color_rgb is not None) else (1.0, 1.0, 1.0)
        # Marge de sécurité de 1.5 pt
        pad_rect = fitz.Rect(rect.x0 - 1.5, rect.y0 - 1.5, rect.x1 + 1.5, rect.y1 + 1.5)
        page.draw_rect(pad_rect, color=fill_color, fill=fill_color)
    else:
        page.add_redact_annot(rect, fill=(1, 1, 1) if use_white_bg else None)
        page.apply_redactions()

    # 3. Positionnement précis de l'origine de base
    if elem_origin:
        origin = fitz.Point(elem_origin[0], elem_origin[1])
    else:
        origin = fitz.Point(rect.x0, rect.y1 - 2)

    # 4. Insertion du nouveau texte
    if new_text:
        page.insert_text(
            origin,
            new_text,
            fontsize=final_font_size,
            color=font_color,
            **font_kwargs
        )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return True


def search_and_replace_text(
    pdf_path: str,
    output_path: str,
    search_text: str,
    replace_text: str,
    target_page: Optional[int] = None,
    use_white_bg: bool = False,
    auto_fit: bool = True
) -> int:
    """
    Recherche et remplace toutes les occurrences d'une chaîne dans le document.
    Préserve police, taille et couleur natives.
    Bascule automatiquement sur RapidOCR si le document est scanné.
    """
    if not search_text.strip():
        raise ValueError("Le texte à rechercher ne peut pas être vide.")

    doc = fitz.open(pdf_path)
    total_replaced = 0
    pages = [doc[target_page]] if target_page is not None else list(doc)

    # Étape 1 : Remplacement vectoriel direct
    for page in pages:
        rects = page.search_for(search_text)
        if not rects:
            continue

        page_dict = page.get_text("dict")
        for r in rects:
            matched_span = None
            for b in page_dict.get("blocks", []):
                for l in b.get("lines", []):
                    for s in l.get("spans", []):
                        if fitz.Rect(s.get("bbox")).intersects(r):
                            matched_span = s
                            break
                    if matched_span:
                        break
                if matched_span:
                    break

            if matched_span:
                font_name = matched_span.get("font", "Helvetica")
                flags = matched_span.get("flags", 0)
                font_size = matched_span.get("size", 12.0)
                col_rgb = int_to_rgb(matched_span.get("color", 0))
                baseline_y = matched_span.get("origin", (r.x0, r.y1 - 2))[1]
            else:
                font_name = "Helvetica"
                flags = 0
                font_size = 12.0
                col_rgb = (0.0, 0.0, 0.0)
                baseline_y = r.y1 - 2

            font_kwargs = get_font_kwargs(font_name, flags=flags)
            orig_w = max(1.0, r.width)

            final_font_size = font_size
            if auto_fit and replace_text:
                final_font_size = calculate_fit_fontsize(
                    text=replace_text,
                    font_kwargs=font_kwargs,
                    target_width=orig_w,
                    initial_size=font_size
                )

            origin = fitz.Point(r.x0, baseline_y)

            if use_white_bg:
                page.add_redact_annot(r, fill=(1, 1, 1))
            else:
                page.add_redact_annot(r)
            page.apply_redactions()

            if replace_text:
                page.insert_text(origin, replace_text, fontsize=final_font_size, color=col_rgb, **font_kwargs)
            total_replaced += 1

    # Étape 2 : Bascule OCR si 0 occurrence vectorielle
    if total_replaced == 0:
        engine = get_ocr_engine()
        if engine:
            scale = 150 / 72.0
            search_lower = search_text.lower().strip()
            pattern = re.compile(re.escape(search_text), re.IGNORECASE)

            for page in pages:
                pix = page.get_pixmap(dpi=150)
                ocr_res, _ = engine(pix.tobytes("png"))
                if not ocr_res:
                    continue

                for box, ocr_txt, score in ocr_res:
                    if search_lower in ocr_txt.lower():
                        xs = [pt[0] for pt in box]
                        ys = [pt[1] for pt in box]
                        x0 = min(xs) / scale
                        y0 = min(ys) / scale
                        x1 = max(xs) / scale
                        y1 = max(ys) / scale
                        bbox = (x0, y0, x1, y1)

                        new_line_text = pattern.sub(replace_text, ocr_txt)

                        # Échantillonner la couleur du fond du scan
                        bg_rgb = sample_background_color(pix, bbox, dpi=150)

                        pad_rect = fitz.Rect(x0 - 2, y0 - 1.5, x1 + 2, y1 + 1.5)
                        page.draw_rect(pad_rect, color=bg_rgb, fill=bg_rgb)

                        h = y1 - y0
                        init_size = max(8.0, round(h * 0.75, 1))
                        font_kwargs = get_font_kwargs("Arial")

                        final_size = init_size
                        if auto_fit:
                            final_size = calculate_fit_fontsize(
                                new_line_text, font_kwargs, max(1.0, x1 - x0), init_size
                            )

                        origin = fitz.Point(x0, y1 - 2)
                        page.insert_text(origin, new_line_text, fontsize=final_size, color=(0.1, 0.1, 0.1), **font_kwargs)
                        total_replaced += 1

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return total_replaced
