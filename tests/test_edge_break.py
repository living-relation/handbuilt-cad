import sys
from pathlib import Path

import pytest

bd = pytest.importorskip("build123d")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from edge_break import edge_break  # noqa: E402


def test_edge_break_box_stays_one_valid_solid():
    part, ok, failed = edge_break(bd.Box(20, 20, 20), 1.0)
    assert ok > 0
    assert part.is_valid and len(part.solids()) == 1
    assert part.volume < 8000.0


def test_edge_break_skips_short_edges():
    part, ok, failed = edge_break(bd.Box(3, 3, 3), 0.5, min_len=4.0)
    assert ok == 0 and failed == 0
    assert abs(part.volume - 27.0) < 1e-6


def two_boxes():
    return bd.Compound([bd.Box(10, 10, 10).solid(), bd.Pos(30, 0, 0) * bd.Box(20, 20, 20).solid()])


def test_edge_break_refuses_several_solids():
    with pytest.raises(ValueError):
        edge_break(two_boxes(), 0.5)


def test_edge_break_allow_multi_uses_largest():
    part, ok, failed = edge_break(two_boxes(), 0.5, allow_multi=True)
    assert part.volume > 7000.0


def test_cli_writes_step_only_unless_stl(tmp_path):
    import edge_break as eb
    src = tmp_path / "box.step"
    bd.export_step(bd.Box(10, 10, 10), str(src))
    eb.main([str(src), str(tmp_path / "a"), "0.5"])
    assert (tmp_path / "a.step").exists() and not (tmp_path / "a.stl").exists()
    eb.main([str(src), str(tmp_path / "b"), "0.5", "--stl"])
    assert (tmp_path / "b.stl").exists()
