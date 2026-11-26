"""
core/pages.py - Opérations structurelles sur les pages PDF (ordre, rotation, fusion, découpe).
"""

import os
from typing import Any, Dict, List, Tuple, Union
from PIL import Image
import pymupdf as fitz

from core.models import PageConfig, PDFMetadata


def _open_authenticated(pdf_path: str, password: str = "") -> fitz.Document:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")
    doc = fitz.open(pdf_path)
    if doc.is_encrypted and password:
        doc.authenticate(password)
    return doc


def _extract_doc_metadata(doc: fitz.Document, pdf_path: str) -> PDFMetadata:
    meta = doc.metadata or {}
    page_count = len(doc)
    has_text = any(
        len(doc[i].get_text().strip()) > 0 for i in range(min(page_count, 3))
    )
    return PDFMetadata(
        page_count=page_count,
        size_bytes=os.path.getsize(pdf_path),
        title=meta.get("title") or "",
        author=meta.get("author") or "",
        subject=meta.get("subject") or "",
        creator=meta.get("creator") or "",
        producer=meta.get("producer") or "",
        is_encrypted=False,
        is_scanned=(page_count > 0 and not has_text),
    )


def get_pdf_metadata(pdf_path: str, password: str = "") -> PDFMetadata:
    """Extrait les métadonnées typées et le statut d'un document PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        if doc.is_encrypted and (not password or not doc.authenticate(password)):
            return PDFMetadata(
                page_count=0,
                size_bytes=os.path.getsize(pdf_path),
                is_encrypted=True,
            )
        return _extract_doc_metadata(doc, pdf_path)
    finally:
        doc.close()


def _render_page_to_pil(page: fitz.Page, max_size: Tuple[int, int]) -> Image.Image:
    rect = page.rect
    scale_w = max_size[0] / max(rect.width, 1.0)
    scale_h = max_size[1] / max(rect.height, 1.0)
    scale = min(scale_w, scale_h, 2.5)
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def render_page_thumbnail(
    pdf_path: str,
    page_num: int,
    max_size: Tuple[int, int] = (160, 220),
    password: str = "",
) -> Image.Image:
    """Génère une miniature PIL Image d'une page spécifique."""
    doc = _open_authenticated(pdf_path, password)
    try:
        if page_num < 0 or page_num >= len(doc):
            raise IndexError(f"Numéro de page hors limites : {page_num}")
        return _render_page_to_pil(doc[page_num], max_size)
    finally:
        doc.close()


def render_all_thumbnails(
    pdf_path: str,
    max_size: Tuple[int, int] = (160, 220),
    password: str = "",
) -> List[Image.Image]:
    """Génère les miniatures PIL Image de toutes les pages d'un PDF."""
    doc = _open_authenticated(pdf_path, password)
    try:
        return [_render_page_to_pil(doc[i], max_size) for i in range(len(doc))]
    finally:
        doc.close()


def _append_configured_page(
    src_doc: fitz.Document,
    out_doc: fitz.Document,
    conf: Union[PageConfig, Dict[str, Any]],
) -> None:
    idx = conf["source_page"] if isinstance(conf, dict) else conf.source_page
    rot = (
        conf.get("rotation", 0) % 360
        if isinstance(conf, dict)
        else conf.normalized_rotation()
    )
    if 0 <= idx < len(src_doc):
        out_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
        if rot != 0:
            target = out_doc[-1]
            target.set_rotation((target.rotation + rot) % 360)


def apply_page_modifications(
    source_pdf_path: str,
    output_path: str,
    page_configs: List[Union[PageConfig, Dict[str, Any]]],
    password: str = "",
) -> None:
    """Applique réorganisation, rotations et suppressions en une passe unique."""
    src_doc = _open_authenticated(source_pdf_path, password)
    out_doc = fitz.open()
    try:
        for conf in page_configs:
            _append_configured_page(src_doc, out_doc, conf)
        out_doc.save(output_path, garbage=4, deflate=True)
    finally:
        out_doc.close()
        src_doc.close()


