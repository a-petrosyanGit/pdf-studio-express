"""
core/security.py - Gestion de la sécurité, chiffrement AES-256 et déverrouillage de documents PDF.
Fournit une protection cryptographique conforme aux standards PDF sans fuite de mot de passe.
"""

import os
import fitz


def protect_pdf(pdf_path: str, output_path: str, password: str) -> None:
    """Protège un document PDF par mot de passe avec chiffrement AES-256."""
    if not password:
        raise ValueError("Le mot de passe de protection ne peut pas être vide.")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier source introuvable : {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        doc.save(
            output_path,
            encryption=fitz.PDF_ENCRYPT_AES_256,
            user_pw=password,
            owner_pw=password
        )
    finally:
        doc.close()


def unlock_pdf(pdf_path: str, output_path: str, password: str) -> bool:
    """Déverrouille un PDF protégé par mot de passe et génère une version décryptée."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        if not doc.is_encrypted:
            doc.save(output_path, garbage=4, deflate=True)
            return True

        auth_res = doc.authenticate(password)
        if auth_res <= 0:
            return False

        doc.save(output_path, garbage=4, deflate=True)
        return True
    finally:
        doc.close()


def verify_pdf_password(pdf_path: str, password: str) -> bool:
    """Vérifie si un mot de passe permet d'authentifier un document chiffré."""
    if not os.path.exists(pdf_path):
        return False
    doc = fitz.open(pdf_path)
    try:
        if not doc.is_encrypted:
            return True
        return doc.authenticate(password) > 0
    finally:
        doc.close()
