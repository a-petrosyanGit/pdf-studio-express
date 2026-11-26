"""
ui/gui/tools_view.py - Conversion Images <-> PDF, Chiffrement AES-256 et Optimisation.
"""

from dataclasses import dataclass
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, List

from core import enhancements, optimization, security
from ui.gui.base_view import AppContext, BaseView
from ui.theme import PALETTE, make_button, make_view_header


@dataclass
class _PwSectionSpec:
    title: str
    label: str
    var: tk.StringVar
    btn_text: str
    command: Callable[[], None]
    variant: str


class ConvertPane(ttk.Notebook):
    """Onglets PDF -> Images et Images -> PDF."""

    def __init__(self, parent: tk.Misc, ctx: AppContext, picker_builder):
        super().__init__(parent)
        self.ctx = ctx
        self.img_list: List[str] = []
        self.p2i_var = tk.StringVar()
        self.add(self._build_pdf_to_images(picker_builder), text="📄 PDF vers Images")
        self.add(self._build_images_to_pdf(), text="🖼️ Images vers PDF")

    def sync_active(self) -> None:
        self.p2i_var.set(self.ctx.session.working_path or "")

    def _build_pdf_to_images(self, picker_builder) -> tk.Frame:
        tab = tk.Frame(self, bg=PALETTE["surface"], padx=16, pady=16)
        picker_builder(tab, self.p2i_var, "1. Fichier PDF à convertir :")
        opts = tk.Frame(tab, bg=PALETTE["surface"])
        opts.pack(fill=tk.X, pady=(4, 14))
        self.p2i_fmt = tk.StringVar(value="PNG")
        self.p2i_dpi = tk.IntVar(value=150)

        tk.Label(opts, text="Format :", bg=PALETTE["surface"]).pack(side=tk.LEFT)
        ttk.Combobox(
            opts, textvariable=self.p2i_fmt, values=["PNG", "JPEG"], state="readonly", width=8
        ).pack(side=tk.LEFT, padx=(4, 16))
        tk.Label(opts, text="Qualité DPI :", bg=PALETTE["surface"]).pack(side=tk.LEFT)
        ttk.Combobox(
            opts,
            textvariable=self.p2i_dpi,
            values=[100, 150, 200, 300],
            state="readonly",
            width=8,
        ).pack(side=tk.LEFT, padx=4)
        make_button(tab, "🖼️ Exporter les images...", self._run_p2i, variant="primary").pack(
            anchor="w"
        )
        return tab

    def _build_images_to_pdf(self) -> tk.Frame:
        tab = tk.Frame(self, bg=PALETTE["surface"], padx=16, pady=16)
        bar = tk.Frame(tab, bg=PALETTE["surface"])
        bar.pack(fill=tk.X, pady=(0, 8))
        make_button(bar, "➕ Ajouter images...", self._add_images, variant="primary").pack(
            side=tk.LEFT, padx=(0, 6)
        )
        make_button(bar, "❌ Retirer", self._remove_image, variant="danger").pack(
            side=tk.LEFT, padx=2
        )
        make_button(bar, "🧹 Vider", self._clear_images).pack(side=tk.LEFT, padx=2)
        self.i2p_list = tk.Listbox(tab, font=("Segoe UI", 10), height=9)
        self.i2p_list.pack(expand=True, fill=tk.BOTH, pady=(0, 10))
        make_button(tab, "📄 Créer le PDF...", self._run_i2p, variant="success").pack(anchor="e")
        return tab

    def _add_images(self) -> None:
        files = filedialog.askopenfilenames(
            title="Images", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")]
        )
        for path in files:
            if path not in self.img_list:
                self.img_list.append(path)
                self.i2p_list.insert(tk.END, os.path.basename(path))

    def _remove_image(self) -> None:
        sel = self.i2p_list.curselection()
        if sel:
            self.img_list.pop(sel[0])
            self.i2p_list.delete(sel[0])

    def _clear_images(self) -> None:
        self.img_list.clear()
        self.i2p_list.delete(0, tk.END)

    def _run_p2i(self) -> None:
        pdf_path = self.p2i_var.get().strip()
        folder = filedialog.askdirectory(title="Dossier cible") if os.path.exists(pdf_path) else ""
        if folder:
            fmt, dpi = self.p2i_fmt.get(), self.p2i_dpi.get()
            self.ctx.runner.run(
                lambda: enhancements.pdf_to_images(pdf_path, folder, fmt=fmt, dpi=dpi),
                lambda res: messagebox.showinfo("Succès", f"{len(res)} image(s) exportée(s)."),
                status_msg="Export en images...",
            )

    def _run_i2p(self) -> None:
        if not self.img_list:
            messagebox.showwarning("Attention", "Ajoutez au moins une image.")
            return
        out = filedialog.asksaveasfilename(
            title="Créer PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
        )
        if out:
            self.ctx.runner.run(
                lambda: enhancements.images_to_pdf(self.img_list, out),
                lambda cnt: messagebox.showinfo("Succès", f"PDF créé ({cnt} pages)."),
                status_msg="Assemblage du PDF...",
            )


