"""
tests/test_session.py - Tests unitaires pour DocumentSession et historique Undo/Redo.
"""

import os
import pymupdf as fitz

from core.session import DocumentSession
from core.temp_manager import SessionTempManager


def test_session_load_and_working_copy(sample_vector_pdf, fresh_session):
    meta = fresh_session.load_document(sample_vector_pdf)
    assert meta.page_count == 3
    assert fresh_session.working_path is not None
    assert os.path.exists(fresh_session.working_path)
    assert fresh_session.working_path != sample_vector_pdf
    assert len(fresh_session.page_configs) == 3


def test_session_undo_redo(sample_vector_pdf, fresh_session):
    fresh_session.load_document(sample_vector_pdf)
    orig_working = fresh_session.working_path

    new_tmp1 = fresh_session.temp_manager.create_temp_file()
    doc1 = fitz.open(orig_working)
    doc1[0].set_rotation(90)
    doc1.save(new_tmp1)
    doc1.close()

    fresh_session.commit_working_copy(new_tmp1)
    assert fresh_session.can_undo is True
    assert fresh_session.can_redo is False
    assert fresh_session.working_path == new_tmp1

    assert fresh_session.undo() is True
    assert fresh_session.working_path == orig_working
    assert fresh_session.can_redo is True

    assert fresh_session.redo() is True
    assert fresh_session.working_path == new_tmp1
    assert fresh_session.can_undo is True


def test_session_page_actions(sample_vector_pdf, fresh_session):
    fresh_session.load_document(sample_vector_pdf)
    fresh_session.rotate_page(0, angle=90)
    assert fresh_session.page_configs[0].rotation == 90

    fresh_session.delete_page(2)
    assert len(fresh_session.page_configs) == 2

    fresh_session.apply_page_modifications_to_working_copy()
    assert fresh_session.metadata.page_count == 2
    assert fresh_session.can_undo is True


def test_session_save_to(sample_vector_pdf, fresh_session, test_temp_dir):
    fresh_session.load_document(sample_vector_pdf)
    dest_path = os.path.join(test_temp_dir, "saved_from_session.pdf")
    fresh_session.save_to(dest_path)
    assert os.path.exists(dest_path)
    assert os.path.getsize(dest_path) > 0


def test_session_temp_cleanup(sample_vector_pdf):
    tm = SessionTempManager(prefix="cleanup_test_")
    session = DocumentSession(temp_manager=tm)
    session.load_document(sample_vector_pdf)
    session_dir = tm.session_dir
    assert os.path.exists(session_dir)

    session.close()
    assert not os.path.exists(session_dir)
