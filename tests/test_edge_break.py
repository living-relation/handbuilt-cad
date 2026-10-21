import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build123d import Box  # noqa: E402
from edge_break import edge_break  # noqa: E402


def test_edge_break_box_stays_one_valid_solid():
    box = Box(20, 20, 20)
    part, ok, failed = edge_break(box, 1.0)
    assert ok > 0
    assert part.is_valid and len(part.solids()) == 1
    assert part.volume < 8000.0


def test_edge_break_skips_short_edges():
    part, ok, failed = edge_break(Box(3, 3, 3), 0.5, min_len=4.0)
    assert ok == 0 and failed == 0
    assert abs(part.volume - 27.0) < 1e-6