class SecurityPane(tk.Frame):
    """Panneau chiffrement AES-256, déverrouillage, compression et extraction."""

    def __init__(self, parent: tk.Misc, ctx: AppContext, picker_builder):
        super().__init__(
            parent,
            bg=PALETTE["surface"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            padx=18,
            pady=16,
        )
        self.ctx = ctx
        self.sec_var = tk.StringVar()
        picker_builder(self, self.sec_var)
        self.protect_pw, self.unlock_pw = tk.StringVar(), tk.StringVar()
        self._build_sections()

    def sync_active(self) -> None:
        self.sec_var.set(self.ctx.session.working_path or "")

    def _build_sections(self) -> None:
        for spec in (
            _PwSectionSpec(
                " 🔒 1. Protéger avec mot de passe (AES-256) ",
                "Mot de passe :",
                self.protect_pw,
                "Chiffrer...",
                self._run_protect,
                "primary",
            ),
            _PwSectionSpec(
                " 🔓 2. Déverrouiller un PDF protégé ",
                "Mot de passe actuel :",
                self.unlock_pw,
                "Déverrouiller...",
                self._run_unlock,
                "neutral",
            ),
        ):
            self._build_pw_block(spec)

        tools_box = tk.LabelFrame(
            self,
            text=" ⚡ 3. Optimisation & Extraction ",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["surface"],
            padx=12,
            pady=10,
        )
        tools_box.pack(fill=tk.X)
        make_button(
            tools_box, "🗜️ Compresser le PDF", self._run_compress, variant="success"
        ).pack(side=tk.LEFT, padx=(0, 10))
        make_button(
            tools_box, "📝 Extraire texte (.txt)", self._run_extract_text, variant="info"
        ).pack(side=tk.LEFT)

    def _build_pw_block(self, spec: _PwSectionSpec) -> None:
        box = tk.LabelFrame(
            self,
            text=spec.title,
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["surface"],
            padx=12,
            pady=10,
        )
        box.pack(fill=tk.X, pady=(0, 12))
        tk.Label(box, text=spec.label, bg=PALETTE["surface"]).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(box, textvariable=spec.var, show="*", width=24).pack(
            side=tk.LEFT, padx=(0, 12)
        )
        make_button(box, spec.btn_text, spec.command, variant=spec.variant).pack(side=tk.LEFT)

    def _run_protect(self) -> None:
        src, pw = self.sec_var.get().strip(), self.protect_pw.get().strip()
        if not os.path.exists(src) or not pw:
            messagebox.showwarning("Attention", "Fichier valide et mot de passe requis.")
            return
        out = filedialog.asksaveasfilename(
            title="Enregistrer protégé", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
        )
        if out:
            security.protect_pdf(src, out, pw)
            messagebox.showinfo("Succès", f"PDF chiffré en AES-256 :\n{out}")

    def _run_unlock(self) -> None:
        src, pw = self.sec_var.get().strip(), self.unlock_pw.get().strip()
        if not os.path.exists(src):
            return
        out = filedialog.asksaveasfilename(
            title="Enregistrer déverrouillé",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if out:
            if security.unlock_pdf(src, out, pw):
                messagebox.showinfo("Succès", f"PDF déverrouillé :\n{out}")
            else:
                messagebox.showerror("Échec", "Mot de passe incorrect.")

    def _run_compress(self) -> None:
        src = self.sec_var.get().strip()
        if not os.path.exists(src):
            return
        out = filedialog.asksaveasfilename(
            title="Enregistrer compressé", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
        )
        if out:
            self.ctx.runner.run(
                lambda: optimization.compress_pdf(src, out),
                lambda st: messagebox.showinfo("Succès", f"Gain : {st.reduction_percentage:.1f}%"),
                status_msg="Compression en cours...",
            )

    def _run_extract_text(self) -> None:
        src = self.sec_var.get().strip()
        if not os.path.exists(src):
            return
        out = filedialog.asksaveasfilename(
            title="Enregistrer texte", defaultextension=".txt", filetypes=[("Texte", "*.txt")]
        )
        if out:
            self.ctx.runner.run(
                lambda: optimization.extract_text_from_pdf(src, out),
                lambda txt: messagebox.showinfo("Succès", f"{len(txt)} caractères extraits."),
                status_msg="Extraction du texte...",
            )


class ToolsView(BaseView):
    """Conteneur léger hébergeant Images <-> PDF ou Sécurité & Optimisation."""

    def __init__(self, parent: tk.Misc, ctx: AppContext, mode: str = "security"):
        super().__init__(parent, ctx)
        if mode == "convert":
            make_view_header(
                self,
                "Images ↔ PDF",
                "Exportez vos pages en images HD ou assemblez des images en PDF.",
            )
            self.pane = ConvertPane(self, ctx, self.build_target_pdf_picker)
        else:
            make_view_header(
                self,
                "Sécurité & Optimisation",
                "Protégez par mot de passe AES-256, compressez ou extrayez le texte brut.",
            )
            self.pane = SecurityPane(self, ctx, self.build_target_pdf_picker)
        self.pane.pack(expand=True, fill=tk.BOTH)

    def on_document_updated(self) -> None:
        self.pane.sync_active()
