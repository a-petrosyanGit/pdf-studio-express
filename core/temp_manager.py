"""
core/temp_manager.py - Gestionnaire sécurisé de fichiers et répertoires temporaires.
Isole les fichiers de travail dans un sous-répertoire dédié et nettoie automatiquement
les résidus au démarrage et à la fermeture.
"""

import os
import shutil
import tempfile
import atexit
import time
from typing import List, Optional


class SessionTempManager:
    """
    Gestionnaire de cycle de vie des fichiers temporaires pour une session PDF Studio.
    Crée un dossier dédié 'pdf_studio_<id>' dans le répertoire temporaire système,
    assure un nettoyage propre et purge les dossiers orphelins anciens.
    """

    def __init__(self, prefix: str = "pdf_studio_"):
        self.prefix = prefix
        self._temp_dir: Optional[str] = None
        self._created_files: List[str] = []
        self._init_session_dir()
        atexit.register(self.cleanup)

    def _init_session_dir(self) -> None:
        """Crée un répertoire temporaire isolé pour la session courante."""
        self._temp_dir = tempfile.mkdtemp(prefix=self.prefix)

    @property
    def session_dir(self) -> str:
        if self._temp_dir is None or not os.path.exists(self._temp_dir):
            self._init_session_dir()
        return self._temp_dir  # type: ignore

    def create_temp_file(self, suffix: str = ".pdf", prefix: str = "doc_") -> str:
        """Crée un chemin de fichier temporaire unique dans le dossier de session."""
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=self.session_dir)
        os.close(fd)
        self._created_files.append(path)
        return path

    def create_temp_copy(self, source_path: str, suffix: str = ".pdf") -> str:
        """Copie un fichier existant dans le répertoire temporaire de la session."""
        target_path = self.create_temp_file(suffix=suffix)
        shutil.copy2(source_path, target_path)
        return target_path

    def remove_file(self, file_path: str) -> None:
        """Supprime un fichier spécifique s'il existe dans la session."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            if file_path in self._created_files:
                self._created_files.remove(file_path)
        except OSError:
            pass

    def cleanup(self) -> None:
        """Supprime l'intégralité du répertoire temporaire de la session."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            except OSError:
                pass
            self._temp_dir = None
            self._created_files.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    @classmethod
    def purge_orphaned_sessions(cls, prefix: str = "pdf_studio_", max_age_hours: float = 24.0) -> int:
        """
        Nettoie les anciens répertoires temporaires laissés par d'anciennes sessions
        antérieures ou anormalement interrompues.
        """
        base_temp = tempfile.gettempdir()
        now = time.time()
        max_age_seconds = max_age_hours * 3600.0
        purged_count = 0

        try:
            for item in os.listdir(base_temp):
                if item.startswith(prefix):
                    full_path = os.path.join(base_temp, item)
                    if os.path.isdir(full_path):
                        try:
                            mtime = os.path.getmtime(full_path)
                            if (now - mtime) > max_age_seconds:
                                shutil.rmtree(full_path, ignore_errors=True)
                                purged_count += 1
                        except OSError:
                            continue
        except OSError:
            pass

        return purged_count


# Instance globale par défaut utilisable par le moteur
default_temp_manager = SessionTempManager()
# Purge initiale silencieuse des résidus de plus de 12 heures
try:
    SessionTempManager.purge_orphaned_sessions(max_age_hours=12.0)
except Exception:
    pass
