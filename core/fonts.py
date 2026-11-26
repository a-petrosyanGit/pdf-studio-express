"""
core/fonts.py - Résolution multi-plateforme des polices et adaptation typographique.
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
import pymupdf as fitz

logger = logging.getLogger(__name__)

FONT_CANDIDATES: Dict[str, Dict[str, List[str]]] = {
    "arial": {
        "regular": ["arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
        "bold": ["arialbd.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
        "italic": ["ariali.ttf", "LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf"],
        "bolditalic": [
            "arialbi.ttf",
            "LiberationSans-BoldItalic.ttf",
            "DejaVuSans-BoldOblique.ttf",
        ],
    },
    "calibri": {
        "regular": ["calibri.ttf", "Carlito-Regular.ttf", "arial.ttf"],
        "bold": ["calibrib.ttf", "Carlito-Bold.ttf", "arialbd.ttf"],
        "italic": ["calibrii.ttf", "Carlito-Italic.ttf", "ariali.ttf"],
        "bolditalic": ["calibriz.ttf", "Carlito-BoldItalic.ttf", "arialbi.ttf"],
    },
    "times": {
        "regular": [
            "times.ttf",
            "timesnr.ttf",
            "LiberationSerif-Regular.ttf",
            "DejaVuSerif.ttf",
        ],
        "bold": ["timesbd.ttf", "LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"],
        "italic": ["timesi.ttf", "LiberationSerif-Italic.ttf", "DejaVuSerif-Italic.ttf"],
        "bolditalic": [
            "timesbi.ttf",
            "LiberationSerif-BoldItalic.ttf",
            "DejaVuSerif-BoldItalic.ttf",
        ],
    },
    "courier": {
        "regular": [
            "cour.ttf",
            "courier.ttf",
            "LiberationMono-Regular.ttf",
            "DejaVuSansMono.ttf",
        ],
        "bold": ["courbd.ttf", "LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"],
        "italic": ["couri.ttf", "LiberationMono-Italic.ttf", "DejaVuSansMono-Oblique.ttf"],
        "bolditalic": [
            "courbi.ttf",
            "LiberationMono-BoldItalic.ttf",
            "DejaVuSansMono-BoldOblique.ttf",
        ],
    },
    "segoe": {
        "regular": ["segoeui.ttf", "arial.ttf"],
        "bold": ["segoeuib.ttf", "arialbd.ttf"],
        "italic": ["segoeuii.ttf", "ariali.ttf"],
        "bolditalic": ["segoeuiz.ttf", "arialbi.ttf"],
    },
    "tahoma": {
        "regular": ["tahoma.ttf", "arial.ttf"],
        "bold": ["tahomabd.ttf", "arialbd.ttf"],
        "italic": ["tahoma.ttf", "ariali.ttf"],
        "bolditalic": ["tahomabd.ttf", "arialbi.ttf"],
    },
    "verdana": {
        "regular": ["verdana.ttf", "arial.ttf"],
        "bold": ["verdanab.ttf", "arialbd.ttf"],
        "italic": ["verdanai.ttf", "ariali.ttf"],
        "bolditalic": ["verdanaz.ttf", "arialbi.ttf"],
    },
    "consolas": {
        "regular": ["consola.ttf", "cour.ttf"],
        "bold": ["consolab.ttf", "courbd.ttf"],
        "italic": ["consolai.ttf", "couri.ttf"],
        "bolditalic": ["consolaz.ttf", "courbi.ttf"],
    },
}

_BASE14_TABLE: Dict[str, Dict[Tuple[bool, bool], str]] = {
    "serif": {
        (False, False): "tiro",
        (True, False): "tibo",
        (False, True): "tiit",
        (True, True): "tibi",
    },
    "mono": {
        (False, False): "cour",
        (True, False): "cobo",
        (False, True): "coit",
        (True, True): "cobi",
    },
    "sans": {
        (False, False): "helv",
        (True, False): "hebo",
        (False, True): "heit",
        (True, True): "hebi",
    },
}


def get_system_font_dirs() -> List[str]:
    """Retourne les répertoires de polices existants selon le système d'exploitation."""
    dirs: List[str] = []
    if sys.platform.startswith("win"):
        windir = os.environ.get("WINDIR", "C:\\Windows")
        dirs.append(os.path.join(windir, "Fonts"))
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            dirs.append(os.path.join(local_app, "Microsoft", "Windows", "Fonts"))
    elif sys.platform == "darwin":
        dirs.extend([
            "/Library/Fonts",
            "/System/Library/Fonts",
            os.path.expanduser("~/Library/Fonts"),
        ])
    else:
        dirs.extend([
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts"),
        ])
    return [d for d in dirs if os.path.exists(d)]


def _style_key(is_bold: bool, is_italic: bool) -> str:
    if is_bold and is_italic:
        return "bolditalic"
    if is_bold:
        return "bold"
    if is_italic:
        return "italic"
    return "regular"


