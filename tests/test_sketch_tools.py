"""Tests for tools/sketch_blend.py and tools/chamfer_batch.py (ported from handbuilt-models)."""
import math, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from build123d import Box
import sketch_blend as sb
import chamfer_batch as cb


def test_capsule_area():
    f = sb.capsule((0, 0), 10, (40, 0), 10)          # equal radii: stadium = rectangle + circle
    assert f.area == pytest.approx(40 * 20 + math.pi * 100, rel=1e-3)


def test_round_outline_keeps_area_and_prism_volume():
    sq = sb.poly_face([(0, 0), (50, 0), (50, 30), (0, 30)], rin=0, rout=4)
    assert sq.area < 50 * 30 and sq.area > 0.95 * 50 * 30          # only the 4 corners rounded
    assert sb.prism(sq, 0, 10).volume == pytest.approx(sq.area * 10, rel=1e-6)


def test_strict_fuse_fails_loudly_on_disjoint():
    a = Box(10, 10, 10); b = Box(10, 10, 10).moved(sb.Location((50, 0, 0)))
    with pytest.raises(sb.JoinError):
        sb.strict_fuse(a, b, 'disjoint')
    assert sb.strict_fuse(a, Box(10, 10, 10).moved(sb.Location((5, 0, 0))), 'overlap').volume == pytest.approx(1500, rel=1e-6)


def test_chamfer_batch_box():
    part, done, skipped = cb.chamfer_batch(Box(20, 20, 20).solids()[0], size=1.0)
    assert len(done) == 12 and not skipped
    assert part.is_valid and len(part.solids()) == 1
    assert part.volume < 8000
