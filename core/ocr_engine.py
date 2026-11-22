"""
core/ocr_engine.py - Moteur de reconnaissance optique de caractères (OCR) et analyse de documents scannés.
Fournit une détection haute fidélité via RapidOCR et un échantillonnage intelligent
de la couleur de fond pour un masquage invisible des documents numérisés.
"""

from typing import List, Tuple, Optional, Any
import numpy as np
from PIL import Image
import fitz

from core.models import TextElement

# Instance unique paresseuse
_OCR_INSTANCE = None


def get_ocr_engine():
    """Initialise ou retourne l'instance unique de RapidOCR (singleton thread-safe basique)."""
    global _OCR_INSTANCE
    if _OCR_INSTANCE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _OCR_INSTANCE = RapidOCR()
        except ImportError:
            return None
        except Exception as e:
            print(f"[OCR] Avertissement initialisation RapidOCR: {e}")
            return None
    return _OCR_INSTANCE


def sample_background_color(pix: fitz.Pixmap, bbox_pts: Tuple[float, float, float, float], dpi: int = 150) -> Tuple[float, float, float]:
    """
    Échantillonne la couleur réelle du papier/fond sur le périmètre extérieur de la boîte englobante.
    Permet un masquage naturel sur les documents jaunis, grisâtres ou scannés avec grain.
    """
    scale = dpi / 72.0
    x0 = int(bbox_pts[0] * scale)
    y0 = int(bbox_pts[1] * scale)
    x1 = int(bbox_pts[2] * scale)
    y1 = int(bbox_pts[3] * scale)

    # Limites de l'image
    img_w, img_h = pix.width, pix.height
    samples: List[Tuple[int, int, int]] = []

    # Échantillonnage sur le périmètre extérieur (3 px d'écart)
    pad = 3
    coords_to_check = []
    
    # Bord supérieur et inférieur
    for x in range(max(0, x0 - pad), min(img_w - 1, x1 + pad), 2):
        if y0 - pad >= 0:
            coords_to_check.append((x, y0 - pad))
        if y1 + pad < img_h:
            coords_to_check.append((x, y1 + pad))
            
    # Bord gauche et droit
    for y in range(max(0, y0 - pad), min(img_h - 1, y1 + pad), 2):
        if x0 - pad >= 0:
            coords_to_check.append((x0 - pad, y))
        if x1 + pad < img_w:
            coords_to_check.append((x1 + pad, y))

    for x, y in coords_to_check:
        try:
            # fitz.Pixmap pixel(x, y) retourne (r, g, b) ou (r, g, b, a)
            p = pix.pixel(x, y)
            r, g, b = p[0], p[1], p[2]
            # Exclure les pixels trop sombres qui correspondent à des tracés d'encre voisins
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            if luminance > 120:  # Fond clair
                samples.append((r, g, b))
        except (IndexError, ValueError):
            continue

    if not samples:
        return (1.0, 1.0, 1.0)  # Blanc pur par défaut

    # Moyenne des canaux
    avg_r = sum(s[0] for s in samples) / (len(samples) * 255.0)
    avg_g = sum(s[1] for s in samples) / (len(samples) * 255.0)
    avg_b = sum(s[2] for s in samples) / (len(samples) * 255.0)
    return (round(avg_r, 3), round(avg_g, 3), round(avg_b, 3))


def run_ocr_on_page(page: fitz.Page, dpi: int = 150) -> List[TextElement]:
    """
    Exécute la reconnaissance optique de caractères (OCR) sur une page PDF (document scanné ou image),
    et renvoie les objets TextElement avec coordonnées adaptées à l'échelle du document.
    """
    engine = get_ocr_engine()
    if engine is None:
        return []

    scale = dpi / 72.0
    pix = page.get_pixmap(dpi=dpi)
    results, _ = engine(pix.tobytes("png"))
    if not results:
        return []

    elements: List[TextElement] = []
    for idx, (box, text, score) in enumerate(results):
        text_str = text.strip()
        if not text_str:
            continue

        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]

        x0 = min(xs) / scale
        y0 = min(ys) / scale
        x1 = max(xs) / scale
        y1 = max(ys) / scale
        h = y1 - y0

        font_size = max(8.0, round(h * 0.75, 1))
        bbox = (x0, y0, x1, y1)

        # Échantillonnage de la couleur réelle du papier
        bg_rgb = sample_background_color(pix, bbox, dpi=dpi)

        elem = TextElement(
            id=idx,
            text=text_str,
            font="Arial (Scanné)",
            size=font_size,
            flags=0,
            color_rgb=(0.1, 0.1, 0.1),
            color_hex="#1A1A1A",
            bbox=bbox,
            origin=(x0, y1 - 2),
            is_ocr=True,
            bg_color_rgb=bg_rgb
        )
        elements.append(elem)

    return elements


def is_page_scanned(page: fitz.Page) -> bool:
    """Détermine si une page contient principalement des images scannées sans couche de texte."""
    text = page.get_text().strip()
    if len(text) > 10:
        return False
    images = page.get_images()
    return len(images) > 0
