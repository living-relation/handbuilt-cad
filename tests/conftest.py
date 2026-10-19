import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import pytest


@pytest.fixture(autouse=True)
def _test_requester(monkeypatch):
    """Drawings need the requester's initials (drawing/settings.py); tests use a test person, never the PC's file."""
    monkeypatch.setenv("DRAWING_INITIALS", "TP")
