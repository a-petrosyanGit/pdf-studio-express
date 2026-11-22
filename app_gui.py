"""
app_gui.py - Interface graphique moderne pour l'édition et la manipulation de PDF.
Application de bureau complète, rapide, intuitive et 100% autonome.
Inclut le remplacement et la modification de texte avec conservation de la même police.
"""

import os
import sys
import threading
import tempfile
from typing import List, Dict, Any, Optional, Tuple
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import fitz

import pdf_core

# Configuration du DPI awareness pour un affichage net sur Windows 10/11
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class PDFEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("PDF Studio Express - Éditeur PDF Simple & Complet")
        self.geometry("1220x780")
        self.minsize(1020, 660)

        # Couleurs du thème moderne
        self.colors = {
            "bg": "#f8fafc",
            "sidebar": "#0f172a",
            "sidebar_btn": "#1e293b",
            "sidebar_hover": "#334155",
            "sidebar_active": "#2563eb",
            "text_light": "#f8fafc",
            "text_muted": "#94a3b8",
            "card_bg": "#ffffff",
            "card_selected": "#dbeafe",
            "border": "#e2e8f0",
            "primary": "#2563eb",
            "primary_hover": "#1d4ed8",
            "success": "#16a34a",
            "danger": "#dc2626",
            "warning": "#d97706",
            "text_dark": "#0f172a"
        }

        self.configure(bg=self.colors["bg"])

        # État général du document ouvert
        self.current_pdf_path: Optional[str] = None
        self.current_pdf_password: str = ""
        # Fichier temporaire de travail pour accumuler les modifications de texte en direct
        self.working_pdf_path: Optional[str] = None

        # État de l'organiseur visuel
        self.pages_data: List[Dict[str, Any]] = []
        self.selected_indices: set = set()
        self.card_widgets: List[tk.Widget] = []

        # État de la modification de texte
        self.text_edit_page: int = 0
        self.text_elements: List[Dict[str, Any]] = []
        self.text_edit_preview_img: Optional[ImageTk.PhotoImage] = None

        # État de la fusion
        self.merge_files_list: List[str] = []

        # État de conversion images
        self.img_conv_list: List[str] = []

        self._init_styles()
        self._build_ui()

        # Raccourcis clavier
        self.bind("<Control-o>", lambda e: self._open_pdf_dialog())
        self.bind("<Control-s>", lambda e: self._save_modified_pdf())
        self.protocol("WM_DELETE_WINDOW", self._on_app_closing)

    def _on_app_closing(self):
        """Nettoie les fichiers temporaires à la fermeture de l'application."""
        if self.working_pdf_path and os.path.exists(self.working_pdf_path) and self.working_pdf_path != self.current_pdf_path:
            try:
                os.remove(self.working_pdf_path)
            except Exception:
                pass
        self.destroy()

    def _init_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure(".", font=("Segoe UI", 10), background=self.colors["bg"], foreground=self.colors["text_dark"])
        self.style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text_dark"])
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.colors["text_dark"])
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 10), foreground="#64748b")
        
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["primary"], foreground="#ffffff", padding=6)
        self.style.map("Primary.TButton",
            background=[("active", self.colors["primary_hover"])],
            foreground=[("active", "#ffffff")]
        )

        self.style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["success"], foreground="#ffffff", padding=6)
        self.style.map("Success.TButton", background=[("active", "#15803d")])

        self.style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["danger"], foreground="#ffffff", padding=6)
        self.style.map("Danger.TButton", background=[("active", "#b91c1c")])

        self.style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[12, 6], background="#e2e8f0")
        self.style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", self.colors["primary"])])

    def _build_ui(self):
        # 1. Barre latérale (Navigation)
        self.sidebar = tk.Frame(self, bg=self.colors["sidebar"], width=235)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Titre application dans la sidebar
        app_title_frame = tk.Frame(self.sidebar, bg=self.colors["sidebar"], pady=18, padx=14)
        app_title_frame.pack(fill=tk.X)
        
        lbl_app_icon = tk.Label(app_title_frame, text="⚡ PDF Studio", font=("Segoe UI", 15, "bold"), bg=self.colors["sidebar"], fg="#ffffff")
        lbl_app_icon.pack(anchor="w")
        lbl_app_sub = tk.Label(app_title_frame, text="Éditeur Simple & Complet", font=("Segoe UI", 8), bg=self.colors["sidebar"], fg=self.colors["text_muted"])
        lbl_app_sub.pack(anchor="w")

        tk.Frame(self.sidebar, bg="#1e293b", height=1).pack(fill=tk.X, padx=10, pady=5)

        # Boutons de navigation
        self.nav_buttons = {}
        tabs = [
            ("pages", "📑 Organiseur & Pages"),
            ("text_edit", "✏️ Modifier le Texte"),
            ("merge", "➕ Fusionner des PDF"),
            ("split", "✂️ Découper / Scinder"),
            ("watermark", "🏷️ Filigrane & Numéros"),
            ("convert", "🖼️ Images & PDF"),
            ("security", "🔒 Sécurité & Outils"),
        ]

        for tab_id, tab_label in tabs:
            btn = tk.Button(
                self.sidebar,
                text=tab_label,
                font=("Segoe UI", 10, "bold"),
                bg=self.colors["sidebar_btn"],
                fg=self.colors["text_light"],
                activebackground=self.colors["sidebar_active"],
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                padx=16,
                pady=10,
                anchor="w",
                cursor="hand2",
                command=lambda t=tab_id: self.show_tab(t)
            )
            btn.pack(fill=tk.X, padx=10, pady=3)
            self.nav_buttons[tab_id] = btn

        tk.Frame(self.sidebar, bg=self.colors["sidebar"]).pack(expand=True, fill=tk.BOTH)
        
        lbl_info = tk.Label(
            self.sidebar,
            text="Fait avec ❤️ pour simplifier\nvos documents PDF",
            font=("Segoe UI", 8),
            bg=self.colors["sidebar"],
            fg=self.colors["text_muted"],
            pady=15
        )
        lbl_info.pack(side=tk.BOTTOM)

        # 2. Zone principale
        self.main_container = tk.Frame(self, bg=self.colors["bg"])
        self.main_container.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        # Barre de statut inférieure
        self.status_bar = tk.Frame(self.main_container, bg="#ffffff", height=30, bd=1, relief=tk.SOLID)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_bar,
            text="Prêt. Ouvrez un PDF ou sélectionnez une action dans le menu.",
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#475569",
            padx=10
        )
        self.status_label.pack(side=tk.LEFT)

        # Pages / Vues de contenu
        self.content_frames: Dict[str, tk.Frame] = {}

        self.content_frames["pages"] = self._build_pages_tab()
        self.content_frames["text_edit"] = self._build_text_edit_tab()
        self.content_frames["merge"] = self._build_merge_tab()
        self.content_frames["split"] = self._build_split_tab()
        self.content_frames["watermark"] = self._build_watermark_tab()
        self.content_frames["convert"] = self._build_convert_tab()
        self.content_frames["security"] = self._build_security_tab()

        self.show_tab("pages")

    def set_status(self, text: str, is_error: bool = False):
        color = self.colors["danger"] if is_error else "#475569"
        self.status_label.config(text=text, fg=color)

    def show_tab(self, tab_id: str):
        for name, frame in self.content_frames.items():
            if name == tab_id:
                frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=15)
                self.nav_buttons[name].config(bg=self.colors["sidebar_active"], fg="#ffffff")
            else:
                frame.pack_forget()
                self.nav_buttons[name].config(bg=self.colors["sidebar_btn"], fg=self.colors["text_light"])

        # Si on passe sur l'onglet de modification de texte, rafraîchir la page actuelle
        if tab_id == "text_edit":
            self._text_edit_refresh_page()

    # -------------------------------------------------------------
    # ONGLET 1 : ORGANISEUR VISUEL DE PAGES
    # -------------------------------------------------------------
    def _build_pages_tab(self) -> tk.Frame:
        frame = tk.Frame(self.main_container, bg=self.colors["bg"])

        header_frame = tk.Frame(frame, bg=self.colors["bg"])
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_frame, text="Organiseur Visuel & Édition de Pages", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Tournez, déplacez, supprimez et réorganisez visuellement les pages de votre PDF.", style="SubHeader.TLabel").pack(anchor="w")

        toolbar = tk.Frame(frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=10, pady=8)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        btn_open = tk.Button(toolbar, text="📂 Ouvrir un PDF...", font=("Segoe UI", 9, "bold"), bg=self.colors["primary"], fg="#ffffff", relief=tk.FLAT, padx=12, pady=4, cursor="hand2", command=self._open_pdf_dialog)
        btn_open.pack(side=tk.LEFT, padx=(0, 8))

        btn_rot_left = tk.Button(toolbar, text="↺ Tourner -90°", font=("Segoe UI", 9), bg="#f1f5f9", fg=self.colors["text_dark"], relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=lambda: self._rotate_selected(-90))
        btn_rot_left.pack(side=tk.LEFT, padx=3)

        btn_rot_right = tk.Button(toolbar, text="↻ Tourner +90°", font=("Segoe UI", 9), bg="#f1f5f9", fg=self.colors["text_dark"], relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=lambda: self._rotate_selected(90))
        btn_rot_right.pack(side=tk.LEFT, padx=3)

        btn_move_left = tk.Button(toolbar, text="⬅ Monter / Avancer", font=("Segoe UI", 9), bg="#f1f5f9", fg=self.colors["text_dark"], relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=self._move_selected_left)
        btn_move_left.pack(side=tk.LEFT, padx=3)

        btn_move_right = tk.Button(toolbar, text="➡ Descendre / Reculer", font=("Segoe UI", 9), bg="#f1f5f9", fg=self.colors["text_dark"], relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=self._move_selected_right)
        btn_move_right.pack(side=tk.LEFT, padx=3)

        btn_del = tk.Button(toolbar, text="🗑️ Supprimer", font=("Segoe UI", 9, "bold"), bg="#fee2e2", fg=self.colors["danger"], relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=self._delete_selected)
        btn_del.pack(side=tk.LEFT, padx=3)

        btn_select_all = tk.Button(toolbar, text="Tout sélectionner", font=("Segoe UI", 9), bg="#f1f5f9", fg=self.colors["text_dark"], relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=self._toggle_select_all)
        btn_select_all.pack(side=tk.LEFT, padx=3)

        btn_export_sel = tk.Button(toolbar, text="📤 Extraire sélection", font=("Segoe UI", 9), bg="#e0e7ff", fg=self.colors["primary"], relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self._export_selected_pages)
        btn_export_sel.pack(side=tk.RIGHT, padx=4)

        btn_save = tk.Button(toolbar, text="💾 Enregistrer sous...", font=("Segoe UI", 9, "bold"), bg=self.colors["success"], fg="#ffffff", relief=tk.FLAT, padx=12, pady=4, cursor="hand2", command=self._save_modified_pdf)
        btn_save.pack(side=tk.RIGHT, padx=4)

        self.lbl_current_file_info = tk.Label(frame, text="Aucun fichier ouvert", font=("Segoe UI", 9, "italic"), bg=self.colors["bg"], fg="#64748b")
        self.lbl_current_file_info.pack(anchor="w", pady=(0, 6))

        canvas_container = tk.Frame(frame, bg="#ffffff", bd=1, relief=tk.SOLID)
        canvas_container.pack(expand=True, fill=tk.BOTH)

        self.pages_canvas = tk.Canvas(canvas_container, bg="#f8fafc", highlightthickness=0)
        self.pages_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL, command=self.pages_canvas.yview)
        
        self.pages_grid_frame = tk.Frame(self.pages_canvas, bg="#f8fafc")
        self.pages_grid_frame.bind("<Configure>", lambda e: self.pages_canvas.configure(scrollregion=self.pages_canvas.bbox("all")))
        
        self.canvas_window_id = self.pages_canvas.create_window((0, 0), window=self.pages_grid_frame, anchor="nw")
        self.pages_canvas.configure(xscrollcommand=None, yscrollcommand=self.pages_scrollbar.set)

        self.pages_canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        self.pages_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.pages_canvas.bind_all("<MouseWheel>", self._on_canvas_mousewheel)
        self.pages_canvas.bind("<Configure>", self._on_canvas_resize)

        return frame

    def _on_canvas_mousewheel(self, event):
        if self.pages_canvas.winfo_ismapped():
            self.pages_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_canvas_resize(self, event):
        self.pages_canvas.itemconfig(self.canvas_window_id, width=event.width)
        self._refresh_grid_layout()

    def _open_pdf_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Sélectionner un fichier PDF",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if filepath:
            self.load_pdf(filepath)

    def load_pdf(self, filepath: str):
        self.set_status(f"Chargement de {os.path.basename(filepath)}...")
        self.lbl_current_file_info.config(text=f"Chargement : {filepath}...")
        self.update_idletasks()

        try:
            info = pdf_core.get_pdf_info(filepath)
            if info["is_encrypted"]:
                self._prompt_password(filepath)
                return

            # Copie de travail temporaire pour permettre des modifications non destructives
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            with open(filepath, "rb") as src_f:
                tmp.write(src_f.read())
            tmp.close()
            self.working_pdf_path = tmp.name

            thumbs = pdf_core.render_all_thumbnails(filepath, max_size=(150, 200))
            self._on_pdf_loaded(filepath, thumbs)
        except Exception as e:
            self._on_pdf_error(str(e))

    def _prompt_password(self, filepath: str):
        win = tk.Toplevel(self)
        win.title("PDF Protégé par mot de passe")
        win.geometry("380x160")
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Ce document est protégé par un mot de passe :", font=("Segoe UI", 10)).pack(pady=10)
        ent_pw = ttk.Entry(win, show="*", width=30)
        ent_pw.pack(pady=5)
        ent_pw.focus_set()

        def submit():
            pw = ent_pw.get()
            win.destroy()
            try:
                info = pdf_core.get_pdf_info(filepath, password=pw)
                if info.get("is_encrypted", False):
                    messagebox.showerror("Erreur", "Mot de passe incorrect.")
                    return
                
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                doc = fitz.open(filepath)
                doc.authenticate(pw)
                doc.save(tmp.name)
                doc.close()
                self.working_pdf_path = tmp.name

                thumbs = pdf_core.render_all_thumbnails(filepath, max_size=(150, 200), password=pw)
                self._on_pdf_loaded(filepath, thumbs, password=pw)
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

        btn = ttk.Button(win, text="Déverrouiller", style="Primary.TButton", command=submit)
        btn.pack(pady=10)

    def _on_pdf_loaded(self, filepath: str, thumbnails: List[Image.Image], password: str = ""):
        self.current_pdf_path = filepath
        self.current_pdf_password = password
        self.pages_data = []
        self.selected_indices.clear()

        for idx, thumb in enumerate(thumbnails):
            self.pages_data.append({
                "source_page": idx,
                "rotation": 0,
                "orig_thumb": thumb,
                "display_thumb": thumb,
                "tk_thumb": ImageTk.PhotoImage(thumb)
            })

        count = len(self.pages_data)
        self.lbl_current_file_info.config(
            text=f"📄 {os.path.basename(filepath)} ({count} pages) - Dossier : {os.path.dirname(filepath)}"
        )
        self.set_status(f"Fichier chargé : {count} pages.")
        self._refresh_grid_layout()

        # Mettre à jour également les champs des autres onglets
        self.split_file_var.set(filepath)
        self.wm_file_var.set(filepath)
        self.p2i_file_var.set(filepath)
        self.sec_file_var.set(filepath)
        self.text_edit_file_lbl.config(text=f"📄 {os.path.basename(filepath)} ({count} pages)")
        self.text_edit_page = 0
        self._text_edit_refresh_page()

    def _on_pdf_error(self, err_msg: str):
        self.set_status(f"Erreur de chargement : {err_msg}", is_error=True)
        messagebox.showerror("Erreur d'ouverture", f"Impossible d'ouvrir le fichier PDF :\n{err_msg}")

    def _refresh_grid_layout(self):
        for widget in self.pages_grid_frame.winfo_children():
            widget.destroy()

        self.card_widgets.clear()
        if not self.pages_data:
            empty_lbl = tk.Label(
                self.pages_grid_frame,
                text="Aucun document ouvert.\n\nCliquez sur « 📂 Ouvrir un PDF... » ci-dessus\nou testez avec 'exemple_document.pdf' !",
                font=("Segoe UI", 12),
                fg="#94a3b8",
                bg="#f8fafc",
                pady=60
            )
            empty_lbl.pack()
            return

        canvas_width = max(self.pages_canvas.winfo_width(), 600)
        card_width = 180
        cols = max(1, canvas_width // (card_width + 16))

        for idx, page_info in enumerate(self.pages_data):
            row = idx // cols
            col = idx % cols

            is_selected = (idx in self.selected_indices)
            card_bg = self.colors["card_selected"] if is_selected else self.colors["card_bg"]

            card = tk.Frame(
                self.pages_grid_frame,
                bg=card_bg,
                bd=2,
                relief=tk.SOLID,
                padx=8,
                pady=8,
                cursor="hand2"
            )
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            header_text = f"Page {idx + 1}"
            sub_text = f"Origine #{page_info['source_page'] + 1}"
            if page_info["rotation"] != 0:
                sub_text += f" | {page_info['rotation']}°"

            lbl_title = tk.Label(card, text=header_text, font=("Segoe UI", 10, "bold"), bg=card_bg, fg=self.colors["text_dark"])
            lbl_title.pack(anchor="w")

            lbl_sub = tk.Label(card, text=sub_text, font=("Segoe UI", 8), bg=card_bg, fg="#64748b")
            lbl_sub.pack(anchor="w", pady=(0, 4))

            lbl_img = tk.Label(card, image=page_info["tk_thumb"], bg=card_bg)
            lbl_img.pack(pady=4)

            for w in (card, lbl_title, lbl_sub, lbl_img):
                w.bind("<Button-1>", lambda e, i=idx: self._on_card_clicked(i, e))
                w.bind("<Double-Button-1>", lambda e, i=idx: self._on_card_double_clicked(i))

            self.card_widgets.append(card)

    def _on_card_clicked(self, idx: int, event):
        if event.state & 0x0004 or event.state & 0x0001:  # Ctrl ou Shift
            if idx in self.selected_indices:
                self.selected_indices.remove(idx)
            else:
                self.selected_indices.add(idx)
        else:
            if idx in self.selected_indices and len(self.selected_indices) == 1:
                self.selected_indices.clear()
            else:
                self.selected_indices = {idx}
        
        self._refresh_selection_visuals()

    def _on_card_double_clicked(self, idx: int):
        self.selected_indices = {idx}
        self._rotate_selected(90)

    def _refresh_selection_visuals(self):
        for idx, card in enumerate(self.card_widgets):
            is_selected = (idx in self.selected_indices)
            card_bg = self.colors["card_selected"] if is_selected else self.colors["card_bg"]
            card.config(bg=card_bg)
            for child in card.winfo_children():
                if isinstance(child, tk.Label):
                    child.config(bg=card_bg)

        sel_count = len(self.selected_indices)
        if sel_count > 0:
            self.set_status(f"{sel_count} page(s) sélectionnée(s).")
        else:
            self.set_status("Prêt.")

    def _toggle_select_all(self):
        if len(self.selected_indices) == len(self.pages_data):
            self.selected_indices.clear()
        else:
            self.selected_indices = set(range(len(self.pages_data)))
        self._refresh_selection_visuals()

    def _rotate_selected(self, angle_delta: int):
        if not self.selected_indices:
            messagebox.showinfo("Information", "Veuillez d'abord sélectionner au moins une page à pivoter.")
            return

        for idx in self.selected_indices:
            page = self.pages_data[idx]
            page["rotation"] = (page["rotation"] + angle_delta) % 360
            orig = page["orig_thumb"]
            rotated_img = orig.rotate(-page["rotation"], expand=True)
            page["display_thumb"] = rotated_img
            page["tk_thumb"] = ImageTk.PhotoImage(rotated_img)

        self.set_status(f"Rotation appliquée sur {len(self.selected_indices)} page(s).")
        self._refresh_grid_layout()

    def _delete_selected(self):
        if not self.selected_indices:
            messagebox.showinfo("Information", "Veuillez sélectionner au moins une page à supprimer.")
            return

        if not messagebox.askyesno("Confirmation", f"Voulez-vous supprimer {len(self.selected_indices)} page(s) ?"):
            return

        self.pages_data = [p for i, p in enumerate(self.pages_data) if i not in self.selected_indices]
        self.selected_indices.clear()
        self.set_status("Pages supprimées.")
        self._refresh_grid_layout()

    def _move_selected_left(self):
        if not self.selected_indices:
            return
        sorted_sel = sorted(list(self.selected_indices))
        if sorted_sel[0] == 0:
            return

        new_selected = set()
        for idx in sorted_sel:
            self.pages_data[idx - 1], self.pages_data[idx] = self.pages_data[idx], self.pages_data[idx - 1]
            new_selected.add(idx - 1)

        self.selected_indices = new_selected
        self._refresh_grid_layout()

    def _move_selected_right(self):
        if not self.selected_indices:
            return
        sorted_sel = sorted(list(self.selected_indices), reverse=True)
        if sorted_sel[0] == len(self.pages_data) - 1:
            return

        new_selected = set()
        for idx in sorted_sel:
            self.pages_data[idx + 1], self.pages_data[idx] = self.pages_data[idx], self.pages_data[idx + 1]
            new_selected.add(idx + 1)

        self.selected_indices = new_selected
        self._refresh_grid_layout()

    def _save_modified_pdf(self):
        src_path = self.working_pdf_path if self.working_pdf_path else self.current_pdf_path
        if not src_path or not self.pages_data:
            messagebox.showwarning("Attention", "Aucun PDF n'est actuellement ouvert.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF modifié sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not out_path:
            return

        try:
            configs = [
                {"source_page": p["source_page"], "rotation": p["rotation"]}
                for p in self.pages_data
            ]
            pdf_core.save_modified_pdf(
                src_path,
                out_path,
                configs,
                password=getattr(self, "current_pdf_password", "")
            )
            self.set_status(f"PDF modifié enregistré avec succès : {os.path.basename(out_path)}")
            messagebox.showinfo("Succès", f"Le fichier a été enregistré avec succès :\n{out_path}")
        except Exception as e:
            messagebox.showerror("Erreur lors de la sauvegarde", str(e))

    def _export_selected_pages(self):
        src_path = self.working_pdf_path if self.working_pdf_path else self.current_pdf_path
        if not self.selected_indices:
            messagebox.showinfo("Information", "Sélectionnez au moins une page à exporter.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Exporter les pages sélectionnées sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not out_path:
            return

        try:
            sorted_sel = sorted(list(self.selected_indices))
            configs = [
                {"source_page": self.pages_data[i]["source_page"], "rotation": self.pages_data[i]["rotation"]}
                for i in sorted_sel
            ]
            pdf_core.save_modified_pdf(
                src_path,
                out_path,
                configs,
                password=getattr(self, "current_pdf_password", "")
            )
            messagebox.showinfo("Succès", f"{len(configs)} page(s) exportée(s) avec succès dans :\n{out_path}")
        except Exception as e:
            messagebox.showerror("Erreur d'exportation", str(e))

    # -------------------------------------------------------------
    # NOUVEL ONGLET : MODIFIER LE TEXTE (MÊME POLICE)
    # -------------------------------------------------------------
    def _build_text_edit_tab(self) -> tk.Frame:
        frame = tk.Frame(self.main_container, bg=self.colors["bg"])

        # En-tête
        header = tk.Frame(frame, bg=self.colors["bg"])
        header.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header, text="Modifier le Texte Existant (Même Police)", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header, text="Sélectionnez une phrase ou recherchez un terme pour le modifier en conservant fidèlement la même police, taille et couleur.", style="SubHeader.TLabel").pack(anchor="w")

        # Barre d'outils supérieure de navigation de page
        toolbar = tk.Frame(frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=10, pady=8)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        btn_open = tk.Button(toolbar, text="📂 Ouvrir un PDF...", font=("Segoe UI", 9, "bold"), bg=self.colors["primary"], fg="#ffffff", relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self._open_pdf_dialog)
        btn_open.pack(side=tk.LEFT, padx=(0, 15))

        btn_prev = tk.Button(toolbar, text="◀ Page Précédente", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=self._text_edit_prev_page)
        btn_prev.pack(side=tk.LEFT, padx=3)

        self.lbl_text_edit_page_ind = tk.Label(toolbar, text="Page 1 / 1", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=8)
        self.lbl_text_edit_page_ind.pack(side=tk.LEFT)

        btn_next = tk.Button(toolbar, text="Page Suivante ▶", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=self._text_edit_next_page)
        btn_next.pack(side=tk.LEFT, padx=3)

        self.text_edit_file_lbl = tk.Label(toolbar, text="Aucun fichier ouvert", font=("Segoe UI", 9, "italic"), bg="#ffffff", fg="#64748b", padx=15)
        self.text_edit_file_lbl.pack(side=tk.LEFT)

        btn_save_as = tk.Button(toolbar, text="💾 Enregistrer le document sous...", font=("Segoe UI", 9, "bold"), bg=self.colors["success"], fg="#ffffff", relief=tk.FLAT, padx=12, pady=4, cursor="hand2", command=self._text_edit_save_as)
        btn_save_as.pack(side=tk.RIGHT)

        # Corps de la vue : 2 colonnes (Gauche = Aperçu page, Droite = Outils de modification)
        paned = tk.PanedWindow(frame, orient=tk.HORIZONTAL, bg=self.colors["bg"], sashrelief=tk.FLAT, sashwidth=6)
        paned.pack(expand=True, fill=tk.BOTH)

        # Colonne Gauche : Aperçu Visuel
        left_box = tk.Frame(paned, bg="#ffffff", bd=1, relief=tk.SOLID, padx=10, pady=10)
        paned.add(left_box, minsize=420, width=520)

        tk.Label(left_box, text="Aperçu en direct de la page :", font=("Segoe UI", 10, "bold"), bg="#ffffff").pack(anchor="w", pady=(0, 6))

        preview_container = tk.Frame(left_box, bg="#f8fafc", bd=1, relief=tk.SOLID)
        preview_container.pack(expand=True, fill=tk.BOTH)

        self.text_edit_canvas = tk.Canvas(preview_container, bg="#cbd5e1", highlightthickness=0)
        te_scroll_y = ttk.Scrollbar(preview_container, orient=tk.VERTICAL, command=self.text_edit_canvas.yview)
        te_scroll_x = ttk.Scrollbar(preview_container, orient=tk.HORIZONTAL, command=self.text_edit_canvas.xview)
        self.text_edit_canvas.configure(xscrollcommand=te_scroll_x.set, yscrollcommand=te_scroll_y.set)

        self.text_edit_canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        te_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        te_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Colonne Droite : Formulaires de modification
        right_box = tk.Frame(paned, bg="#ffffff", bd=1, relief=tk.SOLID, padx=14, pady=10)
        paned.add(right_box, minsize=440)

        # 1. Sélection et modification directe d'une ligne de texte
        b1 = tk.LabelFrame(right_box, text=" 📝 1. Modifier un texte présent sur cette page ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=10, pady=10)
        b1.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        top_detect_frame = tk.Frame(b1, bg="#ffffff")
        top_detect_frame.pack(fill=tk.X)

        tk.Label(top_detect_frame, text="Textes détectés sur la page :", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(side=tk.LEFT)
        btn_force_ocr = tk.Button(
            top_detect_frame,
            text="🔍 Forcer Scan OCR (Scanné)",
            font=("Segoe UI", 8),
            bg="#f1f5f9",
            fg="#0f172a",
            relief=tk.FLAT,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._text_edit_force_ocr
        )
        btn_force_ocr.pack(side=tk.RIGHT)

        # Treeview des lignes de texte
        tree_f = tk.Frame(b1, bg="#ffffff")
        tree_f.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        self.te_tree = ttk.Treeview(tree_f, columns=("text", "font", "size"), show="headings", height=5, selectmode="browse")
        self.te_tree.heading("text", text="Texte actuel")
        self.te_tree.heading("font", text="Police détectée")
        self.te_tree.heading("size", text="Taille")

        self.te_tree.column("text", width=250)
        self.te_tree.column("font", width=110, anchor="center")
        self.te_tree.column("size", width=55, anchor="center")

        te_tree_scroll = ttk.Scrollbar(tree_f, orient=tk.VERTICAL, command=self.te_tree.yview)
        self.te_tree.configure(yscrollcommand=te_tree_scroll.set)
        self.te_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        te_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.te_tree.bind("<<TreeviewSelect>>", self._on_text_elem_selected)

        # Badge info typographie
        self.lbl_detected_font_badge = tk.Label(
            b1,
            text="Sélectionnez un texte ci-dessus pour le modifier.",
            font=("Segoe UI", 8, "italic"),
            bg="#f1f5f9",
            fg="#475569",
            padx=8,
            pady=4,
            relief=tk.FLAT
        )
        self.lbl_detected_font_badge.pack(fill=tk.X, pady=(0, 6))

        # Champ nouveau texte
        tk.Label(b1, text="Nouveau texte de remplacement :", font=("Segoe UI", 9, "bold"), bg="#ffffff").pack(anchor="w")
        self.te_new_text_var = tk.StringVar()
        ent_new = ttk.Entry(b1, textvariable=self.te_new_text_var, font=("Segoe UI", 10))
        ent_new.pack(fill=tk.X, pady=(2, 6))

        # Options et bouton appliquer
        opt_frame1 = tk.Frame(b1, bg="#ffffff")
        opt_frame1.pack(fill=tk.X, pady=(2, 0))

        self.te_white_bg_var = tk.BooleanVar(value=False)
        chk_w = tk.Checkbutton(opt_frame1, text="Masquer avec fond blanc", variable=self.te_white_bg_var, font=("Segoe UI", 8), bg="#ffffff")
        chk_w.pack(side=tk.LEFT)

        btn_apply_line = tk.Button(
            opt_frame1,
            text="✏️ Remplacer ce texte (Même police)",
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["primary"],
            fg="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._apply_text_line_replacement
        )
        btn_apply_line.pack(side=tk.RIGHT)

        # 2. Rechercher & Remplacer partout
        b2 = tk.LabelFrame(right_box, text=" 🔍 2. Rechercher & Remplacer (Conserver police & style) ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=10, pady=10)
        b2.pack(fill=tk.X, pady=(0, 5))

        f_sr1 = tk.Frame(b2, bg="#ffffff")
        f_sr1.pack(fill=tk.X, pady=2)
        tk.Label(f_sr1, text="Rechercher :", font=("Segoe UI", 9), width=12, anchor="w", bg="#ffffff").pack(side=tk.LEFT)
        self.sr_find_var = tk.StringVar()
        ttk.Entry(f_sr1, textvariable=self.sr_find_var).pack(side=tk.LEFT, expand=True, fill=tk.X)

        f_sr2 = tk.Frame(b2, bg="#ffffff")
        f_sr2.pack(fill=tk.X, pady=4)
        tk.Label(f_sr2, text="Remplacer par :", font=("Segoe UI", 9), width=12, anchor="w", bg="#ffffff").pack(side=tk.LEFT)
        self.sr_replace_var = tk.StringVar()
        ttk.Entry(f_sr2, textvariable=self.sr_replace_var).pack(side=tk.LEFT, expand=True, fill=tk.X)

        f_sr_opts = tk.Frame(b2, bg="#ffffff")
        f_sr_opts.pack(fill=tk.X, pady=(4, 0))

        self.sr_scope_var = tk.StringVar(value="page")
        r_page = tk.Radiobutton(f_sr_opts, text="Cette page", variable=self.sr_scope_var, value="page", font=("Segoe UI", 9), bg="#ffffff")
        r_page.pack(side=tk.LEFT)
        r_all = tk.Radiobutton(f_sr_opts, text="Tout le document", variable=self.sr_scope_var, value="all", font=("Segoe UI", 9), bg="#ffffff")
        r_all.pack(side=tk.LEFT, padx=(8, 0))

        btn_sr = tk.Button(
            f_sr_opts,
            text="🔍 Remplacer partout",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._apply_search_and_replace
        )
        btn_sr.pack(side=tk.RIGHT)

        return frame

    def _text_edit_refresh_page(self):
        pdf_path = self.working_pdf_path if self.working_pdf_path else self.current_pdf_path
        if not pdf_path or not os.path.exists(pdf_path):
            self.text_edit_canvas.delete("all")
            return

        try:
            info = pdf_core.get_pdf_info(pdf_path)
            total = info["page_count"]
            if total == 0:
                return

            self.text_edit_page = max(0, min(self.text_edit_page, total - 1))
            self.lbl_text_edit_page_ind.config(text=f"Page {self.text_edit_page + 1} / {total}")

            # 1. Rendu visuel de la page
            doc = fitz.open(pdf_path)
            page = doc[self.text_edit_page]
            mat = fitz.Matrix(1.4, 1.4)  # Échelle confortable pour la lecture
            pix = page.get_pixmap(matrix=mat, alpha=False)
            doc.close()

            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            self.text_edit_preview_img = ImageTk.PhotoImage(img)

            self.text_edit_canvas.delete("all")
            self.text_edit_canvas.create_image(0, 0, image=self.text_edit_preview_img, anchor="nw")
            self.text_edit_canvas.config(scrollregion=(0, 0, pix.width, pix.height))

            # 2. Liste des textes détectés sur cette page (Vectoriel avec fallback OCR automatique)
            self.text_elements = pdf_core.get_page_text_elements(pdf_path, self.text_edit_page)

            for item in self.te_tree.get_children():
                self.te_tree.delete(item)

            has_ocr = any(e.get("is_ocr", False) for e in self.text_elements)
            for elem in self.text_elements:
                self.te_tree.insert(
                    "",
                    "end",
                    iid=str(elem["id"]),
                    values=(elem["text"], elem["font"], f"{elem['size']} pt")
                )

            mode_str = " (Reconnaissance OCR active pour document scanné)" if has_ocr else ""
            self.lbl_detected_font_badge.config(
                text=f"{len(self.text_elements)} ligne(s) de texte détectée(s) sur la page {self.text_edit_page + 1}{mode_str}."
            )
            self.te_new_text_var.set("")
        except Exception as e:
            self.set_status(f"Erreur d'affichage : {e}", is_error=True)

    def _text_edit_force_ocr(self):
        pdf_path = self.working_pdf_path if self.working_pdf_path else self.current_pdf_path
        if not pdf_path or not os.path.exists(pdf_path):
            return
        self.set_status("Scan OCR en cours sur cette page...")
        self.update_idletasks()
        try:
            self.text_elements = pdf_core.get_page_text_elements(pdf_path, self.text_edit_page, force_ocr=True)
            for item in self.te_tree.get_children():
                self.te_tree.delete(item)
            for elem in self.text_elements:
                self.te_tree.insert(
                    "",
                    "end",
                    iid=str(elem["id"]),
                    values=(elem["text"], elem["font"], f"{elem['size']} pt")
                )
            self.lbl_detected_font_badge.config(
                text=f"🔍 Scan OCR terminé : {len(self.text_elements)} ligne(s) détectée(s) sur la page {self.text_edit_page + 1}."
            )
            self.set_status("Scan OCR terminé.")
        except Exception as e:
            messagebox.showerror("Erreur OCR", str(e))

    def _text_edit_prev_page(self):
        if self.text_edit_page > 0:
            self.text_edit_page -= 1
            self._text_edit_refresh_page()

    def _text_edit_next_page(self):
        pdf_path = self.working_pdf_path if self.working_pdf_path else self.current_pdf_path
        if not pdf_path:
            return
        info = pdf_core.get_pdf_info(pdf_path)
        if self.text_edit_page < info["page_count"] - 1:
            self.text_edit_page += 1
            self._text_edit_refresh_page()

    def _on_text_elem_selected(self, event):
        sel = self.te_tree.selection()
        if not sel:
            return
        elem_id = int(sel[0])
        elem = next((e for e in self.text_elements if e["id"] == elem_id), None)
        if not elem:
            return

        self.te_new_text_var.set(elem["text"])
        self.lbl_detected_font_badge.config(
            text=f"✨ Police : {elem['font']} | Taille : {elem['size']} pt | Couleur : {elem['color_hex']} | Origin : {int(elem['origin'][0])},{int(elem['origin'][1])}"
        )

    def _apply_text_line_replacement(self):
        sel = self.te_tree.selection()
        if not sel:
            messagebox.showinfo("Information", "Veuillez sélectionner un texte dans la liste ci-dessus.")
            return

        elem_id = int(sel[0])
        elem = next((e for e in self.text_elements if e["id"] == elem_id), None)
        if not elem:
            return

        new_text = self.te_new_text_var.get().strip()
        if not new_text:
            messagebox.showwarning("Attention", "Le nouveau texte ne peut pas être vide.")
            return

        current_path = self.working_pdf_path if self.working_pdf_path else self.current_pdf_path
        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_out_path = tmp_out.name
        tmp_out.close()

        try:
            pdf_core.replace_text_element_in_pdf(
                current_path,
                tmp_out_path,
                page_num=self.text_edit_page,
                elem_bbox=elem["bbox"],
                new_text=new_text,
                elem_origin=elem["origin"],
                font_name=elem["font"],
                font_size=elem["size"],
                font_flags=elem.get("flags", 0),
                font_color=elem["color_rgb"],
                use_white_bg=self.te_white_bg_var.get(),
                is_ocr=elem.get("is_ocr", False)
            )

            # Mettre à jour le fichier de travail actif et nettoyer l'ancien
            old_working = self.working_pdf_path
            old_working = self.working_pdf_path
            self.working_pdf_path = tmp_out_path
            if old_working and os.path.exists(old_working) and old_working != self.current_pdf_path:
                try:
                    os.remove(old_working)
                except Exception:
                    pass
            if old_working and os.path.exists(old_working) and old_working != self.current_pdf_path:
                try:
                    os.remove(old_working)
                except Exception:
                    pass
            self.set_status("Texte remplacé avec succès (même police conservée) !")
            self._text_edit_refresh_page()

            # Mettre à jour également les miniatures de l'organiseur
            thumbs = pdf_core.render_all_thumbnails(self.working_pdf_path, max_size=(150, 200))
            for i, thumb in enumerate(thumbs):
                if i < len(self.pages_data):
                    self.pages_data[i]["orig_thumb"] = thumb
                    rot = self.pages_data[i]["rotation"]
                    rotated_img = thumb.rotate(-rot, expand=True) if rot != 0 else thumb
                    self.pages_data[i]["display_thumb"] = rotated_img
                    self.pages_data[i]["tk_thumb"] = ImageTk.PhotoImage(rotated_img)
            self._refresh_grid_layout()

        except Exception as e:
            messagebox.showerror("Erreur de remplacement", str(e))

    def _apply_search_and_replace(self):
        search_str = self.sr_find_var.get().strip()
        replace_str = self.sr_replace_var.get().strip()

        if not search_str:
            messagebox.showwarning("Attention", "Veuillez entrer le texte à rechercher.")
            return

        current_path = self.working_pdf_path if self.working_pdf_path else self.current_pdf_path
        if not current_path:
            messagebox.showwarning("Attention", "Aucun PDF n'est ouvert.")
            return

        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_out_path = tmp_out.name
        tmp_out.close()

        target_p = self.text_edit_page if self.sr_scope_var.get() == "page" else None

        try:
            cnt = pdf_core.search_and_replace_text_in_pdf(
                current_path,
                tmp_out_path,
                search_text=search_str,
                replace_text=replace_str,
                target_page=target_p
            )

            if cnt == 0:
                messagebox.showinfo("Résultat", f"Le texte « {search_str} » n'a pas été trouvé.")
                if os.path.exists(tmp_out_path):
                    os.remove(tmp_out_path)
                return

            old_working = self.working_pdf_path
            self.working_pdf_path = tmp_out_path
            if old_working and os.path.exists(old_working) and old_working != self.current_pdf_path:
                try:
                    os.remove(old_working)
                except Exception:
                    pass
            msg = f"{cnt} occurrence(s) remplacée(s) avec succès avec la même police !"
            messagebox.showinfo("Succès", msg)
            self.set_status(msg)
            self._text_edit_refresh_page()

            # Actualiser les vignettes
            thumbs = pdf_core.render_all_thumbnails(self.working_pdf_path, max_size=(150, 200))
            for i, thumb in enumerate(thumbs):
                if i < len(self.pages_data):
                    self.pages_data[i]["orig_thumb"] = thumb
                    rot = self.pages_data[i]["rotation"]
                    rotated_img = thumb.rotate(-rot, expand=True) if rot != 0 else thumb
                    self.pages_data[i]["display_thumb"] = rotated_img
                    self.pages_data[i]["tk_thumb"] = ImageTk.PhotoImage(rotated_img)
            self._refresh_grid_layout()

        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _text_edit_save_as(self):
        current_path = self.working_pdf_path if self.working_pdf_path else self.current_pdf_path
        if not current_path or not os.path.exists(current_path):
            messagebox.showwarning("Attention", "Aucun document n'est ouvert.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF modifié sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not out_path:
            return

        try:
            # Sauvegarder avec PyMuPDF pour optimiser
            doc = fitz.open(current_path)
            doc.save(out_path, garbage=4, deflate=True)
            doc.close()
            messagebox.showinfo("Succès", f"Fichier enregistré avec succès :\n{out_path}")
            self.set_status(f"Document enregistré : {os.path.basename(out_path)}")
        except Exception as e:
            messagebox.showerror("Erreur lors de l'enregistrement", str(e))

    # -------------------------------------------------------------
    # ONGLET 2 : FUSIONNER DES PDF
    # -------------------------------------------------------------
    def _build_merge_tab(self) -> tk.Frame:
        frame = tk.Frame(self.main_container, bg=self.colors["bg"])

        ttk.Label(frame, text="Fusionner plusieurs PDF en un seul", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Assemblez plusieurs documents PDF dans l'ordre que vous souhaitez.", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))

        card = tk.Frame(frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=15, pady=15)
        card.pack(expand=True, fill=tk.BOTH)

        top_bar = tk.Frame(card, bg="#ffffff")
        top_bar.pack(fill=tk.X, pady=(0, 10))

        btn_add = tk.Button(top_bar, text="➕ Ajouter des fichiers PDF...", font=("Segoe UI", 9, "bold"), bg=self.colors["primary"], fg="#ffffff", relief=tk.FLAT, padx=12, pady=5, cursor="hand2", command=self._merge_add_files)
        btn_add.pack(side=tk.LEFT, padx=(0, 6))

        btn_up = tk.Button(top_bar, text="⬆ Monter", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=8, pady=5, cursor="hand2", command=self._merge_move_up)
        btn_up.pack(side=tk.LEFT, padx=3)

        btn_down = tk.Button(top_bar, text="⬇ Descendre", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=8, pady=5, cursor="hand2", command=self._merge_move_down)
        btn_down.pack(side=tk.LEFT, padx=3)

        btn_rem = tk.Button(top_bar, text="❌ Retirer", font=("Segoe UI", 9), bg="#fee2e2", fg=self.colors["danger"], relief=tk.FLAT, padx=8, pady=5, cursor="hand2", command=self._merge_remove)
        btn_rem.pack(side=tk.LEFT, padx=3)

        btn_clear = tk.Button(top_bar, text="🧹 Tout vider", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=8, pady=5, cursor="hand2", command=self._merge_clear)
        btn_clear.pack(side=tk.LEFT, padx=3)

        tree_frame = tk.Frame(card, bg="#ffffff")
        tree_frame.pack(expand=True, fill=tk.BOTH)

        cols = ("num", "name", "pages", "size", "path")
        self.merge_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        self.merge_tree.heading("num", text="#")
        self.merge_tree.heading("name", text="Nom du fichier")
        self.merge_tree.heading("pages", text="Pages")
        self.merge_tree.heading("size", text="Taille")
        self.merge_tree.heading("path", text="Chemin complet")

        self.merge_tree.column("num", width=40, anchor="center")
        self.merge_tree.column("name", width=200)
        self.merge_tree.column("pages", width=70, anchor="center")
        self.merge_tree.column("size", width=90, anchor="center")
        self.merge_tree.column("path", width=380)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.merge_tree.yview)
        self.merge_tree.configure(yscrollcommand=tree_scroll.set)

        self.merge_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        bottom_bar = tk.Frame(card, bg="#ffffff", pady=12)
        bottom_bar.pack(fill=tk.X)

        self.lbl_merge_summary = tk.Label(bottom_bar, text="0 fichier sélectionné.", font=("Segoe UI", 10), bg="#ffffff", fg="#475569")
        self.lbl_merge_summary.pack(side=tk.LEFT)

        btn_merge_action = tk.Button(
            bottom_bar,
            text="🚀 Fusionner les PDF en un seul fichier...",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["success"],
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._execute_merge
        )
        btn_merge_action.pack(side=tk.RIGHT)

        return frame

    def _merge_add_files(self):
        files = filedialog.askopenfilenames(
            title="Ajouter des fichiers PDF à fusionner",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not files:
            return
        for f in files:
            if f not in self.merge_files_list:
                self.merge_files_list.append(f)
        self._refresh_merge_tree()

    def _refresh_merge_tree(self):
        for item in self.merge_tree.get_children():
            self.merge_tree.delete(item)

        total_pages = 0
        total_size = 0
        for i, path in enumerate(self.merge_files_list):
            try:
                info = pdf_core.get_pdf_info(path)
                p_count = info.get("page_count", 0)
                sz = os.path.getsize(path)
            except Exception:
                p_count = "?"
                sz = 0
            
            total_pages += p_count if isinstance(p_count, int) else 0
            total_size += sz

            sz_str = f"{sz / 1024:.1f} Ko" if sz < 1024*1024 else f"{sz / (1024*1024):.1f} Mo"
            self.merge_tree.insert("", "end", values=(i + 1, os.path.basename(path), p_count, sz_str, path))

        sz_total_str = f"{total_size / 1024:.1f} Ko" if total_size < 1024*1024 else f"{total_size / (1024*1024):.1f} Mo"
        self.lbl_merge_summary.config(
            text=f"Total : {len(self.merge_files_list)} fichier(s) | ~{total_pages} pages | {sz_total_str}"
        )

    def _merge_move_up(self):
        sel = self.merge_tree.selection()
        if not sel:
            return
        idx = self.merge_tree.index(sel[0])
        if idx > 0:
            self.merge_files_list[idx - 1], self.merge_files_list[idx] = self.merge_files_list[idx], self.merge_files_list[idx - 1]
            self._refresh_merge_tree()
            items = self.merge_tree.get_children()
            self.merge_tree.selection_set(items[idx - 1])

    def _merge_move_down(self):
        sel = self.merge_tree.selection()
        if not sel:
            return
        idx = self.merge_tree.index(sel[0])
        if idx < len(self.merge_files_list) - 1:
            self.merge_files_list[idx + 1], self.merge_files_list[idx] = self.merge_files_list[idx], self.merge_files_list[idx + 1]
            self._refresh_merge_tree()
            items = self.merge_tree.get_children()
            self.merge_tree.selection_set(items[idx + 1])

    def _merge_remove(self):
        sel = self.merge_tree.selection()
        if not sel:
            return
        idx = self.merge_tree.index(sel[0])
        self.merge_files_list.pop(idx)
        self._refresh_merge_tree()

    def _merge_clear(self):
        self.merge_files_list.clear()
        self._refresh_merge_tree()

    def _execute_merge(self):
        if len(self.merge_files_list) < 2:
            messagebox.showinfo("Information", "Veuillez ajouter au moins 2 fichiers PDF à fusionner.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF fusionné sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not out_path:
            return

        try:
            total = pdf_core.merge_pdfs(self.merge_files_list, out_path)
            self.set_status(f"Fusion réussie : {total} pages dans {os.path.basename(out_path)}")
            messagebox.showinfo("Succès", f"Les {len(self.merge_files_list)} documents ont été fusionnés avec succès !\nTotal : {total} pages.\nFichier : {out_path}")
        except Exception as e:
            messagebox.showerror("Erreur de fusion", str(e))

    # -------------------------------------------------------------
    # ONGLET 3 : DÉCOUPER / SCINDER
    # -------------------------------------------------------------
    def _build_split_tab(self) -> tk.Frame:
        frame = tk.Frame(self.main_container, bg=self.colors["bg"])

        ttk.Label(frame, text="Découper / Scinder un PDF", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Divisez un document par intervalle, page par page, ou par groupes de pages.", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))

        card = tk.Frame(frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=20, pady=20)
        card.pack(fill=tk.BOTH, expand=True)

        lbl_file = tk.Label(card, text="1. Fichier PDF à découper :", font=("Segoe UI", 10, "bold"), bg="#ffffff")
        lbl_file.pack(anchor="w", pady=(0, 4))

        f_row = tk.Frame(card, bg="#ffffff")
        f_row.pack(fill=tk.X, pady=(0, 15))

        self.split_file_var = tk.StringVar()
        ent_file = ttk.Entry(f_row, textvariable=self.split_file_var, font=("Segoe UI", 10))
        ent_file.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))

        btn_browse = tk.Button(f_row, text="Parcourir...", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self._split_browse_file)
        btn_browse.pack(side=tk.LEFT)

        self.lbl_split_file_info = tk.Label(card, text="Aucun fichier sélectionné", font=("Segoe UI", 9, "italic"), bg="#ffffff", fg="#64748b")
        self.lbl_split_file_info.pack(anchor="w", pady=(0, 15))

        lbl_mode = tk.Label(card, text="2. Choisissez la méthode de découpage :", font=("Segoe UI", 10, "bold"), bg="#ffffff")
        lbl_mode.pack(anchor="w", pady=(0, 8))

        self.split_mode_var = tk.StringVar(value="range")

        r1 = tk.Radiobutton(card, text="Extraire une ou plusieurs plages de pages", variable=self.split_mode_var, value="range", font=("Segoe UI", 10), bg="#ffffff")
        r1.pack(anchor="w")

        f_range = tk.Frame(card, bg="#ffffff", padx=25)
        f_range.pack(fill=tk.X, pady=(2, 10))
        tk.Label(f_range, text="Plages (ex : 1-3, 5, 8-10) :", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.split_range_var = tk.StringVar(value="1-2")
        ttk.Entry(f_range, textvariable=self.split_range_var, width=25).pack(side=tk.LEFT)

        r2 = tk.Radiobutton(card, text="Découper chaque page dans un fichier PDF individuel (page_01.pdf, page_02.pdf...)", variable=self.split_mode_var, value="all_pages", font=("Segoe UI", 10), bg="#ffffff")
        r2.pack(anchor="w", pady=(5, 5))

        r3 = tk.Radiobutton(card, text="Découper par blocs réguliers de pages", variable=self.split_mode_var, value="every_n", font=("Segoe UI", 10), bg="#ffffff")
        r3.pack(anchor="w")

        f_n = tk.Frame(card, bg="#ffffff", padx=25)
        f_n.pack(fill=tk.X, pady=(2, 15))
        tk.Label(f_n, text="Nombre de pages par fichier :", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.split_n_var = tk.IntVar(value=2)
        ttk.Spinbox(f_n, from_=1, to=100, textvariable=self.split_n_var, width=8).pack(side=tk.LEFT)

        tk.Frame(card, bg="#e2e8f0", height=1).pack(fill=tk.X, pady=15)

        btn_do_split = tk.Button(
            card,
            text="✂️ Exécuter le découpage",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["primary"],
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._execute_split
        )
        btn_do_split.pack(anchor="e")

        return frame

    def _split_browse_file(self):
        f = filedialog.askopenfilename(title="Choisir le PDF à découper", filetypes=[("Fichiers PDF", "*.pdf")])
        if f:
            self.split_file_var.set(f)
            try:
                info = pdf_core.get_pdf_info(f)
                self.lbl_split_file_info.config(text=f"Pages totales : {info['page_count']} | Taille : {info['size_bytes']/1024:.1f} Ko")
                self.split_range_var.set(f"1-{min(3, info['page_count'])}")
            except Exception as e:
                self.lbl_split_file_info.config(text=f"Erreur d'analyse : {e}")

    def _execute_split(self):
        pdf_path = self.split_file_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Attention", "Veuillez choisir un fichier PDF valide.")
            return

        mode = self.split_mode_var.get()
        try:
            if mode == "range":
                range_str = self.split_range_var.get().strip()
                if not range_str:
                    messagebox.showwarning("Attention", "Veuillez entrer une plage de pages.")
                    return
                out_path = filedialog.asksaveasfilename(
                    title="Enregistrer les pages extraites sous...",
                    defaultextension=".pdf",
                    filetypes=[("Fichiers PDF", "*.pdf")]
                )
                if not out_path:
                    return
                count = pdf_core.split_pdf_by_range(pdf_path, range_str, out_path)
                messagebox.showinfo("Succès", f"{count} page(s) extraite(s) dans :\n{out_path}")

            elif mode == "all_pages":
                out_folder = filedialog.askdirectory(title="Choisir le dossier de destination pour les pages")
                if not out_folder:
                    return
                base_prefix = os.path.splitext(os.path.basename(pdf_path))[0]
                files = pdf_core.split_pdf_all_pages(pdf_path, out_folder, prefix=base_prefix)
                messagebox.showinfo("Succès", f"{len(files)} fichiers générés dans le dossier :\n{out_folder}")

            elif mode == "every_n":
                n = self.split_n_var.get()
                out_folder = filedialog.askdirectory(title="Choisir le dossier de destination")
                if not out_folder:
                    return
                base_prefix = os.path.splitext(os.path.basename(pdf_path))[0]
                files = pdf_core.split_pdf_every_n_pages(pdf_path, out_folder, n=n, prefix=base_prefix)
                messagebox.showinfo("Succès", f"{len(files)} fichiers par blocs de {n} pages créés dans :\n{out_folder}")

            self.set_status("Découpage terminé avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur de découpage", str(e))

    # -------------------------------------------------------------
    # ONGLET 4 : FILIGRANE & NUMÉROTATION
    # -------------------------------------------------------------
    def _build_watermark_tab(self) -> tk.Frame:
        frame = tk.Frame(self.main_container, bg=self.colors["bg"])

        ttk.Label(frame, text="Ajouter un Filigrane & Numéroter les Pages", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Apposez un texte (ex: CONFIDENTIEL, COPIE) ou ajoutez la numérotation des pages.", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))

        card = tk.Frame(frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=20, pady=20)
        card.pack(fill=tk.BOTH, expand=True)

        f_row = tk.Frame(card, bg="#ffffff")
        f_row.pack(fill=tk.X, pady=(0, 15))
        tk.Label(f_row, text="Fichier PDF :", font=("Segoe UI", 10, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        self.wm_file_var = tk.StringVar()
        ttk.Entry(f_row, textvariable=self.wm_file_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))
        tk.Button(f_row, text="Parcourir...", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=10, pady=3, cursor="hand2", command=self._wm_browse_file).pack(side=tk.LEFT)

        lbl_sec1 = tk.Label(card, text="Texte du Filigrane (Watermark)", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg=self.colors["primary"])
        lbl_sec1.pack(anchor="w", pady=(5, 6))

        wm_box = tk.Frame(card, bg="#f8fafc", bd=1, relief=tk.SOLID, padx=12, pady=12)
        wm_box.pack(fill=tk.X, pady=(0, 15))

        row1 = tk.Frame(wm_box, bg="#f8fafc")
        row1.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row1, text="Texte :", font=("Segoe UI", 9), bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 6))
        self.wm_text_var = tk.StringVar(value="CONFIDENTIEL")
        ttk.Entry(row1, textvariable=self.wm_text_var, width=28).pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(row1, text="Modèles rapides :", font=("Segoe UI", 9), bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 6))
        cb_presets = ttk.Combobox(row1, values=["CONFIDENTIEL", "COPIE", "BROUILLON", "PAYÉ", "DUPLICATA", "ARCHIVE", "URGENT"], state="readonly", width=15)
        cb_presets.pack(side=tk.LEFT)
        cb_presets.bind("<<ComboboxSelected>>", lambda e: self.wm_text_var.set(cb_presets.get()))

        row2 = tk.Frame(wm_box, bg="#f8fafc")
        row2.pack(fill=tk.X)
        tk.Label(row2, text="Angle :", font=("Segoe UI", 9), bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 6))
        self.wm_angle_var = tk.IntVar(value=45)
        cb_angle = ttk.Combobox(row2, textvariable=self.wm_angle_var, values=[0, 45, 90, 315], state="readonly", width=6)
        cb_angle.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(row2, text="Taille police :", font=("Segoe UI", 9), bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 6))
        self.wm_size_var = tk.IntVar(value=44)
        ttk.Spinbox(row2, from_=14, to=100, textvariable=self.wm_size_var, width=6).pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(row2, text="Couleur :", font=("Segoe UI", 9), bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 6))
        self.wm_color_var = tk.StringVar(value="Gris")
        cb_col = ttk.Combobox(row2, textvariable=self.wm_color_var, values=["Gris", "Rouge", "Bleu", "Noir"], state="readonly", width=10)
        cb_col.pack(side=tk.LEFT)

        lbl_sec2 = tk.Label(card, text="Numérotation des pages", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg=self.colors["primary"])
        lbl_sec2.pack(anchor="w", pady=(5, 6))

        num_box = tk.Frame(card, bg="#f8fafc", bd=1, relief=tk.SOLID, padx=12, pady=12)
        num_box.pack(fill=tk.X, pady=(0, 20))

        self.num_enabled_var = tk.BooleanVar(value=True)
        chk_num = tk.Checkbutton(num_box, text="Activer la numérotation des pages", variable=self.num_enabled_var, font=("Segoe UI", 9, "bold"), bg="#f8fafc")
        chk_num.pack(anchor="w", pady=(0, 8))

        row_num = tk.Frame(num_box, bg="#f8fafc")
        row_num.pack(fill=tk.X)

        tk.Label(row_num, text="Format :", font=("Segoe UI", 9), bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 6))
        self.num_fmt_var = tk.StringVar(value="Page {page} / {total}")
        cb_fmt = ttk.Combobox(row_num, textvariable=self.num_fmt_var, values=["Page {page} / {total}", "Page {page}", "{page} sur {total}", "{page}"], width=20)
        cb_fmt.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(row_num, text="Position :", font=("Segoe UI", 9), bg="#f8fafc").pack(side=tk.LEFT, padx=(0, 6))
        self.num_pos_var = tk.StringVar(value="Bas - Centre")
        cb_pos = ttk.Combobox(row_num, textvariable=self.num_pos_var, values=["Bas - Centre", "Bas - Droite", "Bas - Gauche", "Haut - Droite", "Haut - Centre"], state="readonly", width=14)
        cb_pos.pack(side=tk.LEFT)

        btn_apply = tk.Button(
            card,
            text="🏷️ Appliquer et enregistrer sous...",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["success"],
            fg="#ffffff",
            relief=tk.FLAT,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._execute_watermark
        )
        btn_apply.pack(anchor="e")

        return frame

    def _wm_browse_file(self):
        f = filedialog.askopenfilename(title="Sélectionner le PDF", filetypes=[("Fichiers PDF", "*.pdf")])
        if f:
            self.wm_file_var.set(f)

    def _execute_watermark(self):
        pdf_path = self.wm_file_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Attention", "Veuillez sélectionner un fichier PDF valide.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF final sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not out_path:
            return

        try:
            col_map = {
                "Gris": (0.7, 0.7, 0.7),
                "Rouge": (0.85, 0.2, 0.2),
                "Bleu": (0.2, 0.4, 0.85),
                "Noir": (0.1, 0.1, 0.1)
            }
            wm_color = col_map.get(self.wm_color_var.get(), (0.7, 0.7, 0.7))

            pos_map = {
                "Bas - Centre": "bottom-center",
                "Bas - Droite": "bottom-right",
                "Bas - Gauche": "bottom-left",
                "Haut - Droite": "top-right",
                "Haut - Centre": "top-center"
            }
            num_pos = pos_map.get(self.num_pos_var.get(), "bottom-center")

            pdf_core.add_watermark_and_numbering(
                pdf_path,
                out_path,
                watermark_text=self.wm_text_var.get(),
                watermark_color=wm_color,
                watermark_size=self.wm_size_var.get(),
                watermark_angle=self.wm_angle_var.get(),
                add_numbers=self.num_enabled_var.get(),
                number_format=self.num_fmt_var.get(),
                number_position=num_pos
            )
            messagebox.showinfo("Succès", f"Filigrane et/ou numérotation appliqués avec succès !\nFichier enregistré : {out_path}")
            self.set_status("Traitement filigrane terminé.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    # -------------------------------------------------------------
    # ONGLET 5 : CONVERTISSEUR IMAGES <-> PDF
    # -------------------------------------------------------------
    def _build_convert_tab(self) -> tk.Frame:
        frame = tk.Frame(self.main_container, bg=self.colors["bg"])

        ttk.Label(frame, text="Convertisseur Images & PDF", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Convertissez vos pages PDF en images ou transformez vos photos en un fichier PDF.", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))

        nb = ttk.Notebook(frame)
        nb.pack(expand=True, fill=tk.BOTH)

        tab_p2i = tk.Frame(nb, bg="#ffffff", padx=15, pady=15)
        nb.add(tab_p2i, text="📄 PDF vers Images (PNG / JPG)")

        tk.Label(tab_p2i, text="1. Fichier PDF à convertir en images :", font=("Segoe UI", 10, "bold"), bg="#ffffff").pack(anchor="w", pady=(0, 4))
        r1 = tk.Frame(tab_p2i, bg="#ffffff")
        r1.pack(fill=tk.X, pady=(0, 15))
        self.p2i_file_var = tk.StringVar()
        ttk.Entry(r1, textvariable=self.p2i_file_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))
        tk.Button(r1, text="Parcourir...", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=10, pady=3, cursor="hand2", command=lambda: self._browse_single_file(self.p2i_file_var, [("Fichiers PDF", "*.pdf")])).pack(side=tk.LEFT)

        r2 = tk.Frame(tab_p2i, bg="#ffffff")
        r2.pack(fill=tk.X, pady=(0, 20))
        tk.Label(r2, text="Format d'image :", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.p2i_fmt_var = tk.StringVar(value="PNG")
        ttk.Combobox(r2, textvariable=self.p2i_fmt_var, values=["PNG", "JPEG"], state="readonly", width=8).pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(r2, text="Résolution :", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.p2i_dpi_var = tk.IntVar(value=150)
        ttk.Combobox(r2, textvariable=self.p2i_dpi_var, values=[100, 150, 200, 300], state="readonly", width=8).pack(side=tk.LEFT)

        btn_p2i = tk.Button(tab_p2i, text="🖼️ Convertir toutes les pages en images...", font=("Segoe UI", 10, "bold"), bg=self.colors["primary"], fg="#ffffff", relief=tk.FLAT, padx=14, pady=6, cursor="hand2", command=self._execute_pdf_to_images)
        btn_p2i.pack(anchor="w")

        tab_i2p = tk.Frame(nb, bg="#ffffff", padx=15, pady=15)
        nb.add(tab_i2p, text="🖼️ Images vers PDF")

        top_i2p = tk.Frame(tab_i2p, bg="#ffffff")
        top_i2p.pack(fill=tk.X, pady=(0, 10))

        tk.Button(top_i2p, text="➕ Ajouter des images...", font=("Segoe UI", 9, "bold"), bg=self.colors["primary"], fg="#ffffff", relief=tk.FLAT, padx=10, pady=4, cursor="hand2", command=self._i2p_add_images).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(top_i2p, text="❌ Retirer", font=("Segoe UI", 9), bg="#fee2e2", fg=self.colors["danger"], relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=self._i2p_remove).pack(side=tk.LEFT, padx=3)
        tk.Button(top_i2p, text="🧹 Vider", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=8, pady=4, cursor="hand2", command=self._i2p_clear).pack(side=tk.LEFT, padx=3)

        self.i2p_listbox = tk.Listbox(tab_i2p, font=("Segoe UI", 10), height=8)
        self.i2p_listbox.pack(expand=True, fill=tk.BOTH, pady=(0, 10))

        btn_i2p = tk.Button(tab_i2p, text="📄 Créer le PDF à partir de ces images...", font=("Segoe UI", 10, "bold"), bg=self.colors["success"], fg="#ffffff", relief=tk.FLAT, padx=14, pady=6, cursor="hand2", command=self._execute_images_to_pdf)
        btn_i2p.pack(anchor="e")

        return frame

    def _browse_single_file(self, target_var: tk.StringVar, filetypes):
        f = filedialog.askopenfilename(title="Sélectionner le fichier", filetypes=filetypes)
        if f:
            target_var.set(f)

    def _execute_pdf_to_images(self):
        pdf_path = self.p2i_file_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Attention", "Veuillez choisir un fichier PDF valide.")
            return

        out_dir = filedialog.askdirectory(title="Dossier où enregistrer les images")
        if not out_dir:
            return

        try:
            fmt = self.p2i_fmt_var.get()
            dpi = self.p2i_dpi_var.get()
            files = pdf_core.pdf_to_images(pdf_path, out_dir, fmt=fmt, dpi=dpi)
            messagebox.showinfo("Succès", f"{len(files)} image(s) enregistrée(s) avec succès dans :\n{out_dir}")
            self.set_status(f"{len(files)} image(s) exportée(s).")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _i2p_add_images(self):
        files = filedialog.askopenfilenames(
            title="Sélectionner les images",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff")]
        )
        if not files:
            return
        for f in files:
            if f not in self.img_conv_list:
                self.img_conv_list.append(f)
                self.i2p_listbox.insert(tk.END, os.path.basename(f))

    def _i2p_remove(self):
        sel = self.i2p_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.img_conv_list.pop(idx)
        self.i2p_listbox.delete(idx)

    def _i2p_clear(self):
        self.img_conv_list.clear()
        self.i2p_listbox.delete(0, tk.END)

    def _execute_images_to_pdf(self):
        if not self.img_conv_list:
            messagebox.showwarning("Attention", "Veuillez ajouter au moins une image.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF résultant sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not out_path:
            return

        try:
            count = pdf_core.images_to_pdf(self.img_conv_list, out_path)
            messagebox.showinfo("Succès", f"PDF créé avec succès avec {count} image(s) :\n{out_path}")
            self.set_status("PDF créé à partir des images.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    # -------------------------------------------------------------
    # ONGLET 6 : SÉCURITÉ & OUTILS
    # -------------------------------------------------------------
    def _build_security_tab(self) -> tk.Frame:
        frame = tk.Frame(self.main_container, bg=self.colors["bg"])

        ttk.Label(frame, text="Sécurité & Optimisation", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Protégez par mot de passe, déverrouillez, réduisez la taille et extrayez le texte.", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))

        card = tk.Frame(frame, bg="#ffffff", bd=1, relief=tk.SOLID, padx=20, pady=20)
        card.pack(fill=tk.BOTH, expand=True)

        f_row = tk.Frame(card, bg="#ffffff")
        f_row.pack(fill=tk.X, pady=(0, 20))
        tk.Label(f_row, text="Fichier PDF cible :", font=("Segoe UI", 10, "bold"), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 8))
        self.sec_file_var = tk.StringVar()
        ttk.Entry(f_row, textvariable=self.sec_file_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))
        tk.Button(f_row, text="Parcourir...", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=10, pady=3, cursor="hand2", command=lambda: self._browse_single_file(self.sec_file_var, [("Fichiers PDF", "*.pdf")])).pack(side=tk.LEFT)

        b1 = tk.LabelFrame(card, text=" 🔒 1. Verrouiller avec un mot de passe (Chiffrement AES-256) ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=12, pady=10)
        b1.pack(fill=tk.X, pady=(0, 12))

        r_pw = tk.Frame(b1, bg="#ffffff")
        r_pw.pack(fill=tk.X)
        tk.Label(r_pw, text="Mot de passe :", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.protect_pw_var = tk.StringVar()
        ttk.Entry(r_pw, textvariable=self.protect_pw_var, show="*", width=25).pack(side=tk.LEFT, padx=(0, 15))
        tk.Button(r_pw, text="Chiffrer et enregistrer sous...", font=("Segoe UI", 9, "bold"), bg=self.colors["primary"], fg="#ffffff", relief=tk.FLAT, padx=12, pady=4, cursor="hand2", command=self._execute_protect).pack(side=tk.LEFT)

        b2 = tk.LabelFrame(card, text=" 🔓 2. Déverrouiller un PDF protégé ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=12, pady=10)
        b2.pack(fill=tk.X, pady=(0, 12))

        r_un = tk.Frame(b2, bg="#ffffff")
        r_un.pack(fill=tk.X)
        tk.Label(r_un, text="Mot de passe actuel :", font=("Segoe UI", 9), bg="#ffffff").pack(side=tk.LEFT, padx=(0, 6))
        self.unlock_pw_var = tk.StringVar()
        ttk.Entry(r_un, textvariable=self.unlock_pw_var, show="*", width=25).pack(side=tk.LEFT, padx=(0, 15))
        tk.Button(r_un, text="Retirer le mot de passe...", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.FLAT, padx=12, pady=4, cursor="hand2", command=self._execute_unlock).pack(side=tk.LEFT)

        b3 = tk.LabelFrame(card, text=" ⚡ 3. Outils complémentaires ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=12, pady=10)
        b3.pack(fill=tk.X)

        r_tools = tk.Frame(b3, bg="#ffffff")
        r_tools.pack(fill=tk.X)
        tk.Button(r_tools, text="🗜️ Compresser & Optimiser le PDF", font=("Segoe UI", 9, "bold"), bg="#f0fdf4", fg=self.colors["success"], relief=tk.SOLID, bd=1, padx=12, pady=6, cursor="hand2", command=self._execute_compress).pack(side=tk.LEFT, padx=(0, 12))
        tk.Button(r_tools, text="📝 Extraire tout le texte (.txt)", font=("Segoe UI", 9), bg="#f1f5f9", relief=tk.SOLID, bd=1, padx=12, pady=6, cursor="hand2", command=self._execute_extract_text).pack(side=tk.LEFT)

        return frame

    def _execute_protect(self):
        pdf_path = self.sec_file_var.get().strip()
        pw = self.protect_pw_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Attention", "Veuillez choisir un fichier PDF valide.")
            return
        if not pw:
            messagebox.showwarning("Attention", "Veuillez saisir un mot de passe.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF protégé sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not out_path:
            return

        try:
            pdf_core.protect_pdf(pdf_path, out_path, pw)
            messagebox.showinfo("Succès", f"Le PDF a été protégé avec succès !\nFichier : {out_path}")
            self.set_status("Document protégé avec mot de passe.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _execute_unlock(self):
        pdf_path = self.sec_file_var.get().strip()
        pw = self.unlock_pw_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Attention", "Veuillez choisir un fichier PDF valide.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF déverrouillé sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not out_path:
            return

        try:
            ok = pdf_core.unlock_pdf(pdf_path, out_path, pw)
            if ok:
                messagebox.showinfo("Succès", f"Document déverrouillé avec succès !\nEnregistré sous : {out_path}")
                self.set_status("Document déverrouillé.")
            else:
                messagebox.showerror("Échec", "Mot de passe incorrect.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _execute_compress(self):
        pdf_path = self.sec_file_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Attention", "Veuillez choisir un fichier PDF valide.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Enregistrer le PDF compressé sous...",
            defaultextension=".pdf",
            filetypes=[("Fichiers PDF", "*.pdf")]
        )
        if not out_path:
            return

        try:
            init_sz, fin_sz = pdf_core.compress_pdf(pdf_path, out_path)
            gain = ((init_sz - fin_sz) / max(init_sz, 1)) * 100
            msg = f"Compression terminée !\nTaille initiale : {init_sz / 1024:.1f} Ko\nTaille finale : {fin_sz / 1024:.1f} Ko\nGain : {gain:.1f} %\nEnregistré dans : {out_path}"
            messagebox.showinfo("Succès", msg)
            self.set_status(f"Compression terminée : gain de {gain:.1f}%.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def _execute_extract_text(self):
        pdf_path = self.sec_file_var.get().strip()
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showwarning("Attention", "Veuillez choisir un fichier PDF valide.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Enregistrer le texte sous...",
            defaultextension=".txt",
            filetypes=[("Fichiers Texte", "*.txt")]
        )
        if not out_path:
            return

        try:
            text = pdf_core.extract_text_from_pdf(pdf_path, out_path)
            messagebox.showinfo("Succès", f"Texte extrait avec succès ({len(text)} caractères) dans :\n{out_path}")
            self.set_status("Texte extrait avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))


def main():
    app = PDFEditorApp()
    sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exemple_document.pdf")
    if os.path.exists(sample_path):
        app.load_pdf(sample_path)
    app.mainloop()


if __name__ == "__main__":
    main()
