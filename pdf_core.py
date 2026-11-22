"""
pdf_core.py - Moteur de traitement PDF puissant et rapide basé sur PyMuPDF (fitz) et RapidOCR.
Fournit toutes les opérations de modification de PDF :
- Chargement et génération de miniatures (thumbnails)
- Réorganisation, rotation, suppression et insertion de pages
- Fusion de plusieurs PDF
- Découpage (par plage, page par page, par blocs)
- Ajout de filigrane texte personnalisé et numérotation des pages
- Modification et remplacement de texte (documents vectoriels ET scannés/images via OCR !)
- Conversion PDF <-> Images
- Chiffrement (mot de passe) et déverrouillage
- Compression / Optimisation
- Extraction de texte
"""

import os
import math
from typing import List, Dict, Tuple, Optional, Any
import fitz  # PyMuPDF
from PIL import Image, ImageTk

# Moteur OCR paresseux pour documents scannés / images
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception as e:
            print(f"Avertissement : impossible d'initialiser RapidOCR : {e}")
            return None
    return _ocr_engine


def get_font_kwargs(font_name: str, flags: int = 0) -> Dict[str, Any]:
    """
    Détermine le meilleur fichier de police Windows (.ttf) ou police Base14
    pour reproduire fidèlement la police originale (nom, gras, italique).
    """
    fn_lower = font_name.lower()
    is_bold = bool(flags & 16) or ("bold" in fn_lower) or ("gras" in fn_lower)
    is_italic = bool(flags & 2) or ("italic" in fn_lower) or ("oblique" in fn_lower)

    win_fonts = {
        "arial": ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/ariali.ttf"),
        "helvetica": ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/ariali.ttf"),
        "calibri": ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/calibrii.ttf"),
        "times": ("C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/timesbd.ttf", "C:/Windows/Fonts/timesi.ttf"),
        "segoe": ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/segoeuii.ttf"),
        "tahoma": ("C:/Windows/Fonts/tahoma.ttf", "C:/Windows/Fonts/tahomabd.ttf", None),
        "verdana": ("C:/Windows/Fonts/verdana.ttf", "C:/Windows/Fonts/verdanab.ttf", "C:/Windows/Fonts/verdanai.ttf"),
        "courier": ("C:/Windows/Fonts/cour.ttf", "C:/Windows/Fonts/courbd.ttf", "C:/Windows/Fonts/couri.ttf"),
        "consolas": ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/consolab.ttf", "C:/Windows/Fonts/consolai.ttf"),
    }

    for key, paths in win_fonts.items():
        if key in fn_lower:
            reg, bld, itl = paths
            target_path = reg
            if is_bold and bld and os.path.exists(bld):
                target_path = bld
            elif is_italic and itl and os.path.exists(itl):
                target_path = itl
            if target_path and os.path.exists(target_path):
                return {"fontfile": target_path}

    if os.path.exists("C:/Windows/Fonts/arial.ttf"):
        if is_bold and os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
            return {"fontfile": "C:/Windows/Fonts/arialbd.ttf"}
        return {"fontfile": "C:/Windows/Fonts/arial.ttf"}

    if "times" in fn_lower or "serif" in fn_lower or "roman" in fn_lower:
        return {"fontname": "tibo" if is_bold else "tiro"}
    elif "courier" in fn_lower or "mono" in fn_lower or "code" in fn_lower:
        return {"fontname": "cobi" if is_bold else "cour"}
    else:
        if is_bold and is_italic:
            return {"fontname": "hebi"}
        elif is_bold:
            return {"fontname": "hebo"}
        elif is_italic:
            return {"fontname": "heit"}
        else:
            return {"fontname": "helv"}


def int_to_rgb(col_int: int) -> Tuple[float, float, float]:
    """Convertit un entier sRGB en tuple RGB (0.0 à 1.0)."""
    r = ((col_int >> 16) & 255) / 255.0
    g = ((col_int >> 8) & 255) / 255.0
    b = (col_int & 255) / 255.0
    return (r, g, b)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convertit un tuple RGB (0.0-1.0) en code hexadécimal #RRGGBB."""
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


