"""
tests/conftest.py - Fixtures pytest pour la suite de tests de PDF Studio Express.
Génère des documents de test synthétiques (vectoriel, protégé, scanné) pour valider
l'ensemble du moteur sans dépendance réseau.
"""

import os
import shutil
import tempfile
import pytest
from PIL import Image, ImageDraw, ImageFont
import fitz

from core.temp_manager import SessionTempManager
from core.session import DocumentSession


@pytest.fixture(scope="session")
def test_temp_dir():
    """Crée un dossier temporaire dédié pour la session de tests."""
    temp_dir = tempfile.mkdtemp(prefix="pdf_tests_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def sample_vector_pdf(test_temp_dir):
    """
    Génère un PDF vectoriel propre de 3 pages avec différentes polices,
    styles et couleurs pour tester l'édition et les pages.
    """
    pdf_path = os.path.join(test_temp_dir, "sample_vector.pdf")
    doc = fitz.open()

    # Page 1
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(fitz.Point(50, 100), "Rapport Annuel 2026", fontsize=24, fontname="hebo", color=(0.1, 0.2, 0.8))
    p1.insert_text(fitz.Point(50, 150), "Ce document contient des données confidentielles.", fontsize=12, fontname="helv", color=(0.2, 0.2, 0.2))
    p1.insert_text(fitz.Point(50, 200), "Date de validation : Avril 2026", fontsize=12, fontname="helv", color=(0.2, 0.2, 0.2))

    # Page 2
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text(fitz.Point(50, 100), "Chapitre 1 : Analyse Financière", fontsize=18, fontname="hebo", color=(0.1, 0.1, 0.1))
    p2.insert_text(fitz.Point(50, 140), "Le chiffre d'affaires a progressé de 15% sur le trimestre.", fontsize=11, fontname="helv", color=(0.3, 0.3, 0.3))

    # Page 3
    p3 = doc.new_page(width=595, height=842)
    p3.insert_text(fitz.Point(50, 100), "Conclusion & Perspectives", fontsize=18, fontname="hebo", color=(0.1, 0.1, 0.1))
    p3.insert_text(fitz.Point(50, 140), "Approuvé par le Directeur Général.", fontsize=11, fontname="helv", color=(0.3, 0.3, 0.3))

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
        owner_pw="Secret123!"
    )
    doc.close()
    return encrypted_path


@pytest.fixture(scope="session")
def sample_scanned_pdf(test_temp_dir):
    """
    Génère un document PDF contenant une page purement graphique / scannée
    (une image rasterisée avec du texte dessiné sur un fond papier légèrement teinté).
    """
    pdf_path = os.path.join(test_temp_dir, "sample_scanned.pdf")
    
    # Création d'une image PIL de 800x1100 avec fond papier légèrement crème (245, 245, 240)
    w, h = 800, 1100
    bg_color = (245, 245, 240)
    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Dessiner du texte noir sur l'image
    draw.text((100, 150), "FACTURE N° 98765", fill=(20, 20, 20))
    draw.text((100, 220), "Date d'emission : 15 Mars 2026", fill=(30, 30, 30))
    draw.text((100, 280), "Montant Total TTC : 1250 EUR", fill=(20, 20, 20))
    draw.text((100, 350), "Statut : Paye en ligne", fill=(30, 30, 30))

    img_path = os.path.join(test_temp_dir, "scan_raw.png")
    img.save(img_path)

    # Convertir l'image en PDF rasterisé
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
    """Fournit une nouvelle instance de DocumentSession avec nettoyage automatique."""
    tm = SessionTempManager(prefix="pdf_test_session_")
    session = DocumentSession(temp_manager=tm)
    yield session
    session.close()
