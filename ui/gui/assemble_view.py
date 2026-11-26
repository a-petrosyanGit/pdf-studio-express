"""
ui/gui/assemble_view.py - Vues Fusionner et Découper regroupées proprement.
"""

import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List

from core import pages as core_pages
from ui.gui.base_view import AppContext, BaseView
from ui.theme import PALETTE, make_button, make_view_header

logger = logging.getLogger(__name__)


def _describe_pdf_file(path: str):
    try:
        meta = core_pages.get_pdf_metadata(path)
        return meta.page_count, f"{os.path.getsize(path) / 1024.0:.1f} Ko"
    except Exception as exc:
        logger.debug("Analyse PDF ignorée (%s) : %s", path, exc)
        return "?", "0 Ko"


class MergePane(tk.Frame):
    """Panneau de fusion multi-PDF."""

    def __init__(self, parent: tk.Misc, ctx: AppContext):
        super().__init__(parent, bg=PALETTE["surface"], padx=16, pady=14)
        self.ctx = ctx
        self.merge_files: List[str] = []
        self._build_ui()

    def _build_ui(self) -> None:
        bar = tk.Frame(self, bg=PALETTE["surface"])
        bar.pack(fill=tk.X, pady=(0, 10))
        make_button(bar, "➕ Ajouter PDF...", self._add, variant="primary").pack(
            side=tk.LEFT, padx=(0, 6)
        )
        make_button(bar, "⬆ Monter", lambda: self._move(-1)).pack(side=tk.LEFT, padx=2)
        make_button(bar, "⬇ Descendre", lambda: self._move(1)).pack(side=tk.LEFT, padx=2)
        make_button(bar, "❌ Retirer", self._remove, variant="danger").pack(side=tk.LEFT, padx=2)
        make_button(bar, "🧹 Vider", self._clear).pack(side=tk.LEFT, padx=2)

        wrap = tk.Frame(self, bg=PALETTE["surface"])
        wrap.pack(expand=True, fill=tk.BOTH)
        self.tree = ttk.Treeview(
            wrap, columns=("num", "name", "pages", "size"), show="headings", selectmode="browse"
        )
        for col, title, width in (
            ("num", "#", 45),
            ("name", "Nom du fichier", 340),
            ("pages", "Pages", 80),
            ("size", "Taille", 100),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center" if col != "name" else "w")
        scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        bottom = tk.Frame(self, bg=PALETTE["surface"], pady=10)
        bottom.pack(fill=tk.X)
        self.lbl_sum = tk.Label(
            bottom, text="0 fichier sélectionné.", bg=PALETTE["surface"], fg="#475569"
        )
        self.lbl_sum.pack(side=tk.LEFT)
        make_button(
            bottom, "🚀 Fusionner et enregistrer...", self._execute, variant="success"
        ).pack(side=tk.RIGHT)

    def _add(self) -> None:
        files = filedialog.askopenfilenames(
            title="Ajouter des PDF", filetypes=[("Fichiers PDF", "*.pdf")]
        )
        for path in files:
            if path not in self.merge_files:
                self.merge_files.append(path)
        self._refresh()

    def _refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        total_pages = 0
        for idx, path in enumerate(self.merge_files):
            pages_txt, size_txt = _describe_pdf_file(path)
            if isinstance(pages_txt, int):
                total_pages += pages_txt
            self.tree.insert(
                "", "end", values=(idx + 1, os.path.basename(path), pages_txt, size_txt)
            )
        self.lbl_sum.config(text=f"{len(self.merge_files)} fichier(s) | ~{total_pages} pages")

    def _move(self, delta: int) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        nxt = idx + delta
        if 0 <= nxt < len(self.merge_files):
            self.merge_files[idx], self.merge_files[nxt] = (
                self.merge_files[nxt],
                self.merge_files[idx],
            )
            self._refresh()
            self.tree.selection_set(self.tree.get_children()[nxt])

    def _remove(self) -> None:
        sel = self.tree.selection()
        if sel:
            self.merge_files.pop(self.tree.index(sel[0]))
            self._refresh()

    def _clear(self) -> None:
        self.merge_files.clear()
        self._refresh()

    def _execute(self) -> None:
        if len(self.merge_files) < 2:
            messagebox.showinfo("Information", "Sélectionnez au moins 2 fichiers PDF.")
            return
        out = filedialog.asksaveasfilename(
            title="Enregistrer la fusion",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")],
        )
        if out:
            self.ctx.runner.run(
                lambda: core_pages.merge_pdfs(self.merge_files, out),
                lambda total: messagebox.showinfo(
                    "Succès", f"Fusion réussie ({total} pages) :\n{out}"
                ),
                status_msg="Fusion des documents...",
            )


class SplitPane(tk.Frame):
    """Panneau de découpage et d'extraction de pages."""

    def __init__(self, parent: tk.Misc, ctx: AppContext, picker_builder):
        super().__init__(parent, bg=PALETTE["surface"], padx=18, pady=16)
        self.ctx = ctx
        self.file_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="range")
        self.range_var = tk.StringVar(value="1-2")
        self.n_var = tk.IntVar(value=2)
        picker_builder(self, self.file_var, "1. Fichier PDF à découper :", self._inspect)
        self.lbl_info = tk.Label(
            self,
            text="Document actif sélectionné automatiquement.",
            font=("Segoe UI", 9, "italic"),
            bg=PALETTE["surface"],
            fg=PALETTE["text_muted"],
        )
        self.lbl_info.pack(anchor="w", pady=(0, 12))
        self._build_modes()
        make_button(
            self, "✂️ Exécuter le découpage...", self._execute, variant="primary", pady=8
        ).pack(anchor="e", pady=(12, 0))

    def _build_modes(self) -> None:
        tk.Label(
            self,
            text="2. Méthode de découpage :",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["surface"],
        ).pack(anchor="w", pady=(0, 6))
        tk.Radiobutton(
            self,
            text="Plages précises (ex : 1-3, 5)",
            variable=self.mode_var,
            value="range",
            bg=PALETTE["surface"],
        ).pack(anchor="w")
        r_row = tk.Frame(self, bg=PALETTE["surface"], padx=24)
        r_row.pack(fill=tk.X, pady=(2, 8))
        ttk.Entry(r_row, textvariable=self.range_var, width=26).pack(side=tk.LEFT)

        tk.Radiobutton(
            self,
            text="Une page par fichier PDF",
            variable=self.mode_var,
            value="all_pages",
            bg=PALETTE["surface"],
        ).pack(anchor="w", pady=4)
        tk.Radiobutton(
            self,
            text="Par blocs réguliers de N pages",
            variable=self.mode_var,
            value="every_n",
            bg=PALETTE["surface"],
        ).pack(anchor="w")
        n_row = tk.Frame(self, bg=PALETTE["surface"], padx=24)
        n_row.pack(fill=tk.X, pady=(2, 8))
        ttk.Spinbox(n_row, from_=1, to=100, textvariable=self.n_var, width=8).pack(
            side=tk.LEFT
        )

    def sync_active(self) -> None:
        if self.ctx.session.working_path:
            self.file_var.set(self.ctx.session.working_path)
            count = self.ctx.session.metadata.page_count
            self.lbl_info.config(text=f"Document actif : {count} page(s)")
            self.range_var.set(f"1-{min(3, max(1, count))}")

    def _inspect(self, path: str) -> None:
        try:
            meta = core_pages.get_pdf_metadata(path, password=self.ctx.session.password)
            self.lbl_info.config(text=f"Total : {meta.page_count} page(s)")
            self.range_var.set(f"1-{min(3, max(1, meta.page_count))}")
        except Exception as exc:
            self.lbl_info.config(text=f"Erreur : {exc}")

    def _execute(self) -> None:
        path = self.file_var.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning("Attention", "Sélectionnez un document PDF valide.")
            return
        if self.mode_var.get() == "range":
            self._split_range(path)
        else:
            self._split_folder(path, self.mode_var.get())

    def _split_range(self, path: str) -> None:
        out = filedialog.asksaveasfilename(
            title="Enregistrer l'extrait",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")],
        )
        if out:
            rng = self.range_var.get().strip()
            self.ctx.runner.run(
                lambda: core_pages.split_pdf_by_range(path, rng, out),
                lambda cnt: messagebox.showinfo("Succès", f"{cnt} page(s) extraite(s) :\n{out}"),
                status_msg="Extraction des pages...",
            )

    def _split_folder(self, path: str, mode: str) -> None:
        folder = filedialog.askdirectory(title="Dossier de destination")
        if not folder:
            return
        prefix = os.path.splitext(os.path.basename(path))[0]
        worker = (
            (lambda: core_pages.split_pdf_all_pages(path, folder, prefix=prefix))
            if mode == "all_pages"
            else (
                lambda: core_pages.split_pdf_every_n_pages(
                    path, folder, n=self.n_var.get(), prefix=prefix
                )
            )
        )
        self.ctx.runner.run(
            worker,
            lambda files: messagebox.showinfo("Succès", f"{len(files)} fichier(s) créé(s)."),
            status_msg="Découpage en cours...",
        )


class AssembleView(BaseView):
    """Regroupe les onglets Fusionner et Découper."""

    def __init__(self, parent: tk.Misc, ctx: AppContext):
        super().__init__(parent, ctx)
        make_view_header(
            self,
            "Fusionner & Découper",
            "Assemblez plusieurs PDF en un document ou extrayez des pages précises.",
        )
        nb = ttk.Notebook(self)
        nb.pack(expand=True, fill=tk.BOTH)
        self.merge_pane = MergePane(nb, ctx)
        self.split_pane = SplitPane(nb, ctx, self.build_target_pdf_picker)
        nb.add(self.merge_pane, text="➕ Fusionner plusieurs PDF")
        nb.add(self.split_pane, text="✂️ Découper / Scinder")

    def on_document_updated(self) -> None:
        self.split_pane.sync_active()
