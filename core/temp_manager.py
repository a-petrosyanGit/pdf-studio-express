"""
core/temp_manager.py - Gestionnaire sécurisé de fichiers et répertoires temporaires.
Isole les fichiers dans un sous-répertoire dédié et nettoie les résidus.
"""

import atexit
import logging
import os
import shutil
import tempfile
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


def _try_remove_expired_dir(full_path: str, now: float, max_age_sec: float) -> int:
    """Supprime un dossier s'il a dépassé la durée maximale de rétention."""
    if not os.path.isdir(full_path):
        return 0
    try:
        if (now - os.path.getmtime(full_path)) > max_age_sec:
            shutil.rmtree(full_path, ignore_errors=True)
            return 1
    except OSError as exc:
        logger.debug("Impossible de vérifier ou purger %s : %s", full_path, exc)
    return 0


class SessionTempManager:
    """Gestionnaire de cycle de vie des fichiers temporaires de session."""

    def __init__(self, prefix: str = "pdf_studio_"):
        self.prefix = prefix
        self._temp_dir: Optional[str] = None
        self._created_files: List[str] = []
        self._init_session_dir()
        atexit.register(self.cleanup)

    def _init_session_dir(self) -> None:
        self._temp_dir = tempfile.mkdtemp(prefix=self.prefix)

    @property
    def session_dir(self) -> str:
        if self._temp_dir is None or not os.path.exists(self._temp_dir):
            self._init_session_dir()
        return self._temp_dir  # type: ignore[return-value]

    def create_temp_file(self, suffix: str = ".pdf", prefix: str = "doc_") -> str:
        """Crée un fichier temporaire unique dans le répertoire de session."""
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
        except OSError as exc:
            logger.debug("Suppression temporaire différée pour %s : %s", file_path, exc)

    def cleanup(self) -> None:
        """Supprime l'intégralité du répertoire temporaire de la session."""
        if not self._temp_dir or not os.path.exists(self._temp_dir):
            return
        try:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        except OSError as exc:
            logger.warning("Nettoyage incomplet de %s : %s", self._temp_dir, exc)
        self._temp_dir = None
        self._created_files.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    @classmethod
    def purge_orphaned_sessions(
        cls,
        prefix: str = "pdf_studio_",
        max_age_hours: float = 24.0,
    ) -> int:
        """Nettoie les anciens dossiers temporaires laissés par d'anciennes sessions."""
        base_temp = tempfile.gettempdir()
        now = time.time()
        max_age_sec = max_age_hours * 3600.0
        purged = 0
        try:
            entries = os.listdir(base_temp)
        except OSError as exc:
            logger.debug("Lecture impossible de %s : %s", base_temp, exc)
            return 0

        for item in entries:
            if item.startswith(prefix):
                purged += _try_remove_expired_dir(
                    os.path.join(base_temp, item),
                    now,
                    max_age_sec,
                )
        return purged


default_temp_manager = SessionTempManager()
try:
    SessionTempManager.purge_orphaned_sessions(max_age_hours=12.0)
except OSError as exc:
    logger.debug("Purge initiale ignorée : %s", exc)
