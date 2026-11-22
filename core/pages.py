"""
core/pages.py - Gestion des pages, opérations structurelles, filigranes et conversion d'images.
Responsabilité unique : manipulation des pages PDF (ordre, rotation, suppression, fusion, scission).
"""

import os
from typing import List, Dict, Tuple, Optional, Any, Union
from PIL import Image
import fitz

from core.models import PageConfig, WatermarkConfig, PageNumberConfig, PDFMetadata
from core.fonts import get_font_kwargs, measure_text_length


def get_pdf_metadata(pdf_path: str, password: str = "") -> PDFMetadata:
    """Extrait les métadonnées typées et le statut d'un document PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")

    doc = fitz.open(pdf_path)
    if doc.is_encrypted:
        if not password or not doc.authenticate(password):
            doc.close()
            return PDFMetadata(
                page_count=0,
                size_bytes=os.path.getsize(pdf_path),
                is_encrypted=True
            )

    meta = doc.metadata or {}
    page_count = len(doc)
    has_text = any(len(doc[i].get_text().strip()) > 0 for i in range(min(page_count, 3)))
    is_scanned = (page_count > 0 and not has_text)

    info = PDFMetadata(
        page_count=page_count,
        size_bytes=os.path.getsize(pdf_path),
        title=meta.get("title", "") or "",
        author=meta.get("author", "") or "",
        subject=meta.get("subject", "") or "",
        creator=meta.get("creator", "") or "",
        producer=meta.get("producer", "") or "",
        is_encrypted=False,
        is_scanned=is_scanned
    )
    doc.close()
    return info


def render_page_thumbnail(
    pdf_path: str,
    page_num: int,
    max_size: Tuple[int, int] = (160, 220),
    password: str = ""
) -> Image.Image:
    """Génère une miniature PIL Image d'une page spécifique."""
    doc = fitz.open(pdf_path)
    if doc.is_encrypted and password:
        doc.authenticate(password)

    if page_num < 0 or page_num >= len(doc):
        doc.close()
        raise IndexError(f"Numéro de page hors limites : {page_num}")

    page = doc[page_num]
    rect = page.rect

    scale_w = max_size[0] / max(rect.width, 1.0)
    scale_h = max_size[1] / max(rect.height, 1.0)
    scale = min(scale_w, scale_h, 2.5)

    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return img


def render_all_thumbnails(
    pdf_path: str,
    max_size: Tuple[int, int] = (160, 220),
    password: str = ""
) -> List[Image.Image]:
    """Génère les miniatures PIL Image de toutes les pages d'un PDF."""
    doc = fitz.open(pdf_path)
    if doc.is_encrypted and password:
        doc.authenticate(password)

    thumbnails = []
    for i in range(len(doc)):
        page = doc[i]
        rect = page.rect
        scale_w = max_size[0] / max(rect.width, 1.0)
        scale_h = max_size[1] / max(rect.height, 1.0)
        scale = min(scale_w, scale_h, 2.5)

        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        thumbnails.append(img)

    doc.close()
    return thumbnails


def apply_page_modifications(
    source_pdf_path: str,
    output_path: str,
    page_configs: List[Union[PageConfig, Dict[str, Any]]],
    password: str = ""
) -> None:
    """
    Applique une série de réorganisations, rotations et suppressions
    en une passe unique d'assemblage PyMuPDF.
    """
    src_doc = fitz.open(source_pdf_path)
    if src_doc.is_encrypted and password:
        src_doc.authenticate(password)

    out_doc = fitz.open()
    for conf in page_configs:
        if isinstance(conf, dict):
            idx = conf["source_page"]
            rot = conf.get("rotation", 0) % 360
        else:
            idx = conf.source_page
            rot = conf.normalized_rotation()

        if 0 <= idx < len(src_doc):
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
        raise ValueError("Aucun fichier fourni pour la fusion.")

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
    """Convertit une chaîne de plages ('1-3, 5, 8-10') en liste d'indices 0-based ordonnés et dédoublonnés."""
    pages_idx: List[int] = []
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
    """Extrait les pages spécifiées par une plage de numéros."""
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
    """Découpe un PDF en extrayant chaque page dans un fichier individuel."""
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
    watermark_config: Optional[WatermarkConfig] = None,
    number_config: Optional[PageNumberConfig] = None
) -> int:
    """Ajoute un filigrane textuel et/ou une numérotation des pages."""
    doc = fitz.open(pdf_path)
    total = len(doc)

    # Déterminer les pages cibles
    if watermark_config and watermark_config.pages is not None:
        wm_pages = set(watermark_config.pages)
    else:
        wm_pages = set(range(total))

    if number_config and number_config.pages is not None:
        num_pages = set(number_config.pages)
    else:
        num_pages = set(range(total))

    modified_pages = 0
    for i in range(total):
        page = doc[i]
        rect = page.rect
        modified = False

        # Filigrane
        if watermark_config and watermark_config.text.strip() and (i in wm_pages):
            center = fitz.Point(rect.width / 2, rect.height / 2)
            font_kwargs = get_font_kwargs(watermark_config.font_name, flags=16)
            text_len = measure_text_length(watermark_config.text, watermark_config.font_size, font_kwargs)
            text_point = fitz.Point(center.x - (text_len / 2), center.y)

            if watermark_config.angle != 0:
                mat = fitz.Matrix(watermark_config.angle)
                page.insert_text(
                    text_point,
                    watermark_config.text,
                    fontsize=watermark_config.font_size,
                    color=watermark_config.color_rgb,
                    morph=(center, mat),
                    **font_kwargs
                )
            else:
                page.insert_text(
                    text_point,
                    watermark_config.text,
                    fontsize=watermark_config.font_size,
                    color=watermark_config.color_rgb,
                    **font_kwargs
                )
            modified = True

        # Numérotation
        if number_config and number_config.enabled and (i in num_pages):
            page_str = number_config.format_str.replace("{page}", str(i + 1)).replace("{total}", str(total))
            font_kwargs = get_font_kwargs("Arial")
            t_len = measure_text_length(page_str, number_config.font_size, font_kwargs)
            margin = 25

            pos_key = number_config.position
            if pos_key == "bottom-center":
                pos = fitz.Point((rect.width - t_len) / 2, rect.height - margin)
            elif pos_key == "bottom-right":
                pos = fitz.Point(rect.width - t_len - margin, rect.height - margin)
            elif pos_key == "bottom-left":
                pos = fitz.Point(margin, rect.height - margin)
            elif pos_key == "top-center":
                pos = fitz.Point((rect.width - t_len) / 2, margin + number_config.font_size)
            elif pos_key == "top-right":
                pos = fitz.Point(rect.width - t_len - margin, margin + number_config.font_size)
            else:
                pos = fitz.Point((rect.width - t_len) / 2, rect.height - margin)

            page.insert_text(pos, page_str, fontsize=number_config.font_size, color=number_config.color_rgb, **font_kwargs)
            modified = True

        if modified:
            modified_pages += 1

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return modified_pages


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
    """Assemble une liste d'images dans un document PDF."""
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
            print(f"[Conversion] Avertissement image {img_path}: {e}")

    if count == 0:
        doc.close()
        raise ValueError("Aucune image valide n'a pu être traitée.")

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return count
