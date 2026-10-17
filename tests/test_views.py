"""tools/views.py: the z-buffer six-view renderer and the sheet writer (no display needed)."""
import os
import sys

import numpy as np
import pytest
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import views as V  # noqa: E402


def test_render_view_shape_and_content():
    m = trimesh.creation.box((20, 10, 5))
    img = V.render_view(m, (0, 1, 0), (0, 0, 1), size=120, ss=2)
    assert img.shape == (120, 120, 3)
    assert img.max() == pytest.approx(1.0)                              # white background
    grey = img[60, 60, 0]
    assert img.min() < grey - 0.1                                       # darker outline round the part
    assert 0.22 <= grey <= 0.8                                          # the part, flat grey, no triangle seams:
    assert np.allclose(img[50:70, 40:80, 0], grey, atol=1e-6)           # one even shade over the face


def test_front_view_aspect():
    m = trimesh.creation.box((40, 10, 10))
    img = V.render_view(m, (0, 1, 0), (0, 0, 1), size=200, ss=1)[:, :, 0]
    rows, cols = np.where(img < 0.95)
    w, h = cols.max() - cols.min(), rows.max() - rows.min()
    assert w / h == pytest.approx(4.0, rel=0.1)                        # 40 wide, 10 tall seen from the front


def test_six_sheet_and_step_load(tmp_path):
    from build123d import Box, export_step
    step = str(tmp_path / "b.step")
    export_step(Box(20, 10, 5), step)
    m = V.load(step)
    assert m.is_watertight and m.volume == pytest.approx(1000, rel=1e-3)
    out = str(tmp_path / "six.png")
    V.six_sheet(m, "box", out)
    assert os.path.getsize(out) > 10_000
