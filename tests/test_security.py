"""
tests/test_security.py - Tests unitaires pour le chiffrement AES-256 et déverrouillage.
"""

import os
import pymupdf as fitz
import pytest

from core.security import protect_pdf, unlock_pdf, verify_pdf_password


def test_protect_pdf_aes256(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "test_protected.pdf")
    password = "SuperPassword2026!"
    protect_pdf(sample_vector_pdf, out_pdf, password=password)

    doc = fitz.open(out_pdf)
    assert doc.is_encrypted
    assert not doc.authenticate("MauvaisMotDePasse")
    assert doc.authenticate(password) > 0
    doc.close()


def test_protect_pdf_empty_password_raises(sample_vector_pdf, test_temp_dir):
    out_pdf = os.path.join(test_temp_dir, "should_fail.pdf")
    with pytest.raises(ValueError):
        protect_pdf(sample_vector_pdf, out_pdf, password="")


def test_verify_pdf_password(sample_encrypted_pdf):
    assert verify_pdf_password(sample_encrypted_pdf, "Secret123!") is True
    assert verify_pdf_password(sample_encrypted_pdf, "WrongPassword") is False


def test_unlock_pdf(sample_encrypted_pdf, test_temp_dir):
    unlocked_pdf = os.path.join(test_temp_dir, "test_unlocked.pdf")
    assert unlock_pdf(sample_encrypted_pdf, unlocked_pdf, password="Secret123!")

    doc = fitz.open(unlocked_pdf)
    assert not doc.is_encrypted
    assert len(doc) == 3
    doc.close()


def test_unlock_pdf_wrong_password(sample_encrypted_pdf, test_temp_dir):
    unlocked_pdf = os.path.join(test_temp_dir, "test_unlocked_failed.pdf")
    assert not unlock_pdf(
        sample_encrypted_pdf, unlocked_pdf, password="MauvaisMotDePasse"
    )