def merge_pdfs(file_paths: List[str], output_path: str) -> int:
    """Fusionne plusieurs fichiers PDF dans l'ordre fourni."""
    if not file_paths:
        raise ValueError("Aucun fichier fourni pour la fusion.")

    out_doc = fitz.open()
    total_pages = 0
    try:
        for path in file_paths:
            if not os.path.exists(path):
                continue
            src = fitz.open(path)
            try:
                out_doc.insert_pdf(src)
                total_pages += len(src)
            finally:
                src.close()
        out_doc.save(output_path, garbage=4, deflate=True)
        return total_pages
    finally:
        out_doc.close()


def _parse_range_token(token: str, max_pages: int) -> List[int]:
    if "-" in token:
        parts = token.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            start = max(1, int(parts[0]))
            end = min(max_pages, int(parts[1]))
            return [p - 1 for p in range(start, end + 1)]
        return []
    if token.isdigit():
        page = int(token)
        if 1 <= page <= max_pages:
            return [page - 1]
    return []


def parse_page_ranges(range_str: str, max_pages: int) -> List[int]:
    """Convertit une plage ('1-3, 5') en liste d'indices 0-based uniques."""
    pages_idx: List[int] = []
    for token in (p.strip() for p in range_str.split(",") if p.strip()):
        for idx in _parse_range_token(token, max_pages):
            if idx not in pages_idx:
                pages_idx.append(idx)
    return pages_idx


def split_pdf_by_range(pdf_path: str, range_str: str, output_path: str) -> int:
    """Extrait les pages spécifiées par une plage de numéros."""
    doc = fitz.open(pdf_path)
    try:
        pages_idx = parse_page_ranges(range_str, len(doc))
        if not pages_idx:
            raise ValueError("Aucune page valide sélectionnée dans la plage.")

        out_doc = fitz.open()
        try:
            for idx in pages_idx:
                out_doc.insert_pdf(doc, from_page=idx, to_page=idx)
            out_doc.save(output_path, garbage=4, deflate=True)
            return len(pages_idx)
        finally:
            out_doc.close()
    finally:
        doc.close()


def split_pdf_all_pages(
    pdf_path: str,
    output_folder: str,
    prefix: str = "page",
) -> List[str]:
    """Découpe un PDF en extrayant chaque page dans un fichier individuel."""
    os.makedirs(output_folder, exist_ok=True)
    doc = fitz.open(pdf_path)
    created_files: List[str] = []
    pad_len = max(2, len(str(len(doc))))
    try:
        for i in range(len(doc)):
            out_doc = fitz.open()
            out_doc.insert_pdf(doc, from_page=i, to_page=i)
            fname = f"{prefix}_{str(i + 1).zfill(pad_len)}.pdf"
            out_path = os.path.join(output_folder, fname)
            out_doc.save(out_path, garbage=4, deflate=True)
            out_doc.close()
            created_files.append(out_path)
        return created_files
    finally:
        doc.close()


def split_pdf_every_n_pages(
    pdf_path: str,
    output_folder: str,
    n: int = 2,
    prefix: str = "part",
) -> List[str]:
    """Découpe un PDF en paquets de N pages."""
    os.makedirs(output_folder, exist_ok=True)
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    created_files: List[str] = []
    try:
        part_num = 1
        for start in range(0, total_pages, n):
            end = min(start + n - 1, total_pages - 1)
            out_doc = fitz.open()
            out_doc.insert_pdf(doc, from_page=start, to_page=end)
            fname = f"{prefix}_{part_num:02d}_pages_{start + 1}-{end + 1}.pdf"
            out_path = os.path.join(output_folder, fname)
            out_doc.save(out_path, garbage=4, deflate=True)
            out_doc.close()
            created_files.append(out_path)
            part_num += 1
        return created_files
    finally:
        doc.close()