def get_pdf_info(pdf_path: str, password: str = "") -> Dict[str, Any]:
    """Récupère les métadonnées et le nombre de pages du PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Le fichier n'existe pas : {pdf_path}")
    
    doc = fitz.open(pdf_path)
    if doc.is_encrypted:
        if not password or not doc.authenticate(password):
            doc.close()
            return {"is_encrypted": True, "page_count": 0, "size_bytes": os.path.getsize(pdf_path)}
    
    info = {
        "is_encrypted": False,
        "page_count": len(doc),
        "size_bytes": os.path.getsize(pdf_path),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
    }
    doc.close()
    return info


def render_page_thumbnail(pdf_path: str, page_num: int, max_size: Tuple[int, int] = (160, 220), password: str = "") -> Image.Image:
    """Génère une miniature PIL Image d'une page spécifique."""
    doc = fitz.open(pdf_path)
    if doc.is_encrypted and password:
        doc.authenticate(password)
    
    if page_num < 0 or page_num >= len(doc):
        doc.close()
        raise IndexError(f"Numéro de page invalide : {page_num}")
    
    page = doc[page_num]
    rect = page.rect
    
    scale_w = max_size[0] / max(rect.width, 1)
    scale_h = max_size[1] / max(rect.height, 1)
    scale = min(scale_w, scale_h, 2.0)
    
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def render_all_thumbnails(pdf_path: str, max_size: Tuple[int, int] = (160, 220), password: str = "") -> List[Image.Image]:
    """Génère les miniatures de toutes les pages d'un PDF."""
    doc = fitz.open(pdf_path)
    if doc.is_encrypted and password:
        doc.authenticate(password)
    
    thumbnails = []
    for i in range(len(doc)):
        page = doc[i]
        rect = page.rect
        scale_w = max_size[0] / max(rect.width, 1)
        scale_h = max_size[1] / max(rect.height, 1)
        scale = min(scale_w, scale_h, 2.0)
        
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        thumbnails.append(img)
    
    doc.close()
    return thumbnails


def save_modified_pdf(source_pdf_path: str, output_path: str, page_configs: List[Dict[str, Any]], password: str = "") -> None:
    """Sauvegarde un PDF modifié (ordre, rotation, suppression)."""
    src_doc = fitz.open(source_pdf_path)
    if src_doc.is_encrypted and password:
        src_doc.authenticate(password)
    
    out_doc = fitz.open()
    for conf in page_configs:
        idx = conf["source_page"]
        rot = conf.get("rotation", 0) % 360
        
        out_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
        new_page_idx = len(out_doc) - 1
        
        if rot != 0:
            current_rot = out_doc[new_page_idx].rotation
            out_doc[new_page_idx].set_rotation((current_rot + rot) % 360)
            
    out_doc.save(output_path, garbage=4, deflate=True)
    out_doc.close()
    src_doc.close()


def merge_pdfs(file_paths: List[str], output_path: str) -> int:
    """Fusionne plusieurs fichiers PDF dans l'ordre de la liste."""
    if not file_paths:
        raise ValueError("Aucun fichier à fusionner.")
    
    out_doc = fitz.open()
    total_pages = 0
    for path in file_paths:
        if not os.path.exists(path):
            continue
        src = fitz.open(path)
        out_doc.insert_pdf(src)
        total_pages += len(src)
        src.close()
        
    out_doc.save(output_path, garbage=4, deflate=True)
    out_doc.close()
    return total_pages


