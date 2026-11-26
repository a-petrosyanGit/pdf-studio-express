"""
ui/gui/pages_view.py - Organiseur visuel de pages avec actions directes par vignette.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional, Set, Tuple
from PIL import Image, ImageTk

from core import pages as core_pages
from ui.gui.base_view import AppContext, BaseView
from ui.theme import PALETTE, make_button, make_view_header

ZOOM_PRESETS: Dict[str, Tuple[int, int]] = {
    "Petit (120x160)": (120, 160),
    "Moyen (160x220)": (160, 220),
    "Grand (220x300)": (220, 300),
}


def _render_welcome_screen(
    parent: tk.Frame,
    open_cb: Callable[[], None],
    example_cb: Callable[[], None],
) -> None:
    box = tk.Frame(parent, bg=PALETTE["surface_alt"], pady=70)
    box.pack(expand=True, fill=tk.BOTH)
    tk.Label(
        box,
        text="Bienvenue dans PDF Studio Express",
        font=("Segoe UI", 16, "bold"),
        bg=PALETTE["surface_alt"],
        fg=PALETTE["text_dark"],
    ).pack(pady=(0, 8))
    tk.Label(
        box,
        text="Ouvrez votre fichier PDF ou chargez l'exemple pour commencer :",
        font=("Segoe UI", 10),
        bg=PALETTE["surface_alt"],
        fg=PALETTE["text_muted"],
    ).pack(pady=(0, 18))

    btns = tk.Frame(box, bg=PALETTE["surface_alt"])
    btns.pack()
    make_button(btns, "📂 Ouvrir un PDF...", open_cb, variant="primary", padx=16, pady=8).pack(
        side=tk.LEFT, padx=6
    )
    make_button(
        btns, "📄 Tester avec l'exemple", example_cb, variant="info", padx=16, pady=8
    ).pack(side=tk.LEFT, padx=6)


class PageCardGrid(tk.Frame):
    """Grille défilable affichant les vignettes interactives des pages."""

    def __init__(self, parent: tk.Misc, callbacks: Dict[str, Callable]):
        super().__init__(
            parent,
            bg=PALETTE["surface"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
        )
        self.cb = callbacks
        self.tk_thumbs: List[ImageTk.PhotoImage] = []
        self.selected: Set[int] = set()
        self.thumb_size: Tuple[int, int] = (160, 220)
        self._build_canvas()

    def _build_canvas(self) -> None:
        self.canvas = tk.Canvas(self, bg=PALETTE["surface_alt"], highlightthickness=0)
        scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.grid_frame = tk.Frame(self.canvas, bg=PALETTE["surface_alt"])
        self.grid_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.window_id = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll_y.set)
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            if self.canvas.winfo_ismapped()
            else None,
        )
        self.canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event: tk.Event) -> None:
        self.canvas.itemconfig(self.window_id, width=event.width)
        self.redraw()

    def set_thumbs(self, thumbs: List[ImageTk.PhotoImage], thumb_size: Tuple[int, int]) -> None:
        self.tk_thumbs = thumbs
        self.thumb_size = thumb_size
        self.redraw()

    def redraw(self) -> None:
        for child in self.grid_frame.winfo_children():
            child.destroy()
        if not self.tk_thumbs:
            _render_welcome_screen(self.grid_frame, self.cb["open"], self.cb["example"])
            return

        canvas_w = max(self.canvas.winfo_width(), 640)
        card_w = max(self.thumb_size[0] + 44, 184)
        cols = max(1, canvas_w // (card_w + 16))
        for idx, tk_img in enumerate(self.tk_thumbs):
            self._build_card(idx, tk_img, idx // cols, idx % cols)

    def _build_card(self, idx: int, tk_img: ImageTk.PhotoImage, row: int, col: int) -> None:
        is_sel = idx in self.selected
        bg = PALETTE["card_selected"] if is_sel else PALETTE["surface"]
        border = PALETTE["card_selected_border"] if is_sel else PALETTE["border"]
        card = tk.Frame(
            self.grid_frame,
            bg=bg,
            highlightbackground=border,
            highlightthickness=2 if is_sel else 1,
            padx=8,
            pady=8,
            cursor="hand2",
        )
        card.grid(row=row, column=col, padx=8, pady=8, sticky="n")
        lbl_t = tk.Label(card, text=f"Page {idx + 1}", font=("Segoe UI", 10, "bold"), bg=bg)
        lbl_t.pack(anchor="w")
        lbl_i = tk.Label(card, image=tk_img, bg=bg)
        lbl_i.pack(pady=5)

        strip = tk.Frame(card, bg=bg)
        strip.pack(fill=tk.X, pady=(4, 0))
        for label, key, arg, variant in (
            ("◀", "move", -1, "neutral"),
            ("↺", "rotate", -90, "neutral"),
            ("↻", "rotate", 90, "neutral"),
            ("▶", "move", 1, "neutral"),
            ("🗑️", "delete", 0, "danger"),
        ):
            cmd = lambda k=key, i=idx, a=arg: self.cb[k](i, a)
            make_button(strip, label, cmd, variant=variant, padx=5, pady=2).pack(
                side=tk.LEFT, expand=True, fill=tk.X, padx=1
            )
        for w in (card, lbl_t, lbl_i):
            w.bind("<Button-1>", lambda e, i=idx: self._on_click(i, e))

    def _on_click(self, idx: int, event: tk.Event) -> None:
        if event.state & 0x0004 or event.state & 0x0001:
            self.selected.symmetric_difference_update({idx})
        else:
            self.selected = set() if self.selected == {idx} else {idx}
        self.redraw()


class PagesView(BaseView):
    """Vue d'organisation visuelle des pages du document PDF actif."""

    def __init__(
        self,
        parent: tk.Misc,
        ctx: AppContext,
        open_callback: Callable[[], None],
        load_example_callback: Callable[[], None],
    ):
        super().__init__(parent, ctx)
        self.thumb_size: Tuple[int, int] = (160, 220)
        make_view_header(
            self,
            "Organiseur Visuel de Pages",
            "Agissez directement sur chaque page ou sélectionnez plusieurs vignettes.",
        )
        self._build_toolbar()
        self.grid = PageCardGrid(
            self,
            {
                "open": open_callback,
                "example": load_example_callback,
                "move": self._move_single,
                "rotate": self._rotate_single,
                "delete": self._delete_single,
            },
        )
        self.grid.pack(expand=True, fill=tk.BOTH)

    def _build_toolbar(self) -> None:
        bar = tk.Frame(
            self,
            bg=PALETTE["surface"],
            highlightbackground=PALETTE["border"],
            highlightthickness=1,
            padx=10,
            pady=8,
        )
        bar.pack(fill=tk.X, pady=(0, 10))
        make_button(bar, "↺ -90°", lambda: self._rotate_selected(-90)).pack(side=tk.LEFT, padx=2)
        make_button(bar, "↻ +90°", lambda: self._rotate_selected(90)).pack(side=tk.LEFT, padx=2)
        make_button(bar, "🗑️ Suppr. sélec.", self._delete_selected, variant="danger").pack(
            side=tk.LEFT, padx=2
        )
        make_button(bar, "☑ Tout", self._toggle_select_all).pack(side=tk.LEFT, padx=2)
        make_button(bar, "📤 Extraire sélec.", self._export_selected, variant="info").pack(
            side=tk.RIGHT, padx=2
        )
        tk.Label(bar, text="🔍 Zoom :", font=("Segoe UI", 9), bg=PALETTE["surface"]).pack(
            side=tk.RIGHT, padx=(8, 2)
        )
        self.zoom_var = tk.StringVar(value="Moyen (160x220)")
        combo = ttk.Combobox(
            bar,
            textvariable=self.zoom_var,
            values=list(ZOOM_PRESETS.keys()),
            state="readonly",
            width=15,
        )
        combo.pack(side=tk.RIGHT, padx=2)
        combo.bind("<<ComboboxSelected>>", self._on_zoom_changed)

    def _on_zoom_changed(self, _event: Optional[tk.Event] = None) -> None:
        self.thumb_size = ZOOM_PRESETS.get(self.zoom_var.get(), (160, 220))
        self.on_document_updated()

    def on_document_updated(self) -> None:
        self.grid.selected.clear()
        working = self.ctx.session.working_path
        if not working or not os.path.exists(working):
            self.grid.set_thumbs([], self.thumb_size)
            return

        def on_ok(images: List[Image.Image]) -> None:
            tk_imgs = [ImageTk.PhotoImage(img) for img in images]
            self.grid.set_thumbs(tk_imgs, self.thumb_size)
            self.ctx.set_status(f"Prêt ({len(images)} pages).", False)

        self.ctx.runner.run(
            lambda: self.ctx.session.render_thumbnails(max_size=self.thumb_size),
            on_ok,
            status_msg="Rendu des miniatures...",
        )

    def _toggle_select_all(self) -> None:
        total = len(self.grid.tk_thumbs)
        self.grid.selected = set() if len(self.grid.selected) == total else set(range(total))
        self.grid.redraw()

    def _commit_pages(self, msg: str) -> None:
        self.ctx.runner.run(
            self.ctx.session.apply_page_modifications_to_working_copy,
            lambda _r: (self.ctx.set_status(msg, False), self.ctx.on_document_changed()),
            status_msg="Mise à jour des pages...",
        )

    def _rotate_single(self, idx: int, angle: int) -> None:
        self.ctx.session.rotate_page(idx, angle)
        self._commit_pages(f"Page {idx + 1} pivotée de {angle}°.")

    def _rotate_selected(self, angle: int) -> None:
        if not self.grid.selected:
            messagebox.showinfo("Information", "Sélectionnez au moins une page.")
            return
        for idx in self.grid.selected:
            self.ctx.session.rotate_page(idx, angle)
        self._commit_pages(f"Rotation appliquée sur {len(self.grid.selected)} page(s).")

    def _move_single(self, idx: int, delta: int) -> None:
        total = len(self.ctx.session.page_configs)
        target = idx + delta
        if 0 <= target < total:
            order = list(range(total))
            order[idx], order[target] = order[target], order[idx]
            self.ctx.session.reorder_pages(order)
            self._commit_pages(f"Page {idx + 1} déplacée.")

    def _delete_single(self, idx: int, _unused: int = 0) -> None:
        if len(self.ctx.session.page_configs) <= 1:
            messagebox.showwarning("Impossible", "Un PDF doit garder au moins 1 page.")
            return
        self.ctx.session.delete_page(idx)
        self._commit_pages(f"Page {idx + 1} supprimée (Ctrl+Z pour annuler).")

    def _delete_selected(self) -> None:
        sel = self.grid.selected
        if not sel or len(sel) >= len(self.ctx.session.page_configs):
            return
        if messagebox.askyesno("Confirmation", f"Supprimer {len(sel)} page(s) ?"):
            for idx in sorted(sel, reverse=True):
                self.ctx.session.delete_page(idx)
            self._commit_pages("Pages supprimées.")

    def _export_selected(self) -> None:
        working = self.ctx.session.working_path
        if not working or not self.grid.selected:
            messagebox.showinfo("Information", "Sélectionnez au moins une page.")
            return
        out = filedialog.asksaveasfilename(
            title="Extraire sélection", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
        )
        if out:
            configs = [self.ctx.session.page_configs[i] for i in sorted(self.grid.selected)]
            core_pages.apply_page_modifications(
                working, out, configs, password=self.ctx.session.password
            )
            messagebox.showinfo("Succès", f"{len(configs)} page(s) exportée(s) :\n{out}")
