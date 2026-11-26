"""
ui/gui/text_view.py - Éditeur de texte interactif (clic sur aperçu, filtre, OCR).
"""

import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageTk

from core import text_editor
from core.models import SearchReplaceRequest, TextEditRequest, TextElement
from ui.gui.base_view import AppContext, BaseView
from ui.theme import PALETTE, make_button, make_card, make_view_header

_PREVIEW_SCALE = 1.35


class PreviewCanvasPane(tk.Frame):
    """Panneau d'aperçu PDF interactif avec surlignage de la zone sélectionnée."""

    def __init__(self, parent: tk.Misc, on_click_cb: Callable[[float, float], None]):
        super().__init__(
            parent,
            bg=PALETTE["surface"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            padx=10,
            pady=10,
        )
        self.on_click_cb = on_click_cb
        self.base_img: Optional[Image.Image] = None
        self.tk_img: Optional[ImageTk.PhotoImage] = None
        self._build()

    def _build(self) -> None:
        tk.Label(
            self,
            text="Aperçu interactif (cliquez sur un texte pour le sélectionner) :",
            font=("Segoe UI", 9, "bold"),
            bg=PALETTE["surface"],
        ).pack(anchor="w", pady=(0, 6))
        wrap = tk.Frame(self, bg=PALETTE["surface_alt"], bd=1, relief=tk.SOLID)
        wrap.pack(expand=True, fill=tk.BOTH)
        self.canvas = tk.Canvas(wrap, bg="#cbd5e1", highlightthickness=0, cursor="crosshair")
        sy = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.canvas.yview)
        sx = ttk.Scrollbar(wrap, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        sx.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.canvas.bind("<Button-1>", self._handle_click)

    def _handle_click(self, event: tk.Event) -> None:
        pdf_x = self.canvas.canvasx(event.x) / _PREVIEW_SCALE
        pdf_y = self.canvas.canvasy(event.y) / _PREVIEW_SCALE
        self.on_click_cb(pdf_x, pdf_y)

    def clear(self) -> None:
        self.base_img = None
        self.canvas.delete("all")

    def render(self, img: Image.Image, highlight_elem: Optional[TextElement] = None) -> None:
        self.base_img = img
        self.redraw(highlight_elem)

    def redraw(self, highlight_elem: Optional[TextElement] = None) -> None:
        if self.base_img is None:
            return
        canvas_img = self.base_img.copy()
        if highlight_elem is not None:
            draw = ImageDraw.Draw(canvas_img)
            x0, y0, x1, y1 = [v * _PREVIEW_SCALE for v in highlight_elem.bbox]
            draw.rectangle([x0 - 3, y0 - 2, x1 + 3, y1 + 2], outline="#2563eb", width=3)
        self.tk_img = ImageTk.PhotoImage(canvas_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")
        self.canvas.config(scrollregion=(0, 0, canvas_img.width, canvas_img.height))


class SearchReplacePane(tk.LabelFrame):
    """Panneau dédié à la recherche & remplacement globale."""

    def __init__(self, parent: tk.Misc, on_execute: Callable[[str, str, str], None]):
        super().__init__(
            parent,
            text=" 🔍 2. Rechercher & Remplacer partout ",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["surface"],
            padx=10,
            pady=8,
        )
        self.find_var = tk.StringVar()
        self.rep_var = tk.StringVar()
        self.scope_var = tk.StringVar(value="page")
        self.on_execute = on_execute
        self._build()

    def _build(self) -> None:
        for label, var in (("Rechercher :", self.find_var), ("Remplacer par :", self.rep_var)):
            row = tk.Frame(self, bg=PALETTE["surface"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=label, width=13, anchor="w", bg=PALETTE["surface"]).pack(
                side=tk.LEFT
            )
            ttk.Entry(row, textvariable=var).pack(side=tk.LEFT, expand=True, fill=tk.X)

        opts = tk.Frame(self, bg=PALETTE["surface"])
        opts.pack(fill=tk.X, pady=(6, 0))
        tk.Radiobutton(
            opts, text="Cette page", variable=self.scope_var, value="page", bg=PALETTE["surface"]
        ).pack(side=tk.LEFT)
        tk.Radiobutton(
            opts, text="Tout le PDF", variable=self.scope_var, value="all", bg=PALETTE["surface"]
        ).pack(side=tk.LEFT, padx=(8, 0))
        make_button(opts, "🔍 Remplacer partout", self._submit, variant="info").pack(
            side=tk.RIGHT
        )

    def _submit(self) -> None:
        self.on_execute(
            self.find_var.get().strip(),
            self.rep_var.get().strip(),
            self.scope_var.get(),
        )


class TextEditView(BaseView):
    """Vue d'édition directe de texte avec sélection sur l'aperçu PDF."""

    def __init__(self, parent: tk.Misc, ctx: AppContext):
        super().__init__(parent, ctx)
        self.current_page: int = 0
        self.elements: List[TextElement] = []
        self.selected_id: Optional[int] = None
        self._build_ui()

    def _build_ui(self) -> None:
        make_view_header(
            self,
            "Éditer le Texte Existant",
            "Cliquez sur une ligne dans l'aperçu ou filtrez la liste pour modifier.",
        )
        bar = make_card(self, padx=10, pady=8)
        bar.pack(fill=tk.X, pady=(0, 10))
        make_button(bar, "◀ Page préc.", lambda: self._shift_page(-1)).pack(side=tk.LEFT, padx=3)
        self.lbl_page = tk.Label(
            bar, text="Page 1 / 1", font=("Segoe UI", 10, "bold"), bg=PALETTE["surface"]
        )
        self.lbl_page.pack(side=tk.LEFT, padx=10)
        make_button(bar, "Page suiv. ▶", lambda: self._shift_page(1)).pack(side=tk.LEFT, padx=3)
        make_button(
            bar, "🔍 Forcer Scan OCR", lambda: self.refresh_page(force_ocr=True), variant="info"
        ).pack(side=tk.RIGHT)

        paned = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, bg=PALETTE["bg"], sashrelief=tk.FLAT, sashwidth=6
        )
        paned.pack(expand=True, fill=tk.BOTH)
        self.preview = PreviewCanvasPane(paned, self._on_pdf_point_clicked)
        paned.add(self.preview, minsize=400, width=500)
        paned.add(self._build_editor_panel(paned), minsize=430)

    def _build_editor_panel(self, parent: tk.Misc) -> tk.Frame:
        box = make_card(parent, padx=12, pady=10)
        sec = tk.LabelFrame(
            box,
            text=" 📝 1. Remplacer une ligne détectée ",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["surface"],
            padx=10,
            pady=8,
        )
        sec.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self._build_filter_and_tree(sec)
        self._build_replacement_controls(sec)
        SearchReplacePane(box, self._apply_search_replace).pack(fill=tk.X)
        return box

    def _build_filter_and_tree(self, parent: tk.Misc) -> None:
        row = tk.Frame(parent, bg=PALETTE["surface"])
        row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row, text="🔎 Filtrer :", bg=PALETTE["surface"]).pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_args: self._populate_tree())
        ttk.Entry(row, textvariable=self.filter_var).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(6, 0)
        )

        wrap = tk.Frame(parent, bg=PALETTE["surface"])
        wrap.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        self.tree = ttk.Treeview(
            wrap, columns=("text", "font", "size"), show="headings", height=5, selectmode="browse"
        )
        cols = (("text", "Texte actuel", 220), ("font", "Police", 100), ("size", "Taille", 55))
        for col, title, w in cols:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor="w" if col == "text" else "center")
        scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_selected)

    def _build_replacement_controls(self, parent: tk.Misc) -> None:
        self.lbl_font_badge = tk.Label(
            parent,
            text="Cliquez sur l'aperçu ou dans la liste ci-dessus.",
            font=("Segoe UI", 8, "italic"),
            bg="#f1f5f9",
            fg="#475569",
            padx=8,
            pady=4,
        )
        self.lbl_font_badge.pack(fill=tk.X, pady=(0, 6))
        tk.Label(
            parent, text="Nouveau texte :", font=("Segoe UI", 9, "bold"), bg=PALETTE["surface"]
        ).pack(anchor="w")
        self.new_text_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.new_text_var).pack(fill=tk.X, pady=(2, 6))

        bottom = tk.Frame(parent, bg=PALETTE["surface"])
        bottom.pack(fill=tk.X)
        self.white_bg_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            bottom, text="Fond opaque", variable=self.white_bg_var, bg=PALETTE["surface"]
        ).pack(side=tk.LEFT)
        make_button(
            bottom, "✏️ Remplacer (Auto-ajusté)", self._apply_line_edit, variant="primary"
        ).pack(side=tk.RIGHT)

    def on_activated(self) -> None:
        self.refresh_page()

    def on_document_updated(self) -> None:
        if self.winfo_ismapped():
            self.refresh_page()

    def refresh_page(self, force_ocr: bool = False) -> None:
        path = self.ctx.session.working_path
        if not path or not os.path.exists(path):
            self.preview.clear()
            self.elements = []
            self._populate_tree()
            return

        def worker():
            doc = fitz.open(path)
            total = len(doc)
            idx = max(0, min(self.current_page, max(total - 1, 0)))
            pix = doc[idx].get_pixmap(matrix=fitz.Matrix(_PREVIEW_SCALE, _PREVIEW_SCALE))
            doc.close()
            pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            return total, idx, pil_img, text_editor.get_page_text_elements(path, idx, force_ocr)

        def on_ok(res) -> None:
            total, idx, pil_img, elems = res
            self.current_page, self.elements, self.selected_id = idx, elems, None
            self.lbl_page.config(text=f"Page {idx + 1} / {total}")
            self.preview.render(pil_img, None)
            self._populate_tree()
            self.ctx.set_status(f"{len(elems)} ligne(s) détectée(s).", False)

        self.ctx.runner.run(
            worker,
            on_ok,
            status_msg="Scan OCR en cours..." if force_ocr else "Lecture de la page...",
        )

    def _populate_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        query = self.filter_var.get().strip().lower()
        for elem in self.elements:
            if not query or query in elem.text.lower():
                self.tree.insert(
                    "", "end", iid=str(elem.id), values=(elem.text, elem.font, f"{elem.size} pt")
                )

    def _on_pdf_point_clicked(self, pdf_x: float, pdf_y: float) -> None:
        for elem in self.elements:
            x0, y0, x1, y1 = elem.bbox
            if (x0 - 4) <= pdf_x <= (x1 + 4) and (y0 - 4) <= pdf_y <= (y1 + 4):
                iid = str(elem.id)
                if self.tree.exists(iid):
                    self.tree.selection_set(iid)
                    self.tree.see(iid)
                self._select_element(elem)
                return

    def _on_tree_selected(self, _event: tk.Event) -> None:
        sel = self.tree.selection()
        if sel:
            elem = next((e for e in self.elements if e.id == int(sel[0])), None)
            if elem:
                self._select_element(elem)

    def _select_element(self, elem: TextElement) -> None:
        self.selected_id = elem.id
        self.new_text_var.set(elem.text)
        self.lbl_font_badge.config(
            text=f"✨ {elem.font} • {elem.size} pt • {elem.color_hex} (auto-fit actif)"
        )
        self.preview.redraw(elem)

    def _shift_page(self, delta: int) -> None:
        nxt = self.current_page + delta
        if 0 <= nxt < self.ctx.session.metadata.page_count:
            self.current_page = nxt
            self.refresh_page()

    def _apply_line_edit(self) -> None:
        elem = next((e for e in self.elements if e.id == self.selected_id), None)
        new_text = self.new_text_var.get().strip()
        src = self.ctx.session.working_path
        if not elem or not new_text or not src:
            messagebox.showinfo("Information", "Sélectionnez une ligne et entrez un texte.")
            return

        tmp_out = self.ctx.session.temp_manager.create_temp_file(suffix=".pdf")
        req = TextEditRequest(
            page_num=self.current_page,
            elem_bbox=elem.bbox,
            new_text=new_text,
            elem_origin=elem.origin,
            font_name=elem.font,
            font_size=elem.size,
            font_flags=elem.flags,
            font_color=elem.color_rgb,
            use_white_bg=self.white_bg_var.get(),
            is_ocr=elem.is_ocr,
            bg_color_rgb=elem.bg_color_rgb,
        )
        self.ctx.runner.run(
            lambda: (
                text_editor.replace_text_element(src, tmp_out, req),
                self.ctx.session.commit_working_copy(tmp_out),
            ),
            lambda _r: (
                self.ctx.set_status("Texte remplacé (Ctrl+Z pour annuler).", False),
                self.ctx.on_document_changed(),
            ),
            status_msg="Remplacement du texte...",
        )

    def _apply_search_replace(self, search_str: str, replace_str: str, scope: str) -> None:
        src = self.ctx.session.working_path
        if not search_str or not src:
            messagebox.showwarning("Attention", "Ouvrez un PDF et entrez le texte recherché.")
            return

        tmp_out = self.ctx.session.temp_manager.create_temp_file(suffix=".pdf")
        req = SearchReplaceRequest(
            search_text=search_str,
            replace_text=replace_str,
            target_page=self.current_page if scope == "page" else None,
        )

        def worker() -> int:
            cnt = text_editor.search_and_replace_text(src, tmp_out, req)
            if cnt > 0:
                self.ctx.session.commit_working_copy(tmp_out)
            else:
                self.ctx.session.temp_manager.remove_file(tmp_out)
            return cnt

        def on_ok(cnt: int) -> None:
            if cnt == 0:
                messagebox.showinfo("Résultat", f"« {search_str} » introuvable.")
                return
            self.ctx.set_status(f"{cnt} occurrence(s) remplacée(s).", False)
            self.ctx.on_document_changed()

        self.ctx.runner.run(worker, on_ok, status_msg=f"Remplacement de « {search_str} »...")
