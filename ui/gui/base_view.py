"""
ui/gui/base_view.py - Classe de base partagée pour les vues Tkinter.
Fournit l'accès à la session active, au runner asynchrone et aux sélecteurs PDF.
"""

import os
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Dict, List, Optional, Tuple

from core.session import DocumentSession
from ui.gui.async_runner import AsyncTaskRunner
from ui.theme import PALETTE, make_button


class SidebarNav(tk.Frame):
    """Barre latérale de navigation regroupée par catégories."""

    def __init__(self, parent: tk.Misc, on_select: Callable[[str], None]):
        super().__init__(parent, bg=PALETTE["sidebar"], width=230)
        self.pack_propagate(False)
        self.on_select = on_select
        self.buttons: Dict[str, tk.Button] = {}
        self._build_brand()

    def _build_brand(self) -> None:
        brand = tk.Frame(self, bg=PALETTE["sidebar"], pady=18, padx=16)
        brand.pack(fill=tk.X)
        tk.Label(
            brand,
            text="⚡ PDF Studio",
            font=("Segoe UI", 15, "bold"),
            bg=PALETTE["sidebar"],
            fg="#ffffff",
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="Rapide • Hors-ligne • Privé",
            font=("Segoe UI", 8),
            bg=PALETTE["sidebar"],
            fg=PALETTE["text_sidebar_muted"],
        ).pack(anchor="w")

    def add_section(self, title: str, items: List[Tuple[str, str]]) -> None:
        tk.Label(
            self,
            text=title,
            font=("Segoe UI", 8, "bold"),
            bg=PALETTE["sidebar"],
            fg=PALETTE["text_sidebar_muted"],
            padx=16,
            pady=6,
        ).pack(anchor="w", pady=(10, 0))
        for key, label in items:
            btn = tk.Button(
                self,
                text=label,
                font=("Segoe UI", 10),
                bg=PALETTE["sidebar_btn"],
                fg=PALETTE["text_light"],
                anchor="w",
                padx=16,
                pady=9,
                relief=tk.FLAT,
                cursor="hand2",
                command=lambda k=key: self.on_select(k),
            )
            btn.pack(fill=tk.X, padx=10, pady=2)
            self.buttons[key] = btn

    def set_active(self, active_key: str) -> None:
        for key, btn in self.buttons.items():
            bg = PALETTE["sidebar_active"] if key == active_key else PALETTE["sidebar_btn"]
            btn.config(bg=bg)


class AppContext:
    """Contexte partagé injecté dans chaque vue modulaire."""

    def __init__(
        self,
        session: DocumentSession,
        runner: AsyncTaskRunner,
        set_status: Callable[[str, bool], None],
        on_document_changed: Callable[[], None],
    ):
        self.session = session
        self.runner = runner
        self.set_status = set_status
        self.on_document_changed = on_document_changed


class BaseView(tk.Frame):
    """Socle commun pour toutes les vues de l'interface bureau."""

    def __init__(self, parent: tk.Misc, ctx: AppContext):
        super().__init__(parent, bg=PALETTE["bg"])
        self.ctx = ctx

    def on_activated(self) -> None:
        """Hook appelé lorsque l'utilisateur affiche cette vue."""

    def on_document_updated(self) -> None:
        """Hook appelé lorsque le document actif ou ses pages changent."""

    def build_target_pdf_picker(
        self,
        parent: tk.Misc,
        path_var: tk.StringVar,
        label_text: str = "1. Document PDF cible :",
        on_selected: Optional[Callable[[str], None]] = None,
    ) -> tk.Frame:
        """Construit un sélecteur de PDF pré-rempli avec le document actif."""
        box = tk.Frame(parent, bg=PALETTE["surface"])
        box.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            box, text=label_text, font=("Segoe UI", 10, "bold"), bg=PALETTE["surface"]
        ).pack(anchor="w", pady=(0, 4))

        row = tk.Frame(box, bg=PALETTE["surface"])
        row.pack(fill=tk.X)
        ttk.Entry(row, textvariable=path_var).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8)
        )
        self._add_picker_buttons(row, path_var, on_selected)
        return box

    def _add_picker_buttons(
        self,
        row: tk.Frame,
        path_var: tk.StringVar,
        on_selected: Optional[Callable[[str], None]],
    ) -> None:
        def browse() -> None:
            chosen = filedialog.askopenfilename(
                title="Sélectionner un document PDF", filetypes=[("Fichiers PDF", "*.pdf")]
            )
            if chosen:
                path_var.set(chosen)
                if on_selected:
                    on_selected(chosen)

        def use_active() -> None:
            active = self.ctx.session.working_path
            if active and os.path.exists(active):
                path_var.set(active)
                if on_selected:
                    on_selected(active)

        make_button(row, "📄 Utiliser actif", use_active, variant="info").pack(
            side=tk.LEFT, padx=(0, 4)
        )
        make_button(row, "📂 Parcourir...", browse, variant="neutral").pack(side=tk.LEFT)
