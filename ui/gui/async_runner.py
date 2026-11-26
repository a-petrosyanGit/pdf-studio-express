"""
ui/gui/async_runner.py - Exécution asynchrone sécurisée pour Tkinter.
Évite le gel de l'interface lors des tâches OCR, rendus et exports PDF.
"""

from concurrent.futures import ThreadPoolExecutor
import logging
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AsyncTaskRunner:
    """Exécute des tâches lourdes sur un pool de threads avec callbacks UI."""

    def __init__(
        self,
        root: tk.Tk,
        status_callback: Callable[[str, bool], None],
    ):
        self.root = root
        self.set_status = status_callback
        self.executor = ThreadPoolExecutor(max_workers=2)

    def _set_cursor(self, cursor_name: str) -> None:
        try:
            self.root.config(cursor=cursor_name)
        except tk.TclError as exc:
            logger.debug("Curseur ignoré : %s", exc)

    def run(
        self,
        worker: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Optional[Callable[[Exception], None]] = None,
        status_msg: Optional[str] = None,
    ) -> None:
        """Soumet une fonction bloquante en arrière-plan."""
        if status_msg:
            self.set_status(f"⏳ {status_msg}", False)
            self._set_cursor("watch")

        def task_wrapper() -> None:
            try:
                result = worker()
                self.root.after(0, lambda: self._finish_ok(result, on_success))
            except Exception as exc:
                self.root.after(0, lambda: self._finish_err(exc, on_error))

        self.executor.submit(task_wrapper)

    def _finish_ok(self, result: Any, on_success: Callable[[Any], None]) -> None:
        self._set_cursor("")
        on_success(result)

    def _finish_err(
        self,
        err: Exception,
        on_error: Optional[Callable[[Exception], None]],
    ) -> None:
        self._set_cursor("")
        if on_error is not None:
            on_error(err)
            return
        self.set_status(f"Erreur : {err}", True)
        messagebox.showerror("Erreur de traitement", str(err))

    def shutdown(self) -> None:
        """Arrête proprement le pool de threads à la fermeture."""
        try:
            self.executor.shutdown(wait=False, cancel_futures=True)
        except RuntimeError as exc:
            logger.debug("Arrêt exécuteur : %s", exc)
