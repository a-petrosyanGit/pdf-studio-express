"""
core/ocr_engine.py - Moteur OCR (RapidOCR) et analyse de documents scannés.
Inclut l'échantillonnage de la couleur réelle du papier pour un masquage invisible.
"""

import logging
from typing import List, Tuple
import pymupdf as fitz

from core.models import TextElement

logger = logging.getLogger(__name__)
_OCR_INSTANCE = None


def get_ocr_engine():
    """Initialise ou retourne l'instance unique de RapidOCR."""
    global _OCR_INSTANCE
    if _OCR_INSTANCE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR

            _OCR_INSTANCE = RapidOCR()
        except ImportError:
            logger.warning("rapidocr_onnxruntime introuvable ; OCR désactivé.")
            return None
        except Exception as exc:
            logger.warning("Initialisation RapidOCR impossible : %s", exc)
            return None
    return _OCR_INSTANCE


def _collect_perimeter_coords(
    bbox_px: Tuple[int, int, int, int],
    img_w: int,
    img_h: int,
    pad: int = 3,
) -> List[Tuple[int, int]]:
    x0, y0, x1, y1 = bbox_px
    coords: List[Tuple[int, int]] = []
    for x in range(max(0, x0 - pad), min(img_w - 1, x1 + pad), 2):
        if y0 - pad >= 0:
            coords.append((x, y0 - pad))
        if y1 + pad < img_h:
            coords.append((x, y1 + pad))
    for y in range(max(0, y0 - pad), min(img_h - 1, y1 + pad), 2):
        if x0 - pad >= 0:
            coords.append((x0 - pad, y))
        if x1 + pad < img_w:
            coords.append((x1 + pad, y))
    return coords


def _sample_light_pixels(
    pix: fitz.Pixmap,
    coords: List[Tuple[int, int]],
) -> List[Tuple[int, int, int]]:
    samples: List[Tuple[int, int, int]] = []
    for x, y in coords:
        if x < 0 or x >= pix.width or y < 0 or y >= pix.height:
            continue
        try:
            pixel = pix.pixel(x, y)
            r, g, b = pixel[0], pixel[1], pixel[2]
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            if luminance > 120:
                samples.append((r, g, b))
        except (IndexError, ValueError) as exc:
            logger.debug("Lecture pixel ignorée (%s, %s) : %s", x, y, exc)
    return samples


def sample_background_color(
    pix: fitz.Pixmap,
    bbox_pts: Tuple[float, float, float, float],
    dpi: int = 150,
) -> Tuple[float, float, float]:
    """Échantillonne la couleur du fond sur le périmètre extérieur du rectangle."""
    scale = dpi / 72.0
    bbox_px = (
        int(bbox_pts[0] * scale),
        int(bbox_pts[1] * scale),
        int(bbox_pts[2] * scale),
        int(bbox_pts[3] * scale),
    )
    coords = _collect_perimeter_coords(bbox_px, pix.width, pix.height)
    samples = _sample_light_pixels(pix, coords)

    if not samples:
        return (1.0, 1.0, 1.0)

    count = len(samples) * 255.0
    avg_r = sum(s[0] for s in samples) / count
    avg_g = sum(s[1] for s in samples) / count
    avg_b = sum(s[2] for s in samples) / count
    return (round(avg_r, 3), round(avg_g, 3), round(avg_b, 3))


def _ocr_box_to_element(
    idx: int,
    box: List[List[float]],
    text_str: str,
    pix: fitz.Pixmap,
    dpi: int,
) -> TextElement:
    scale = dpi / 72.0
    xs = [pt[0] for pt in box]
    ys = [pt[1] for pt in box]
    x0, y0 = min(xs) / scale, min(ys) / scale
    x1, y1 = max(xs) / scale, max(ys) / scale
    bbox = (x0, y0, x1, y1)
    bg_rgb = sample_background_color(pix, bbox, dpi=dpi)

    return TextElement(
        id=idx,
        text=text_str,
        font="Arial (Scanné)",
        size=max(8.0, round((y1 - y0) * 0.75, 1)),
        flags=0,
        color_rgb=(0.1, 0.1, 0.1),
        color_hex="#1A1A1A",
        bbox=bbox,
        origin=(x0, y1 - 2),
        is_ocr=True,
        bg_color_rgb=bg_rgb,
    )


def run_ocr_on_page(page: fitz.Page, dpi: int = 150) -> List[TextElement]:
    """Exécute RapidOCR sur une page PDF et renvoie les TextElement détectés."""
    engine = get_ocr_engine()
    if engine is None:
        return []

    pix = page.get_pixmap(dpi=dpi)
    results, _ = engine(pix.tobytes("png"))
    if not results:
        return []

    elements: List[TextElement] = []
    for idx, (box, text, _) in enumerate(results):
        text_str = text.strip()
        if text_str:
            elements.append(_ocr_box_to_element(idx, box, text_str, pix, dpi))
    return elements


def is_page_scanned(page: fitz.Page) -> bool:
    """Détermine si une page est principalement constituée d'images sans couche texte."""
    text = page.get_text().strip()
    if len(text) > 10:
        return False
    return len(page.get_images()) > 0