def parse_page_ranges(range_str: str, max_pages: int) -> List[int]:
    """Convertit une chaîne comme '1-3, 5, 8-10' en liste d'indices 0-based."""
    pages_idx = []
    parts = [p.strip() for p in range_str.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            sub = part.split("-")
            if len(sub) == 2 and sub[0].isdigit() and sub[1].isdigit():
                start = max(1, int(sub[0]))
                end = min(max_pages, int(sub[1]))
                for p in range(start, end + 1):
                    if (p - 1) not in pages_idx:
                        pages_idx.append(p - 1)
        elif part.isdigit():
            p = int(part)
            if 1 <= p <= max_pages and (p - 1) not in pages_idx:
                pages_idx.append(p - 1)
    return pages_idx


def split_pdf_by_range(pdf_path: str, range_str: str, output_path: str) -> int:
    """Extrait les pages spécifiées par une plage (ex: '1-3, 5') dans un nouveau PDF."""
    doc = fitz.open(pdf_path)
    pages_idx = parse_page_ranges(range_str, len(doc))
    if not pages_idx:
        doc.close()
        raise ValueError("Aucune page valide sélectionnée dans la plage.")
    
    out_doc = fitz.open()
    for idx in pages_idx:
        out_doc.insert_pdf(doc, from_page=idx, to_page=idx)
        
    out_doc.save(output_path, garbage=4, deflate=True)
    out_doc.close()
    doc.close()
    return len(pages_idx)


def split_pdf_all_pages(pdf_path: str, output_folder: str, prefix: str = "page") -> List[str]:
    """Découpe un PDF en extrayant chaque page dans un fichier séparé."""
    doc = fitz.open(pdf_path)
    created_files = []
    pad_len = max(2, len(str(len(doc))))
    
    os.makedirs(output_folder, exist_ok=True)
    for i in range(len(doc)):
        out_doc = fitz.open()
        out_doc.insert_pdf(doc, from_page=i, to_page=i)
        filename = f"{prefix}_{str(i + 1).zfill(pad_len)}.pdf"
        out_path = os.path.join(output_folder, filename)
        out_doc.save(out_path, garbage=4, deflate=True)
        out_doc.close()
        created_files.append(out_path)
        
    doc.close()
    return created_files


def split_pdf_every_n_pages(pdf_path: str, output_folder: str, n: int = 2, prefix: str = "part") -> List[str]:
    """Découpe un PDF en paquets de N pages."""
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    created_files = []
    os.makedirs(output_folder, exist_ok=True)
    
    part_num = 1
    for start in range(0, total_pages, n):
        end = min(start + n - 1, total_pages - 1)
        out_doc = fitz.open()
        out_doc.insert_pdf(doc, from_page=start, to_page=end)
        filename = f"{prefix}_{part_num:02d}_pages_{start + 1}-{end + 1}.pdf"
        out_path = os.path.join(output_folder, filename)
        out_doc.save(out_path, garbage=4, deflate=True)
        out_doc.close()
        created_files.append(out_path)
        part_num += 1
        
    doc.close()
    return created_files


def add_watermark_and_numbering(
    pdf_path: str,
    output_path: str,
    watermark_text: str = "",
    watermark_color: Tuple[float, float, float] = (0.7, 0.7, 0.7),
    watermark_opacity: float = 0.35,
    watermark_size: int = 44,
    watermark_angle: int = 45,
    add_numbers: bool = False,
    number_format: str = "Page {page} / {total}",
    number_position: str = "bottom-center",
    number_size: int = 10,
    number_color: Tuple[float, float, float] = (0.4, 0.4, 0.4),
    pages_to_apply: Optional[List[int]] = None
) -> int:
    """Ajoute un filigrane textuel et/ou une numérotation des pages sur un PDF."""
    doc = fitz.open(pdf_path)
    total = len(doc)
    target_pages = pages_to_apply if pages_to_apply is not None else list(range(total))
    
    for i in target_pages:
        if i >= total:
            continue
        page = doc[i]
        rect = page.rect
        
        if watermark_text.strip():
            center = fitz.Point(rect.width / 2, rect.height / 2)
            text_len = fitz.get_text_length(watermark_text, fontsize=watermark_size)
            text_point = fitz.Point(center.x - (text_len / 2), center.y)
            
            font_kwargs = get_font_kwargs("Arial-Bold", flags=16)
            if watermark_angle != 0:
                mat = fitz.Matrix(watermark_angle)
                page.insert_text(
                    text_point,
                    watermark_text,
                    fontsize=watermark_size,
                    color=watermark_color,
                    morph=(center, mat),
                    **font_kwargs
                )
            else:
                page.insert_text(
                    text_point,
                    watermark_text,
                    fontsize=watermark_size,
                    color=watermark_color,
                    **font_kwargs
                )
                
        if add_numbers:
            page_str = number_format.replace("{page}", str(i + 1)).replace("{total}", str(total))
            t_len = fitz.get_text_length(page_str, fontsize=number_size)
            margin = 25
            
            if number_position == "bottom-center":
                pos = fitz.Point((rect.width - t_len) / 2, rect.height - margin)
            elif number_position == "bottom-right":
                pos = fitz.Point(rect.width - t_len - margin, rect.height - margin)
            elif number_position == "bottom-left":
                pos = fitz.Point(margin, rect.height - margin)
            elif number_position == "top-center":
                pos = fitz.Point((rect.width - t_len) / 2, margin + number_size)
            elif number_position == "top-right":
                pos = fitz.Point(rect.width - t_len - margin, margin + number_size)
            else:
                pos = fitz.Point((rect.width - t_len) / 2, rect.height - margin)
                
            page.insert_text(pos, page_str, fontsize=number_size, color=number_color, **get_font_kwargs("Arial"))
            
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return len(target_pages)


# -------------------------------------------------------------
# MODIFICATION ET REMPLACEMENT DE TEXTE (VECTORIEL & OCR SCANNÉ)
# -------------------------------------------------------------

def run_ocr_on_page(page: fitz.Page, dpi: int = 150) -> List[Dict[str, Any]]:
    """
    Exécute la reconnaissance optique de caractères (OCR) sur une page PDF (document scanné ou image),
    et renvoie les blocs de texte avec coordonnées précises adaptées à l'échelle du document.
    """
    engine = get_ocr_engine()
    if engine is None:
        return []

    scale = dpi / 72.0
    pix = page.get_pixmap(dpi=dpi)
    results, _ = engine(pix.tobytes("png"))
    if not results:
        return []

    elements = []
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

        elements.append({
            "id": idx,
            "text": text_str,
            "font": "Arial (Scanné)",
            "size": font_size,
            "flags": 0,
            "color_rgb": (0.1, 0.1, 0.1),
            "color_hex": "#1A1A1A",
            "bbox": [x0, y0, x1, y1],
            "origin": [x0, y1 - 2],
            "is_ocr": True
        })

    return elements


def get_page_text_elements(pdf_path: str, page_num: int, force_ocr: bool = False) -> List[Dict[str, Any]]:
    """
    Extrait tous les textes de la page spécifiée.
    Si le PDF est vectoriel, extrait les polices, tailles et couleurs natives.
    Si le document est scanné / image (0 texte vectoriel) ou si force_ocr=True,
    utilise automatiquement l'OCR haute précision !
    """
    doc = fitz.open(pdf_path)
    if page_num < 0 or page_num >= len(doc):
        doc.close()
        return []

    page = doc[page_num]
    elements = []
    elem_id = 0

    if not force_ocr:
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = "".join(s["text"] for s in line["spans"]).strip()
                if not line_text:
                    continue

                s0 = line["spans"][0]
                col_rgb = int_to_rgb(s0.get("color", 0))
                col_hex = rgb_to_hex(*col_rgb)

                elements.append({
                    "id": elem_id,
                    "text": line_text,
                    "font": s0.get("font", "Helvetica"),
                    "size": round(s0.get("size", 12.0), 1),
                    "flags": s0.get("flags", 0),
                    "color_rgb": col_rgb,
                    "color_hex": col_hex,
                    "bbox": list(line["bbox"]),
                    "origin": list(s0.get("origin", (line["bbox"][0], line["bbox"][3] - 2))),
                    "is_ocr": False
                })
                elem_id += 1

    # SI AUCUN TEXTE VECTORIEL DÉTECTÉ -> BASCULE AUTOMATIQUE SUR L'OCR (PDF SCANNÉ)
    if len(elements) == 0:
        elements = run_ocr_on_page(page)

    doc.close()
    return elements


def replace_text_element_in_pdf(
    pdf_path: str,
    output_path: str,
    page_num: int,
    elem_bbox: List[float],
    new_text: str,
    elem_origin: Optional[List[float]] = None,
    font_name: str = "Helvetica",
    font_size: float = 12.0,
    font_flags: int = 0,
    font_color: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    use_white_bg: bool = False,
    is_ocr: bool = False
) -> bool:
    """
    Remplace un élément de texte spécifique sur une page par un nouveau texte
    en conservant la même police, taille et couleur (vectoriel ou scanné).
    """
    doc = fitz.open(pdf_path)
    if page_num < 0 or page_num >= len(doc):
        doc.close()
        raise IndexError("Numéro de page invalide")

    page = doc[page_num]
    rect = fitz.Rect(elem_bbox)

    # Pour un document scanné ou si masque blanc demandé :
    # dessine un rectangle de masquage blanc opaque par-dessus l'image
    if is_ocr or use_white_bg:
        # Marge légère de 1 pt pour effacer parfaitement
        pad_rect = fitz.Rect(rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 1)
        page.draw_rect(pad_rect, color=(1, 1, 1), fill=(1, 1, 1))
    else:
        page.add_redact_annot(rect)
        page.apply_redactions()

    font_kwargs = get_font_kwargs(font_name, flags=font_flags)

    if elem_origin:
        origin = fitz.Point(elem_origin[0], elem_origin[1])
    else:
        origin = fitz.Point(rect.x0, rect.y1 - 2)

    page.insert_text(
        origin,
        new_text,
        fontsize=font_size,
        color=font_color,
        **font_kwargs
    )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return True


def search_and_replace_text_in_pdf(
    pdf_path: str,
    output_path: str,
    search_text: str,
    replace_text: str,
    target_page: Optional[int] = None,
    use_white_bg: bool = False
) -> int:
    """
    Recherche un texte et le remplace en conservant automatiquement la police et le style.
    Compatible avec les PDF vectoriels ET les PDF scannés / images via OCR automatique !
    """
    if not search_text.strip():
        raise ValueError("Le texte à rechercher ne peut pas être vide.")

    doc = fitz.open(pdf_path)
    total_replaced = 0
    pages = [doc[target_page]] if target_page is not None else list(doc)

    # 1. TENTATIVE VECTORIELLE
    for page in pages:
        rects = page.search_for(search_text)
        if not rects:
            continue

        d = page.get_text("dict")
        for r in rects:
            matched_span = None
            for b in d.get("blocks", []):
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            if fitz.Rect(s["bbox"]).intersects(r):
                                matched_span = s
                                break
                    if matched_span:
                        break

            if matched_span:
                font_name = matched_span.get("font", "Helvetica")
                flags = matched_span.get("flags", 0)
                font_size = matched_span.get("size", 12.0)
                col_rgb = int_to_rgb(matched_span.get("color", 0))
                baseline_y = matched_span["origin"][1]
            else:
                font_name = "Helvetica"
                flags = 0
                font_size = 12.0
                col_rgb = (0.0, 0.0, 0.0)
                baseline_y = r.y1 - 2

            font_kwargs = get_font_kwargs(font_name, flags=flags)
            origin = fitz.Point(r.x0, baseline_y)

            if use_white_bg:
                page.add_redact_annot(r, fill=(1, 1, 1))
            else:
                page.add_redact_annot(r)
            page.apply_redactions()

            page.insert_text(origin, replace_text, fontsize=font_size, color=col_rgb, **font_kwargs)
            total_replaced += 1

    # 2. SI 0 OCCURRENCE VECTORIELLE -> BASCULE SUR LA RECHERCHE OCR (DOCUMENTS SCANNÉS)
    if total_replaced == 0:
        engine = get_ocr_engine()
        if engine:
            scale = 150 / 72.0
            search_lower = search_text.lower().strip()

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
                        h = y1 - y0

                        # Remplacement dans la ligne scannée
                        import re
                        pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                        new_line_text = pattern.sub(replace_text, ocr_txt)

                        # Masquer l'ancien texte scanné avec un rectangle blanc
                        pad_rect = fitz.Rect(x0 - 2, y0 - 1, x1 + 2, y1 + 1)
                        page.draw_rect(pad_rect, color=(1, 1, 1), fill=(1, 1, 1))

                        # Écrire le nouveau texte avec la même taille
                        f_size = max(8.0, round(h * 0.75, 1))
                        origin = fitz.Point(x0, y1 - 2)
                        font_kwargs = get_font_kwargs("Arial")
                        page.insert_text(origin, new_line_text, fontsize=f_size, color=(0.1, 0.1, 0.1), **font_kwargs)
                        total_replaced += 1

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return total_replaced


def pdf_to_images(pdf_path: str, output_folder: str, fmt: str = "png", dpi: int = 150) -> List[str]:
    """Convertit toutes les pages d'un PDF en fichiers images haute définition."""
    os.makedirs(output_folder, exist_ok=True)
    doc = fitz.open(pdf_path)
    output_files = []
    pad_len = max(2, len(str(len(doc))))
    
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        filename = f"page_{str(i + 1).zfill(pad_len)}.{fmt.lower()}"
        out_path = os.path.join(output_folder, filename)
        pix.save(out_path)
        output_files.append(out_path)
        
    doc.close()
    return output_files


def images_to_pdf(image_paths: List[str], output_path: str) -> int:
    """Assemble une liste d'images en un seul document PDF."""
    if not image_paths:
        raise ValueError("Aucune image spécifiée.")
    
    doc = fitz.open()
    count = 0
    for img_path in image_paths:
        if not os.path.exists(img_path):
            continue
        try:
            img_doc = fitz.open(img_path)
            pdfbytes = img_doc.convert_to_pdf()
            img_doc.close()
            img_pdf = fitz.open("pdf", pdfbytes)
            doc.insert_pdf(img_pdf)
            img_pdf.close()
            count += 1
        except Exception as e:
            print(f"Avertissement : impossible de convertir {img_path} : {e}")
            
    if count == 0:
        doc.close()
        raise ValueError("Aucune image n'a pu être traitée.")
        
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return count


def compress_pdf(pdf_path: str, output_path: str) -> Tuple[int, int]:
    """Compresse et optimise un fichier PDF."""
    initial_size = os.path.getsize(pdf_path)
    doc = fitz.open(pdf_path)
    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()
    final_size = os.path.getsize(output_path)
    return initial_size, final_size


def protect_pdf(pdf_path: str, output_path: str, password: str) -> None:
    """Protège un document PDF par mot de passe avec chiffrement AES-256."""
    if not password:
        raise ValueError("Le mot de passe ne peut pas être vide.")
    doc = fitz.open(pdf_path)
    doc.save(output_path, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
    doc.close()


def unlock_pdf(pdf_path: str, output_path: str, password: str) -> bool:
    """Déverrouille un PDF protégé et enregistre une copie non chiffrée."""
    doc = fitz.open(pdf_path)
    if not doc.is_encrypted:
        doc.save(output_path)
        doc.close()
        return True
    
    auth_res = doc.authenticate(password)
    if auth_res <= 0:
        doc.close()
        return False
        
    doc.save(output_path)
    doc.close()
    return True


def extract_text_from_pdf(pdf_path: str, output_txt_path: Optional[str] = None) -> str:
    """Extrait tout le texte d'un document PDF (vectoriel ou OCR si scanné)."""
    doc = fitz.open(pdf_path)
    full_text = []
    engine = None

    for i, page in enumerate(doc):
        page_text = page.get_text()
        if not page_text.strip():
            # Si vide, tenter l'OCR
            if engine is None:
                engine = get_ocr_engine()
            if engine:
                pix = page.get_pixmap(dpi=150)
                ocr_res, _ = engine(pix.tobytes("png"))
                if ocr_res:
                    page_text = "\n".join(item[1] for item in ocr_res)

        full_text.append(f"--- PAGE {i + 1} ---\n" + page_text)
    doc.close()
    
    result = "\n\n".join(full_text)
    if output_txt_path:
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(result)
            
    return result
