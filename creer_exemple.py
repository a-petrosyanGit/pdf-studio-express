"""
Génère un fichier PDF d'exemple pour tester immédiatement PDF Studio Express.
"""

import logging
import pymupdf as fitz

logger = logging.getLogger(__name__)

_SAMPLE_PAGES = [
    (
        "Bienvenue dans votre Éditeur PDF",
        "Ce document est un exemple prêt à l'emploi pour tester les outils.\n\n"
        "Vous pouvez :\n"
        "- Tourner cette page à 90° ou 180°\n"
        "- Réorganiser l'ordre des pages\n"
        "- Supprimer des pages inutiles\n"
        "- Fusionner avec un autre PDF\n"
        "- Ajouter un filigrane (ex: CONFIDENTIEL)\n"
        "- Numéroter automatiquement les pages\n"
        "- Protéger avec un mot de passe",
    ),
    (
        "Page 2 : Analyse & Données",
        "Section 1 : Synthèse des modifications apportées aux documents.\n"
        "Section 2 : Les miniatures visuelles permettent d'agir en direct.\n\n"
        "Essayez de déplacer cette page en première position !",
    ),
    (
        "Page 3 : Facture & Détails",
        "Facture N° 2026-0042\n"
        "Date : Novembre 2026\n"
        "Client : Démonstration\n"
        "Montant Total : 150,00 € TTC\n\n"
        "Vous pouvez apposer un tampon 'PAYÉ' ou 'COPIE' sur cette page.",
    ),
    (
        "Page 4 : Page à supprimer",
        "Cette page est destinée à être supprimée lors de vos tests.\n"
        "Cliquez sur l'icône poubelle directement sur la vignette !",
    ),
    (
        "Page 5 : Conclusion & Contact",
        "Félicitations ! Vous maîtrisez maintenant PDF Studio Express.\n"
        "Vous pouvez convertir ce PDF en images PNG ou le compresser.",
    ),
]

_BANNER_COLORS = [
    (0.1, 0.3, 0.7),
    (0.2, 0.5, 0.2),
    (0.7, 0.3, 0.1),
    (0.6, 0.1, 0.1),
    (0.3, 0.2, 0.6),
]


def _draw_sample_page(doc: fitz.Document, idx: int, title: str, content: str) -> None:
    page = doc.new_page()
    color = _BANNER_COLORS[idx % len(_BANNER_COLORS)]
    page.draw_rect(fitz.Rect(0, 0, page.rect.width, 80), color=None, fill=color)
    page.insert_text(fitz.Point(40, 50), title, fontsize=20, color=(1, 1, 1))
    page.insert_textbox(
        fitz.Rect(50, 120, page.rect.width - 50, page.rect.height - 100),
        content,
        fontsize=13,
        color=(0.1, 0.1, 0.1),
    )
    page.insert_text(
        fitz.Point(page.rect.width / 2 - 40, page.rect.height - 30),
        f"- Page {idx + 1} d'exemple -",
        fontsize=10,
        color=(0.5, 0.5, 0.5),
    )


def create_sample() -> None:
    """Crée un document PDF multi-pages de démonstration."""
    doc = fitz.open()
    for i, (title, content) in enumerate(_SAMPLE_PAGES):
        _draw_sample_page(doc, i, title, content)
    doc.save("exemple_document.pdf")
    doc.close()
    logger.info("Fichier 'exemple_document.pdf' créé avec succès.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    create_sample()
