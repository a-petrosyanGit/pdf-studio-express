"""
ui/theme.py - Palette graphique moderne et fabriques de composants Tkinter.
Centralise les styles visuels pour garantir une interface cohérente et épurée.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional

PALETTE: Dict[str, str] = {
    "bg": "#f1f5f9",
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "sidebar": "#0f172a",
    "sidebar_btn": "#1e293b",
    "sidebar_hover": "#334155",
    "sidebar_active": "#2563eb",
    "text_light": "#f8fafc",
    "text_muted": "#64748b",
    "text_sidebar_muted": "#94a3b8",
    "text_dark": "#0f172a",
    "card_selected": "#eff6ff",
    "card_selected_border": "#2563eb",
    "border": "#e2e8f0",
    "primary": "#2563eb",
    "primary_hover": "#1d4ed8",
    "success": "#16a34a",
    "danger": "#dc2626",
    "danger_bg": "#fee2e2",
    "info_bg": "#e0f2fe",
    "info_fg": "#0369a1",
    "warning_bg": "#fef3c7",
    "warning_fg": "#b45309",
    "neutral_btn": "#e2e8f0",
}


def configure_ttk_styles(root: tk.Misc) -> None:
    """Configure le thème ttk moderne de l'application."""
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        ".",
        font=("Segoe UI", 10),
        background=PALETTE["bg"],
        foreground=PALETTE["text_dark"],
    )
    style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
    style.configure(
        "SubHeader.TLabel",
        font=("Segoe UI", 10),
        foreground=PALETTE["text_muted"],
    )
    style.configure("TNotebook", background=PALETTE["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        font=("Segoe UI", 10, "bold"),
        padding=[14, 7],
        background=PALETTE["neutral_btn"],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", PALETTE["surface"])],
        foreground=[("selected", PALETTE["primary"])],
    )


def make_button(
    parent: tk.Misc,
    text: str,
    command: Callable[[], None],
    variant: str = "neutral",
    **pack_or_style: object,
) -> tk.Button:
    """Crée un bouton plat moderne cohérent selon la variante demandée."""
    styles = {
        "primary": (PALETTE["primary"], "#ffffff", True),
        "success": (PALETTE["success"], "#ffffff", True),
        "danger": (PALETTE["danger_bg"], PALETTE["danger"], True),
        "info": (PALETTE["info_bg"], PALETTE["info_fg"], True),
        "neutral": ("#f1f5f9", PALETTE["text_dark"], False),
    }
    bg, fg, bold = styles.get(variant, styles["neutral"])
    font_size = int(pack_or_style.get("font_size", 9))  # type: ignore[arg-type]
    weight = "bold" if bold else "normal"
    padx = int(pack_or_style.get("padx", 10))  # type: ignore[arg-type]
    pady = int(pack_or_style.get("pady", 5))  # type: ignore[arg-type]
    return tk.Button(
        parent,
        text=text,
        font=("Segoe UI", font_size, weight),
        bg=bg,
        fg=fg,
        activebackground=bg,
        relief=tk.FLAT,
        bd=0,
        padx=padx,
        pady=pady,
        cursor="hand2",
        command=command,
    )


def make_card(
    parent: tk.Misc,
    padx: int = 18,
    pady: int = 16,
    bg: Optional[str] = None,
) -> tk.Frame:
    """Crée un conteneur carte épuré avec bordure légère."""
    return tk.Frame(
        parent,
        bg=bg or PALETTE["surface"],
        highlightbackground=PALETTE["border"],
        highlightthickness=1,
        padx=padx,
        pady=pady,
    )


def make_view_header(
    parent: tk.Misc,
    title: str,
    subtitle: str,
) -> tk.Frame:
    """Crée l'en-tête uniformisé d'une vue."""
    header = tk.Frame(parent, bg=PALETTE["bg"])
    header.pack(fill=tk.X, pady=(0, 12))
    ttk.Label(header, text=title, style="Header.TLabel").pack(anchor="w")
    ttk.Label(header, text=subtitle, style="SubHeader.TLabel").pack(anchor="w")
    return header
