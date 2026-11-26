"""
app_gui.py - Application bureau PDF Studio Express (Tkinter modulaire).
Coquille légère coordonnant la barre Document Actif unifiée et les vues `ui/gui/`.
"""

import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import Dict

from core.session import DocumentSession
from ui.gui.assemble_view import AssembleView
from ui.gui.async_runner import AsyncTaskRunner
from ui.gui.base_view import AppContext, BaseView, SidebarNav
from ui.gui.pages_view import PagesView
from ui.gui.text_view import TextEditView
from ui.gui.tools_view import ToolsView
from ui.gui.watermark_view import WatermarkView
from ui.theme import PALETTE, configure_ttk_styles, make_button

logger = logging.getLogger(__name__)


def _enable_windows_dpi_awareness() -> None:
    """Active le rendu haute définition DPI sur Windows lorsque disponible."""
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError) as exc:
        logger.debug("DPI awareness non appliqué : %s", exc)


class PDFEditorApp(tk.Tk):
    """Fenêtre principale épurée de PDF Studio Express."""

    def __init__(self):
        super().__init__()
        self.title("PDF Studio Express — Éditeur PDF Complet")
        self.geometry("1240x800")
        self.minsize(1040, 680)
        self.configure(bg=PALETTE["bg"])

        configure_ttk_styles(self)
        self.session = DocumentSession()
        self.runner = AsyncTaskRunner(self, self.set_status)
        self.ctx = AppContext(
            session=self.session,
            runner=self.runner,
            set_status=self.set_status,
            on_document_changed=self._on_document_changed,
        )

        self.views: Dict[str, BaseView] = {}
        self.current_tab: str = "pages"

        self._build_layout()
        self._bind_shortcuts()
        self.show_tab("pages")
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_layout(self) -> None:
        self.sidebar = SidebarNav(self, self.show_tab)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        for sec, items in (
            ("ÉDITION", [("pages", "📑 Pages & Ordre"), ("text_edit", "✏️ Éditer le Texte")]),
            ("ASSEMBLAGE", [("assemble", "🔗 Fusion & Découpe")]),
            (
                "OUTILS & EXPORT",
                [
                    ("watermark", "🏷️ Filigrane & N°"),
                    ("convert", "🖼️ Images ↔ PDF"),
                    ("security", "🔒 Sécurité & Taille"),
                ],
            ),
        ):
            self.sidebar.add_section(sec, items)

        right = tk.Frame(self, bg=PALETTE["bg"])
        right.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        self._build_top_doc_bar(right)
        self.container = tk.Frame(right, bg=PALETTE["bg"], padx=18, pady=12)
        self.container.pack(expand=True, fill=tk.BOTH)
        self._register_views()

        self.lbl_status = tk.Label(
            right,
            text="Prêt.",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg=PALETTE["text_dark"],
            anchor="w",
            padx=12,
            pady=4,
        )
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_top_doc_bar(self, parent: tk.Frame) -> None:
        bar = tk.Frame(
            parent,
            bg=PALETTE["surface"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            padx=14,
            pady=8,
        )
        bar.pack(fill=tk.X)
        self.lbl_doc_badge = tk.Label(
            bar,
            text="📄 Aucun document ouvert",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["surface"],
            fg=PALETTE["text_muted"],
        )
        self.lbl_doc_badge.pack(side=tk.LEFT)
        make_button(bar, "💾 Enregistrer", self.save_document_as, variant="success").pack(
            side=tk.RIGHT, padx=(6, 0)
        )
        make_button(bar, "↪ Rétablir", self.redo_action).pack(side=tk.RIGHT, padx=2)
        make_button(bar, "↩ Annuler", self.undo_action).pack(side=tk.RIGHT, padx=2)
        make_button(bar, "📄 Exemple", self.load_sample_document, variant="info").pack(
            side=tk.RIGHT, padx=(2, 8)
        )
        make_button(bar, "📂 Ouvrir...", self.open_pdf_dialog, variant="primary").pack(
            side=tk.RIGHT, padx=2
        )

    def _register_views(self) -> None:
        self.views["pages"] = PagesView(
            self.container, self.ctx, self.open_pdf_dialog, self.load_sample_document
        )
        self.views["text_edit"] = TextEditView(self.container, self.ctx)
        self.views["assemble"] = AssembleView(self.container, self.ctx)
        self.views["watermark"] = WatermarkView(self.container, self.ctx)
        self.views["convert"] = ToolsView(self.container, self.ctx, mode="convert")
        self.views["security"] = ToolsView(self.container, self.ctx, mode="security")

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-o>", lambda _e: self.open_pdf_dialog())
        self.bind("<Control-s>", lambda _e: self.save_document_as())
        self.bind("<Control-z>", lambda _e: self.undo_action())
        self.bind("<Control-y>", lambda _e: self.redo_action())
        self.bind("<Control-f>", lambda _e: self.show_tab("text_edit"))

    def set_status(self, text: str, is_error: bool = False) -> None:
        fg = PALETTE["danger"] if is_error else PALETTE["text_dark"]
        self.lbl_status.config(text=f" {text}", fg=fg)

    def show_tab(self, tab_id: str) -> None:
        self.current_tab = tab_id
        for key, view in self.views.items():
            if key == tab_id:
                view.pack(expand=True, fill=tk.BOTH)
                view.on_activated()
            else:
                view.pack_forget()
        self.sidebar.set_active(tab_id)

    def open_pdf_dialog(self) -> None:
        path = filedialog.askopenfilename(
            title="Ouvrir un document PDF", filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if path:
            self.load_pdf(path)

    def load_sample_document(self) -> None:
        sample = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exemple_document.pdf")
        if os.path.exists(sample):
            self.load_pdf(sample)
        else:
            messagebox.showinfo("Information", "Fichier exemple_document.pdf introuvable.")

    def load_pdf(self, filepath: str, password: str = "") -> None:
        def on_ok(meta) -> None:
            if meta.is_encrypted and meta.page_count == 0:
                pw = simpledialog.askstring(
                    "PDF Protégé", "Mot de passe du document :", show="*", parent=self
                )
                if pw:
                    self.load_pdf(filepath, password=pw)
                return
            self._on_document_changed()

        self.runner.run(
            lambda: self.session.load_document(filepath, password=password),
            on_ok,
            status_msg=f"Ouverture de {os.path.basename(filepath)}...",
        )

    def _on_document_changed(self) -> None:
        src = self.session.source_path
        if src:
            pages = self.session.metadata.page_count
            dirty = " • ● Modifié" if self.session.is_dirty else " • ✓ À jour"
            self.lbl_doc_badge.config(
                text=f"📄 {os.path.basename(src)} ({pages} pages{dirty})",
                fg=PALETTE["text_dark"],
            )
        for view in self.views.values():
            view.on_document_updated()

    def undo_action(self) -> None:
        if self.session.undo():
            self.set_status("↩ Annulation effectuée.")
            self._on_document_changed()

    def redo_action(self) -> None:
        if self.session.redo():
            self.set_status("↪ Rétablissement effectué.")
            self._on_document_changed()

    def save_document_as(self) -> None:
        if not self.session.working_path:
            messagebox.showwarning("Attention", "Aucun PDF n'est ouvert.")
            return
        out = filedialog.asksaveasfilename(
            title="Enregistrer sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")],
        )
        if out:
            self.session.save_to(out)
            self._on_document_changed()
            self.set_status(f"Enregistré : {os.path.basename(out)}")
            messagebox.showinfo("Succès", f"Fichier enregistré :\n{out}")

    def _on_closing(self) -> None:
        self.runner.shutdown()
        self.session.close()
        self.destroy()


def main() -> None:
    _enable_windows_dpi_awareness()
    app = PDFEditorApp()
    sample = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exemple_document.pdf")
    if os.path.exists(sample):
        app.load_pdf(sample)
    app.mainloop()


if __name__ == "__main__":
    main()
