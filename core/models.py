"""
core/models.py - Modèles de données typés pour PDF Studio Express.
Regroupe les métadonnées, configurations et requêtes d'édition via dataclasses.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PDFMetadata:
    """Métadonnées générales d'un document PDF."""

    page_count: int = 0
    size_bytes: int = 0
    title: str = ""
    author: str = ""
    subject: str = ""
    creator: str = ""
    producer: str = ""
    is_encrypted: bool = False
    is_scanned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_count": self.page_count,
            "size_bytes": self.size_bytes,
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "creator": self.creator,
            "producer": self.producer,
            "is_encrypted": self.is_encrypted,
            "is_scanned": self.is_scanned,
        }


@dataclass
class PageConfig:
    """Configuration d'une page pour la réorganisation et rotation."""

    source_page: int
    rotation: int = 0

    def normalized_rotation(self) -> int:
        return self.rotation % 360

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_page": self.source_page,
            "rotation": self.normalized_rotation(),
        }


@dataclass
class TextElement:
    """Représente un élément ou bloc de texte extrait (vectoriel ou OCR)."""

    id: int
    text: str
    font: str = "Helvetica"
    size: float = 12.0
    flags: int = 0
    color_rgb: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    color_hex: str = "#000000"
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    origin: Tuple[float, float] = (0.0, 0.0)
    is_ocr: bool = False
    bg_color_rgb: Optional[Tuple[float, float, float]] = None

    @property
    def width(self) -> float:
        return max(0.0, self.bbox[2] - self.bbox[0])

    @property
    def height(self) -> float:
        return max(0.0, self.bbox[3] - self.bbox[1])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "font": self.font,
            "size": self.size,
            "flags": self.flags,
            "color_rgb": self.color_rgb,
            "color_hex": self.color_hex,
            "bbox": list(self.bbox),
            "origin": list(self.origin),
            "is_ocr": self.is_ocr,
            "bg_color_rgb": self.bg_color_rgb,
        }


@dataclass
class TextEditRequest:
    """Paramètres encapsulés pour remplacer un élément textuel ciblé."""

    page_num: int
    elem_bbox: Tuple[float, float, float, float]
    new_text: str
    elem_origin: Optional[Tuple[float, float]] = None
    font_name: str = "Helvetica"
    font_size: float = 12.0
    font_flags: int = 0
    font_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    use_white_bg: bool = False
    is_ocr: bool = False
    bg_color_rgb: Optional[Tuple[float, float, float]] = None
    auto_fit: bool = True
    min_font_size: float = 6.0


@dataclass
class SearchReplaceRequest:
    """Paramètres encapsulés pour rechercher et remplacer dans un PDF."""

    search_text: str
    replace_text: str
    target_page: Optional[int] = None
    use_white_bg: bool = False
    auto_fit: bool = True


@dataclass
class WatermarkConfig:
    """Paramètres pour l'application d'un filigrane textuel."""

    text: str = ""
    font_name: str = "Arial-Bold"
    font_size: int = 44
    color_rgb: Tuple[float, float, float] = (0.7, 0.7, 0.7)
    opacity: float = 0.35
    angle: int = 45
    pages: Optional[List[int]] = None


@dataclass
class PageNumberConfig:
    """Paramètres pour la numérotation des pages."""

    enabled: bool = False
    format_str: str = "Page {page} / {total}"
    position: str = "bottom-center"
    font_size: int = 10
    color_rgb: Tuple[float, float, float] = (0.4, 0.4, 0.4)
    pages: Optional[List[int]] = None


@dataclass
class OptimizationStats:
    """Statistiques issues d'une opération de compression/optimisation."""

    initial_bytes: int = 0
    final_bytes: int = 0

    @property
    def saved_bytes(self) -> int:
        return max(0, self.initial_bytes - self.final_bytes)

    @property
    def reduction_percentage(self) -> float:
        if self.initial_bytes <= 0:
            return 0.0
        return max(0.0, (1.0 - (self.final_bytes / self.initial_bytes)) * 100.0)
