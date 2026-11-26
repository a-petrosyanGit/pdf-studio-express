"""
ui/gui/watermark_view.py - Filigrane texte et numérotation automatique des pages.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import enhancements
from core.models import PageNumberConfig, WatermarkConfig
from ui.gui.base_view import AppContext, BaseView
from ui.theme import PALETTE, make_button, make_card, make_view_header

_COLORS = {
    "Gris": (0.7, 0.7, 0.7),
    "Rouge": (0.85, 0.2, 0.2),
    "Bleu": (0.2, 0.4, 0.85),
    "Noir": (0.1, 0.1, 0.1),
}

_POSITIONS = {
    "Bas - Centre": "bottom-center",
    "Bas - Droite": "bottom-right",
    "Bas - Gauche": "bottom-left",
    "Haut - Droite": "top-right",
    "Haut - Centre": "top-center",
}


class WatermarkView(BaseView):
    """Vue dédiée aux tampons filigranes et numérotation des pages."""

    def __init__(self, parent: tk.Misc, ctx: AppContext):
        super().__init__(parent, ctx)
        self._build_ui()

    def _build_ui(self) -> None:
        make_view_header(
            self,
            "Filigrane & Numérotation",
            "Apposez un tampon (CONFIDENTIEL, PAYÉ...) et/ou numérotez vos pages.",
        )
        card = make_card(self, padx=18, pady=16)
        card.pack(fill=tk.BOTH, expand=True)

        self.wm_file_var = tk.StringVar()
        self.build_target_pdf_picker(card, self.wm_file_var)
        self._build_watermark_box(card)
        self._build_numbering_box(card)

        make_button(
            card,
            "🏷️ Appliquer et enregistrer sous...",
            self._execute,
            variant="success",
            pady=8,
        ).pack(anchor="e", pady=(10, 0))

    def on_document_updated(self) -> None:
        if self.ctx.session.working_path:
            self.wm_file_var.set(self.ctx.session.working_path)

    def _build_watermark_box(self, parent: tk.Frame) -> None:
        box = tk.LabelFrame(
            parent,
            text=" 🏷️ 1. Filigrane Texte ",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["surface_alt"],
            padx=12,
            pady=10,
        )
        box.pack(fill=tk.X, pady=(0, 14))
        self._build_wm_text_row(box)
        self._build_wm_style_row(box)

    def _build_wm_text_row(self, box: tk.LabelFrame) -> None:
        row1 = tk.Frame(box, bg=PALETTE["surface_alt"])
        row1.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row1, text="Texte :", bg=PALETTE["surface_alt"]).pack(side=tk.LEFT)
        self.wm_text_var = tk.StringVar(value="CONFIDENTIEL")
        ttk.Entry(row1, textvariable=self.wm_text_var, width=26).pack(side=tk.LEFT, padx=8)
        for preset in ("CONFIDENTIEL", "PAYÉ", "COPIE", "BROUILLON"):
            make_button(
                row1, preset, lambda p=preset: self.wm_text_var.set(p), padx=6, pady=2
            ).pack(side=tk.LEFT, padx=2)

    def _build_wm_style_row(self, box: tk.LabelFrame) -> None:
        row2 = tk.Frame(box, bg=PALETTE["surface_alt"])
        row2.pack(fill=tk.X)
        self.wm_angle_var = tk.IntVar(value=45)
        self.wm_size_var = tk.IntVar(value=44)
        self.wm_color_var = tk.StringVar(value="Gris")

        tk.Label(row2, text="Angle :", bg=PALETTE["surface_alt"]).pack(side=tk.LEFT)
        ttk.Combobox(
            row2,
            textvariable=self.wm_angle_var,
            values=[0, 45, 90, 315],
            state="readonly",
            width=6,
        ).pack(side=tk.LEFT, padx=(4, 14))
        tk.Label(row2, text="Taille :", bg=PALETTE["surface_alt"]).pack(side=tk.LEFT)
        ttk.Spinbox(row2, from_=14, to=100, textvariable=self.wm_size_var, width=6).pack(
            side=tk.LEFT, padx=(4, 14)
        )
        tk.Label(row2, text="Couleur :", bg=PALETTE["surface_alt"]).pack(side=tk.LEFT)
        ttk.Combobox(
            row2,
            textvariable=self.wm_color_var,
            values=list(_COLORS.keys()),
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT, padx=4)

    def _build_numbering_box(self, parent: tk.Frame) -> None:
        box = tk.LabelFrame(
            parent,
            text=" 🔢 2. Numérotation des pages ",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["surface_alt"],
            padx=12,
            pady=10,
        )
        box.pack(fill=tk.X, pady=(0, 10))
        self.num_enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            box,
            text="Activer la numérotation automatique",
            variable=self.num_enabled_var,
            font=("Segoe UI", 9, "bold"),
            bg=PALETTE["surface_alt"],
        ).pack(anchor="w", pady=(0, 8))

        row = tk.Frame(box, bg=PALETTE["surface_alt"])
        row.pack(fill=tk.X)
        self.num_fmt_var = tk.StringVar(value="Page {page} / {total}")
        self.num_pos_var = tk.StringVar(value="Bas - Centre")
        tk.Label(row, text="Format :", bg=PALETTE["surface_alt"]).pack(side=tk.LEFT)
        ttk.Combobox(
            row,
            textvariable=self.num_fmt_var,
            values=["Page {page} / {total}", "Page {page}", "{page} sur {total}", "{page}"],
            width=20,
        ).pack(side=tk.LEFT, padx=(4, 14))
        tk.Label(row, text="Position :", bg=PALETTE["surface_alt"]).pack(side=tk.LEFT)
        ttk.Combobox(
            row,
            textvariable=self.num_pos_var,
            values=list(_POSITIONS.keys()),
            state="readonly",
            width=15,
        ).pack(side=tk.LEFT, padx=4)

    def _execute(self) -> None:
        pdf_path = self.wm_file_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Attention", "Sélectionnez un fichier PDF valide.")
            return
        out = filedialog.asksaveasfilename(
            title="Enregistrer le PDF final",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")],
        )
        if not out:
            return

        wm_cfg = WatermarkConfig(
            text=self.wm_text_var.get(),
            font_size=self.wm_size_var.get(),
            color_rgb=_COLORS.get(self.wm_color_var.get(), (0.7, 0.7, 0.7)),
            angle=self.wm_angle_var.get(),
        )
        num_cfg = PageNumberConfig(
            enabled=self.num_enabled_var.get(),
            format_str=self.num_fmt_var.get(),
            position=_POSITIONS.get(self.num_pos_var.get(), "bottom-center"),
        )
        self.ctx.runner.run(
            lambda: enhancements.add_watermark_and_numbering(pdf_path, out, wm_cfg, num_cfg),
            lambda _cnt: messagebox.showinfo("Succès", f"Fichier enregistré :\n{out}"),
            status_msg="Application du filigrane et numérotation...",
        )
