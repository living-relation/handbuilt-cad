"""tools/cnc_check.py: no default minimum wall (never assumed), explicit value / spec / walls config, basic screen."""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "tools", "cnc_check.py")
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import cnc_check as CC  # noqa: E402
from build123d import Box, Pos, export_step  # noqa: E402


@pytest.fixture(scope="module")
def thin_part(tmp_path_factory):
    """60 x 40 x 20 block with a pocket leaving a 1.0 mm side wall (and 10 mm elsewhere)."""
    d = tmp_path_factory.mktemp("cnc")
    part = Box(60, 40, 20) - Pos(-4, 0, 5) * Box(50, 20, 10)       # pocket x -29..21 -> 1.0 mm wall at x = -30..-29
    p = str(d / "thin.step")
    export_step(part, p)
    return p


def run(step, *args):
    out = os.path.splitext(step)[0] + "_t" + str(abs(hash(args)) % 10000)
    r = subprocess.run([sys.executable, TOOL, step, "--out", out, *args], capture_output=True, text=True, timeout=300)
    js = json.load(open(out + ".json")) if os.path.exists(out + ".json") else None
    return r, js


def test_default_has_no_min_wall():
    assert CC.DEFAULTS["min_wall_mm"] is None
    assert CC.resolve_min_wall(dict(CC.DEFAULTS)) == (None, None)


def test_resolve_order_and_validation(tmp_path):
    toml = tmp_path / "walls.toml"
    toml.write_text("min_wall = 2.5\n[[parts]]\nname='x'\nfile='x.stl'\n")
    spec = dict(CC.DEFAULTS)
    assert CC.resolve_min_wall(spec, walls_config=str(toml)) == (2.5, "walls config walls.toml")
    assert CC.resolve_min_wall(dict(spec, min_wall_mm=1.8), walls_config=str(toml))[0] == 1.8
    assert CC.resolve_min_wall(dict(spec, min_wall_mm=1.8), cli=3.0, walls_config=str(toml)) == (3.0, "--min-wall")
    with pytest.raises(ValueError):
        CC.resolve_min_wall(spec, cli=0)
    bad = tmp_path / "bad.toml"
    bad.write_text("attach_min = 3.0\n")
    with pytest.raises(ValueError, match="min_wall"):
        CC.resolve_min_wall(spec, walls_config=str(bad))


def test_walls_not_checked_without_a_value(thin_part):
    r, js = run(thin_part)
    assert r.returncode == 0, r.stderr
    assert js["walls"]["checked"] is False and js["spec"]["min_wall_mm"] is None
    assert "Walls: not checked" in r.stdout and "never assumed" in r.stdout


def test_thin_wall_found_with_explicit_value(thin_part):
    r, js = run(thin_part, "--min-wall", "1.5")
    assert r.returncode == 0, r.stderr
    w = js["walls"]
    assert w["checked"] and w["min_wall_set_mm"] == 1.5 and w["source"] == "--min-wall"
    assert w["thin_spots"] and min(s["t_mm"] for s in w["thin_spots"]) == pytest.approx(1.0, abs=0.1)
    assert "candidates" in r.stdout and "structural" in r.stdout
    r2, _ = run(thin_part, "--min-wall", "1.5", "--strict")
    assert r2.returncode == 1                                            # --strict: flagged -> exit 1 (opt-in)


def test_value_under_the_wall_passes_walls(thin_part):
    r, js = run(thin_part, "--min-wall", "0.8")
    assert js["walls"]["checked"] and js["walls"]["thin_spots"] == []


def test_spec_and_walls_config(thin_part, tmp_path):
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps({"min_wall_mm": 1.2}))
    _, js = run(thin_part, "--spec", str(spec))
    assert js["walls"]["source"] == "spec min_wall_mm" and js["walls"]["thin_spots"]
    toml = tmp_path / "w.toml"
    toml.write_text("min_wall = 0.5\n")
    _, js = run(thin_part, "--walls-config", str(toml))
    assert js["walls"]["min_wall_set_mm"] == 0.5 and js["walls"]["thin_spots"] == []


def test_bad_min_wall_exits(thin_part):
    r, _ = run(thin_part, "--min-wall", "-1")
    assert r.returncode != 0 and "minimum wall" in r.stderr


def test_screen_reports_setups_and_corners(thin_part):
    _, js = run(thin_part)
    assert js["n_solids"] == 1 and js["valid"]
    assert js["setups"]                                                 # at least one tool direction
    assert len(js["vertical_corners"]) == 4                             # the 4 sharp pocket corners a Z-down cutter can't make
