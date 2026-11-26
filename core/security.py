"""
core/security.py - Chiffrement AES-256 et déverrouillage de documents PDF.
"""

import os
import pymupdf as fitz


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
            owner_pw=password,
        )
    finally:
        doc.close()


def unlock_pdf(pdf_path: str, output_path: str, password: str) -> bool:
    """Déverrouille un PDF protégé et génère une copie non chiffrée."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        if doc.is_encrypted and doc.authenticate(password) <= 0:
            return False
        doc.save(output_path, garbage=4, deflate=True)
        return True
    finally:
        doc.close()


def verify_pdf_password(pdf_path: str, password: str) -> bool:
    """Vérifie si le mot de passe déverrouille un document PDF."""
    if not os.path.exists(pdf_path):
        return False
    doc = fitz.open(pdf_path)
    try:
        if not doc.is_encrypted:
            return True
        return doc.authenticate(password) > 0
    finally:
        doc.close()