def _find_direct_in_dirs(font_dirs: List[str], candidates: List[str]) -> Optional[str]:
    for fdir in font_dirs:
        for fname in candidates:
            full_path = os.path.join(fdir, fname)
            if os.path.isfile(full_path):
                return full_path
    return None


def _match_in_folder(files: List[str], candidates: List[str]) -> Optional[str]:
    files_lower = {f.lower(): f for f in files}
    for fname in candidates:
        match = files_lower.get(fname.lower())
        if match:
            return match
    return None


def _find_recursive_in_dirs(font_dirs: List[str], candidates: List[str]) -> Optional[str]:
    for fdir in font_dirs:
        for root, _, files in os.walk(fdir):
            match = _match_in_folder(files, candidates)
            if match:
                return os.path.join(root, match)
    return None


def find_font_file(family: str, is_bold: bool, is_italic: bool) -> Optional[str]:
    """Recherche un fichier de police TTF sur le système."""
    family_lower = family.lower()
    matched_key = next((k for k in FONT_CANDIDATES if k in family_lower), "arial")
    style = _style_key(is_bold, is_italic)
    candidates = FONT_CANDIDATES[matched_key].get(style) or (
        FONT_CANDIDATES[matched_key]["regular"]
    )
    font_dirs = get_system_font_dirs()
    return _find_direct_in_dirs(font_dirs, candidates) or _find_recursive_in_dirs(
        font_dirs, candidates
    )


def _select_base14_family(fn_lower: str) -> str:
    if any(token in fn_lower for token in ("times", "serif", "roman")):
        return "serif"
    if any(token in fn_lower for token in ("courier", "mono", "code", "consola")):
        return "mono"
    return "sans"


def get_font_kwargs(font_name: str, flags: int = 0) -> Dict[str, Any]:
    """Retourne les arguments optimaux (`fontfile` ou `fontname`) pour `insert_text`."""
    fn_lower = font_name.lower()
    is_bold = bool(flags & 16) or ("bold" in fn_lower) or ("gras" in fn_lower)
    is_italic = bool(flags & 2) or ("italic" in fn_lower) or ("oblique" in fn_lower)

    font_file = find_font_file(font_name, is_bold=is_bold, is_italic=is_italic)
    if font_file and os.path.exists(font_file):
        return {"fontfile": font_file}

    base14_fam = _select_base14_family(fn_lower)
    return {"fontname": _BASE14_TABLE[base14_fam][(is_bold, is_italic)]}


def measure_text_length(
    text: str,
    fontsize: float,
    font_kwargs: Dict[str, Any],
) -> float:
    """Mesure la largeur d'un texte en points PDF (`fontfile` ou `fontname`)."""
    if not text or fontsize <= 0:
        return 0.0

    if "fontfile" in font_kwargs:
        try:
            font_obj = fitz.Font(fontfile=font_kwargs["fontfile"])
            return float(font_obj.text_length(text, fontsize=fontsize))
        except Exception as exc:
            logger.debug("Repli mesure Base14 après erreur TTF : %s", exc)

    fontname = font_kwargs.get("fontname", "helv")
    try:
        return float(fitz.get_text_length(text, fontname=fontname, fontsize=fontsize))
    except Exception as exc:
        logger.debug("Repli mesure helv pour '%s' : %s", fontname, exc)
        return float(fitz.get_text_length(text, fontname="helv", fontsize=fontsize))


def calculate_fit_fontsize(
    text: str,
    font_kwargs: Dict[str, Any],
    target_width: float,
    initial_size: float,
    min_size: float = 6.0,
) -> float:
    """Réduit proportionnellement la taille de police pour éviter tout débordement."""
    if target_width <= 0 or not text:
        return initial_size

    measured_width = measure_text_length(text, initial_size, font_kwargs)
    if measured_width <= target_width or measured_width <= 0:
        return initial_size

    fitted_size = initial_size * (target_width / measured_width)
    return max(min_size, round(fitted_size, 1))


def int_to_rgb(col_int: int) -> Tuple[float, float, float]:
    """Convertit un entier sRGB en tuple RGB (0.0 à 1.0)."""
    r = ((col_int >> 16) & 255) / 255.0
    g = ((col_int >> 8) & 255) / 255.0
    b = (col_int & 255) / 255.0
    return (r, g, b)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    """Convertit un tuple RGB (0.0-1.0) en code hexadécimal #RRGGBB."""
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


def hex_to_rgb(hex_str: str) -> Tuple[float, float, float]:
    """Convertit un code hexadécimal #RRGGBB en tuple RGB (0.0-1.0)."""
    clean_hex = hex_str.lstrip("#")
    if len(clean_hex) != 6:
        return (0.0, 0.0, 0.0)
    r = int(clean_hex[0:2], 16) / 255.0
    g = int(clean_hex[2:4], 16) / 255.0
    b = int(clean_hex[4:6], 16) / 255.0
    return (r, g, b)
