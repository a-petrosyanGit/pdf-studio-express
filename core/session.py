"""
core/session.py - Modèle de session et gestionnaire d'état partagé pour GUI et Web.
Évite la duplication de logique métier, encapsule l'historique Annuler / Rétablir (Undo/Redo),
le suivi des copies de travail et la gestion des fichiers temporaires.
"""

import os
import shutil
from typing import Optional, List, Set, Dict, Any
from PIL import Image

from core.models import PDFMetadata, PageConfig
from core.temp_manager import SessionTempManager
from core.pages import (
    get_pdf_metadata,
    render_page_thumbnail,
    render_all_thumbnails,
    apply_page_modifications
)


class DocumentSession:
    """
    Session de document PDF active.
    Gère la copie de travail isolée, la pile d'annulation/rétablissement,
    l'état des pages et la sauvegarde définitive.
    """

    def __init__(self, temp_manager: Optional[SessionTempManager] = None):
        self.temp_manager = temp_manager or SessionTempManager()
        self.source_path: Optional[str] = None
        self.working_path: Optional[str] = None
        self.password: str = ""
        self.metadata: PDFMetadata = PDFMetadata()

        # État de l'organiseur de pages
        self.page_configs: List[PageConfig] = []
        self.selected_indices: Set[int] = set()

        # Historique Undo / Redo (piles de chemins temporaires)
        self._undo_stack: List[str] = []
        self._redo_stack: List[str] = []
        self.is_dirty: bool = False

    def load_document(self, file_path: str, password: str = "") -> PDFMetadata:
        """Charge un document source, initialise la copie de travail et les configurations."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier inexistant : {file_path}")

        self.close()
        self.source_path = file_path
        self.password = password
        self.metadata = get_pdf_metadata(file_path, password=password)

        if self.metadata.is_encrypted and self.metadata.page_count == 0:
            return self.metadata

        # Création de la copie de travail isolée
        self.working_path = self.temp_manager.create_temp_copy(file_path)
        self._reset_page_configs()
        self.is_dirty = False
        return self.metadata

    def _reset_page_configs(self) -> None:
        """Réinitialise les configurations de page à l'état initial (1:1 sans rotation)."""
        self.page_configs = [
            PageConfig(source_page=i, rotation=0)
            for i in range(self.metadata.page_count)
        ]
        self.selected_indices.clear()

    def commit_working_copy(self, new_working_path: str) -> None:
        """
        Enregistre un nouvel état du document (ex: après modification de texte ou OCR),
        met à jour la pile d'annulation et actualise les métadonnées.
        """
        if self.working_path and os.path.exists(self.working_path):
            self._undo_stack.append(self.working_path)

        # Vider la pile de rétablissement
        for p in self._redo_stack:
            self.temp_manager.remove_file(p)
        self._redo_stack.clear()

        self.working_path = new_working_path
        self.metadata = get_pdf_metadata(new_working_path, password=self.password)
        self._reset_page_configs()
        self.is_dirty = True

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(self) -> bool:
        """Annule la dernière modification en revenant à l'état précédent."""
        if not self.can_undo or not self.working_path:
            return False

        previous_path = self._undo_stack.pop()
        self._redo_stack.append(self.working_path)
        self.working_path = previous_path
        self.metadata = get_pdf_metadata(self.working_path, password=self.password)
        self._reset_page_configs()
        self.is_dirty = True
        return True

    def redo(self) -> bool:
        """Rétablit la modification précédemment annulée."""
        if not self.can_redo or not self.working_path:
            return False

        next_path = self._redo_stack.pop()
        self._undo_stack.append(self.working_path)
        self.working_path = next_path
        self.metadata = get_pdf_metadata(self.working_path, password=self.password)
        self._reset_page_configs()
        self.is_dirty = True
        return True

    # --- Actions sur les pages ---

    def rotate_page(self, index: int, angle: int = 90) -> None:
        """Pivote une page d'un multiple de 90 degrés."""
        if 0 <= index < len(self.page_configs):
            self.page_configs[index].rotation = (self.page_configs[index].rotation + angle) % 360
            self.is_dirty = True

    def rotate_all(self, angle: int = 90) -> None:
        """Pivote l'ensemble des pages d'un angle donné."""
        for cfg in self.page_configs:
            cfg.rotation = (cfg.rotation + angle) % 360
        self.is_dirty = True

    def delete_page(self, index: int) -> None:
        """Supprime une page de la sélection ordonnée."""
        if 0 <= index < len(self.page_configs):
            self.page_configs.pop(index)
            self.selected_indices.discard(index)
            self.is_dirty = True

    def reorder_pages(self, new_order: List[int]) -> None:
        """Réorganise la liste des configurations de page."""
        self.page_configs = [self.page_configs[i] for i in new_order if 0 <= i < len(self.page_configs)]
        self.selected_indices.clear()
        self.is_dirty = True

    def apply_page_modifications_to_working_copy(self) -> None:
        """Applique les rotations, réordonnancements et suppressions dans un nouveau fichier de travail."""
        if not self.working_path:
            return
        new_tmp = self.temp_manager.create_temp_file(suffix=".pdf")
        apply_page_modifications(
            source_pdf_path=self.working_path,
            output_path=new_tmp,
            page_configs=self.page_configs,
            password=self.password
        )
        self.commit_working_copy(new_tmp)

    def render_thumbnails(self, max_size=(160, 220)) -> List[Image.Image]:
        """Génère les miniatures de la copie de travail actuelle."""
        if not self.working_path or not os.path.exists(self.working_path):
            return []
        return render_all_thumbnails(self.working_path, max_size=max_size, password=self.password)

    def render_page(self, page_num: int, max_size=(160, 220)) -> Optional[Image.Image]:
        """Génère la miniature d'une page individuelle."""
        if not self.working_path or not os.path.exists(self.working_path):
            return None
        return render_page_thumbnail(self.working_path, page_num=page_num, max_size=max_size, password=self.password)

    def save_to(self, output_path: str) -> None:
        """Enregistre le document final au chemin spécifié."""
        if not self.working_path or not os.path.exists(self.working_path):
            raise RuntimeError("Aucun document ouvert à sauvegarder.")
        shutil.copy2(self.working_path, output_path)
        self.is_dirty = False

    def close(self) -> None:
        """Ferme la session et nettoie les fichiers temporaires créés."""
        self.temp_manager.cleanup()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.working_path = None
        self.source_path = None
        self.page_configs.clear()
        self.selected_indices.clear()
        self.is_dirty = False
