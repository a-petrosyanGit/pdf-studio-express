"""
tests/conftest.py - Fixtures pytest pour la suite de tests de PDF Studio Express.
Génère des documents synthétiques (vectoriel, protégé, scanné) sans accès réseau.
"""

import os
import shutil
import tempfile
from PIL import Image, ImageDraw
import pymupdf as fitz
import pytest

from core.session import DocumentSession
from core.temp_manager import SessionTempManager


@pytest.fixture(scope="session")
def test_temp_dir():
    """Crée un dossier temporaire dédié pour la session de tests."""
    temp_dir = tempfile.mkdtemp(prefix="pdf_tests_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def _add_vector_page(
    doc: fitz.Document,
    title: str,
    lines: list,
    title_color: tuple,
) -> None:
    page = doc.new_page(width=595, height=842)
    page.insert_text(
        fitz.Point(50, 100), title, fontsize=20, fontname="hebo", color=title_color
    )
    for idx, text in enumerate(lines):
        page.insert_text(
            fitz.Point(50, 145 + idx * 45),
            text,
            fontsize=12,
            fontname="helv",
            color=(0.2, 0.2, 0.2),
        )


def _populate_vector_pages(doc: fitz.Document) -> None:
    _add_vector_page(
        doc,
        "Rapport Annuel 2026",
        [
            "Ce document contient des données confidentielles.",
            "Date de validation : Avril 2026",
        ],
        (0.1, 0.2, 0.8),
    )
    _add_vector_page(
        doc,
        "Chapitre 1 : Analyse Financière",
        ["Le chiffre d'affaires a progressé de 15% sur le trimestre."],
        (0.1, 0.1, 0.1),
    )
    _add_vector_page(
        doc,
        "Conclusion & Perspectives",
        ["Approuvé par le Directeur Général."],
        (0.1, 0.1, 0.1),
    )


@pytest.fixture(scope="session")
def sample_vector_pdf(test_temp_dir):
    """Génère un PDF vectoriel propre de 3 pages avec polices et couleurs variées."""
    pdf_path = os.path.join(test_temp_dir, "sample_vector.pdf")
    doc = fitz.open()
    _populate_vector_pages(doc)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture(scope="session")
def sample_encrypted_pdf(test_temp_dir, sample_vector_pdf):
    """Génère un PDF protégé par mot de passe AES-256."""
    encrypted_path = os.path.join(test_temp_dir, "sample_encrypted.pdf")
    doc = fitz.open(sample_vector_pdf)
    doc.save(
        encrypted_path,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="Secret123!",
        owner_pw="Secret123!",
    )
    doc.close()
    return encrypted_path


@pytest.fixture(scope="session")
def sample_scanned_pdf(test_temp_dir):
    """Génère un PDF purement graphique simulé avec fond papier teinté."""
    pdf_path = os.path.join(test_temp_dir, "sample_scanned.pdf")
    img = Image.new("RGB", (800, 1100), color=(245, 245, 240))
    draw = ImageDraw.Draw(img)

    draw.text((100, 150), "FACTURE N° 98765", fill=(20, 20, 20))
    draw.text((100, 220), "Date d'emission : 15 Mars 2026", fill=(30, 30, 30))
    draw.text((100, 280), "Montant Total TTC : 1250 EUR", fill=(20, 20, 20))
    draw.text((100, 350), "Statut : Paye en ligne", fill=(30, 30, 30))

    img_path = os.path.join(test_temp_dir, "scan_raw.png")
    img.save(img_path)

    doc = fitz.open()
    img_doc = fitz.open(img_path)
    pdf_bytes = img_doc.convert_to_pdf()
    img_doc.close()

    doc_from_img = fitz.open("pdf", pdf_bytes)
    doc.insert_pdf(doc_from_img)
    doc_from_img.close()

    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def fresh_session():
    """Fournit une nouvelle instance de DocumentSession avec purge automatique."""
    tm = SessionTempManager(prefix="pdf_test_session_")
    session = DocumentSession(temp_manager=tm)
    yield session
    session.close()
