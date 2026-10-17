"""tools/features.py: hole / boss listing and the spec check."""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "tools", "features.py")
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import features as F  # noqa: E402
from build123d import Box, Cylinder, Pos, Rot, export_step  # noqa: E402


@pytest.fixture(scope="module")
def plate(tmp_path_factory):
    """80 x 50 x 10 plate: two 6.6 holes along Z at (+-30, 0) and one 8.0 hole along X through the middle."""
    part = Box(80, 50, 10) - Pos(-30, 0, 0) * Cylinder(3.3, 10) - Pos(30, 0, 0) * Cylinder(3.3, 10) \
        - Rot(0, 90, 0) * Cylinder(4.0, 80)
    p = str(tmp_path_factory.mktemp("feat") / "plate.step")
    export_step(part, p)
    return p, part


def test_holes_found(plate):
    _, part = plate
    hs = F.holes(part)
    z = sorted((h for h in hs if h["axis"] == "z"), key=lambda h: h["x"])
    assert [h["d"] for h in z] == [6.6, 6.6]
    assert z[0]["x"] == pytest.approx(-30) and z[1]["x"] == pytest.approx(30)
    xh = [h for h in hs if h["axis"] == "x"]
    assert len(xh) == 1 and xh[0]["d"] == 8.0


def spec(tmp_path, holes):
    s = tmp_path / "spec.json"
    s.write_text(json.dumps({"tolerance_mm": 0.05, "holes": holes}))
    return str(s)


def test_spec_pass_and_fail(plate, tmp_path):
    step, _ = plate
    ok = spec(tmp_path, [{"name": "A", "x": -30, "y": 0, "z": 0, "d": 6.6, "axis": "z"},
                         {"name": "B", "x": 30, "y": 0, "z": 0, "d": 6.6, "axis": "z"}])
    r = subprocess.run([sys.executable, TOOL, step, "--spec", ok], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "ALL PASS" in r.stdout
    bad = spec(tmp_path, [{"name": "moved", "x": -29.8, "y": 0, "z": 0, "d": 6.6, "axis": "z"}])
    r = subprocess.run([sys.executable, TOOL, step, "--spec", bad], capture_output=True, text=True, timeout=120)
    assert r.returncode == 1 and "FAIL  moved" in r.stdout
