"""
core/fonts.py - Résolution multi-plateforme des polices et adaptation typographique.
Gère la recherche de fichiers de polices système (Windows, macOS, Linux),
les correspondances Base14 pour PDF et le calcul d'auto-ajustement (auto-fitting).
"""

import os
import sys
from typing import Dict, Tuple, Optional, Any, List
import fitz


def get_system_font_dirs() -> List[str]:
    """Retourne la liste ordonnée des répertoires de polices selon le système d'exploitation."""
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
            os.path.expanduser("~/Library/Fonts")
        ])
    else:
        # Linux / Unix
        dirs.extend([
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts"),
            os.path.expanduser("~/.local/share/fonts")
        ])

    return [d for d in dirs if os.path.exists(d)]


# Index de correspondance des familles de polices courantes vers des noms de fichiers types
FONT_CANDIDATES: Dict[str, Dict[str, List[str]]] = {
    "arial": {
        "regular": ["arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf"],
        "bold": ["arialbd.ttf", "LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
        "italic": ["ariali.ttf", "LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf"],
        "bolditalic": ["arialbi.ttf", "LiberationSans-BoldItalic.ttf", "DejaVuSans-BoldOblique.ttf"],
    },
    "calibri": {
        "regular": ["calibri.ttf", "Carlito-Regular.ttf", "arial.ttf"],
        "bold": ["calibrib.ttf", "Carlito-Bold.ttf", "arialbd.ttf"],
        "italic": ["calibrii.ttf", "Carlito-Italic.ttf", "ariali.ttf"],
        "bolditalic": ["calibriz.ttf", "Carlito-BoldItalic.ttf", "arialbi.ttf"],
    },
    "times": {
        "regular": ["times.ttf", "timesnr.ttf", "LiberationSerif-Regular.ttf", "DejaVuSerif.ttf"],
        "bold": ["timesbd.ttf", "LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"],
        "italic": ["timesi.ttf", "LiberationSerif-Italic.ttf", "DejaVuSerif-Italic.ttf"],
        "bolditalic": ["timesbi.ttf", "LiberationSerif-BoldItalic.ttf", "DejaVuSerif-BoldItalic.ttf"],
    },
    "courier": {
        "regular": ["cour.ttf", "courier.ttf", "LiberationMono-Regular.ttf", "DejaVuSansMono.ttf"],
        "bold": ["courbd.ttf", "LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"],
        "italic": ["couri.ttf", "LiberationMono-Italic.ttf", "DejaVuSansMono-Oblique.ttf"],
        "bolditalic": ["courbi.ttf", "LiberationMono-BoldItalic.ttf", "DejaVuSansMono-BoldOblique.ttf"],
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
    }
}


def find_font_file(family: str, is_bold: bool, is_italic: bool) -> Optional[str]:
    """Recherche un fichier de police TTF sur le système d'exploitation."""
    family_lower = family.lower()
    matched_key = None
    for key in FONT_CANDIDATES:
        if key in family_lower:
            matched_key = key
            break

    if not matched_key:
        matched_key = "arial"  # Repli par défaut sans-serif

    style_key = "regular"
    if is_bold and is_italic:
        style_key = "bolditalic"
    elif is_bold:
        style_key = "bold"
    elif is_italic:
        style_key = "italic"

    candidate_filenames = FONT_CANDIDATES[matched_key].get(style_key, [])
    # Repli si variante non présente
    if not candidate_filenames and style_key != "regular":
        candidate_filenames = FONT_CANDIDATES[matched_key].get("regular", [])

    font_dirs = get_system_font_dirs()

    # 1. Recherche par nom exact dans les répertoires de polices
    for fdir in font_dirs:
        for fname in candidate_filenames:
            full_path = os.path.join(fdir, fname)
            if os.path.isfile(full_path):
                return full_path

    # 2. Recherche récursive limitée sous les répertoires de polices (notamment Linux /usr/share/fonts/truetype)
    for fdir in font_dirs:
        for root, _, files in os.walk(fdir):
            files_lower = {f.lower(): f for f in files}
            for fname in candidate_filenames:
                if fname.lower() in files_lower:
                    return os.path.join(root, files_lower[fname.lower()])

    return None


def get_font_kwargs(font_name: str, flags: int = 0) -> Dict[str, Any]:
    """
    Détermine les arguments optimaux pour `fitz.Page.insert_text`.
    Retourne soit `{'fontfile': path}` si un fichier TTF est trouvé,
    soit `{'fontname': base14_name}` en repli standard PDF garanti.
    """
    fn_lower = font_name.lower()
    is_bold = bool(flags & 16) or ("bold" in fn_lower) or ("gras" in fn_lower)
    is_italic = bool(flags & 2) or ("italic" in fn_lower) or ("oblique" in fn_lower)

    # 1. Tentative avec police système installée
    font_file = find_font_file(font_name, is_bold=is_bold, is_italic=is_italic)
    if font_file and os.path.exists(font_file):
        return {"fontfile": font_file}

    # 2. Repli Base14 standardisé PyMuPDF (aucune dépendance OS)
    if "times" in fn_lower or "serif" in fn_lower or "roman" in fn_lower:
        if is_bold and is_italic:
            return {"fontname": "tibi"}
        elif is_bold:
            return {"fontname": "tibo"}
        elif is_italic:
            return {"fontname": "tiit"}
        return {"fontname": "tiro"}

    if "courier" in fn_lower or "mono" in fn_lower or "code" in fn_lower or "consola" in fn_lower:
        if is_bold and is_italic:
            return {"fontname": "cobi"}
        elif is_bold:
            return {"fontname": "cobo"}
        elif is_italic:
            return {"fontname": "coit"}
        return {"fontname": "cour"}

    # Sans-serif (Helvetica / Arial standard)
    if is_bold and is_italic:
        return {"fontname": "hebi"}
    elif is_bold:
        return {"fontname": "hebo"}
    elif is_italic:
        return {"fontname": "heit"}
    return {"fontname": "helv"}


def measure_text_length(text: str, fontsize: float, font_kwargs: Dict[str, Any]) -> float:
    """
    Mesure la largeur d'un texte en points PDF, en acceptant indifféremment
    une police Base14 ('fontname') ou un fichier TrueType ('fontfile').
    """
    if not text or fontsize <= 0:
        return 0.0

    if "fontfile" in font_kwargs:
        try:
            f = fitz.Font(fontfile=font_kwargs["fontfile"])
            return float(f.text_length(text, fontsize=fontsize))
        except Exception:
            pass

    fontname = font_kwargs.get("fontname", "helv")
    try:
        return float(fitz.get_text_length(text, fontname=fontname, fontsize=fontsize))
    except Exception:
        # Repli universel standard
        return float(fitz.get_text_length(text, fontname="helv", fontsize=fontsize))


def calculate_fit_fontsize(
    text: str,
    font_kwargs: Dict[str, Any],
    target_width: float,
    initial_size: float,
    min_size: float = 6.0
) -> float:
    """
    Calcule la taille de police maximale permettant au texte de tenir
    strictement dans la largeur cible `target_width`.
    Empêche les débordements de texte lors des remplacements.
    """
    if target_width <= 0 or not text:
        return initial_size

    measured_width = measure_text_length(text, initial_size, font_kwargs)
    if measured_width <= target_width or measured_width <= 0:
        return initial_size

    scale_ratio = target_width / measured_width
    fitted_size = initial_size * scale_ratio
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
