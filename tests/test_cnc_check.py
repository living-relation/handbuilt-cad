"""tools/cnc_check.py: CNC wall floors, 1.3× corner rule, printed-process opt-out."""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "tools", "cnc_check.py")
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import cnc_check as CC  # noqa: E402
from build123d import Box, Pos, export_step, fillet  # noqa: E402


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


def test_cnc_default_uses_metal_floor():
    v, src, extra = CC.resolve_min_wall(dict(CC.DEFAULTS))
    assert v == pytest.approx(CC.CNC_WALL_METAL_MM)
    assert extra["process"] == "machined" and extra["fail_thin"] and extra["material"] == "metal"
    assert "0.762" in src


def test_cnc_plastic_floor():
    v, src, extra = CC.resolve_min_wall(dict(CC.DEFAULTS), material="plastic")
    assert v == pytest.approx(CC.CNC_WALL_PLASTIC_MM) and extra["material"] == "plastic"


def test_stricter_kept_looser_raised():
    v, src, extra = CC.resolve_min_wall(dict(CC.DEFAULTS), cli=2.0)
    assert v == 2.0 and src == "--min-wall"
    v, src, _ = CC.resolve_min_wall(dict(CC.DEFAULTS), cli=0.5)
    assert v == pytest.approx(CC.CNC_WALL_METAL_MM) and "raised" in src


def test_printed_has_no_default_wall(tmp_path):
    v, src, extra = CC.resolve_min_wall(dict(CC.DEFAULTS), process="printed")
    assert v is None and src is None and extra["fail_thin"] is False
    toml = tmp_path / "walls.toml"
    toml.write_text("min_wall = 2.5\n[[parts]]\nname='x'\nfile='x.stl'\n")
    v, src, extra = CC.resolve_min_wall(dict(CC.DEFAULTS), walls_config=str(toml), process="printed")
    assert v == 2.5 and src == "walls config walls.toml" and extra["fail_thin"] is False


def test_resolve_order_and_validation(tmp_path):
    toml = tmp_path / "walls.toml"
    toml.write_text("min_wall = 2.5\n[[parts]]\nname='x'\nfile='x.stl'\n")
    spec = dict(CC.DEFAULTS)
    assert CC.resolve_min_wall(spec, walls_config=str(toml))[0] == 2.5
    assert CC.resolve_min_wall(dict(spec, min_wall_mm=1.8), walls_config=str(toml))[0] == 1.8
    assert CC.resolve_min_wall(dict(spec, min_wall_mm=1.8), cli=3.0, walls_config=str(toml))[:2] == (3.0, "--min-wall")
    with pytest.raises(ValueError):
        CC.resolve_min_wall(spec, cli=0)
    bad = tmp_path / "bad.toml"
    bad.write_text("attach_min = 3.0\n")
    with pytest.raises(ValueError, match="min_wall"):
        CC.resolve_min_wall(spec, walls_config=str(bad), process="printed")


def test_default_run_checks_cnc_metal_floor(thin_part):
    r, js = run(thin_part)
    assert r.returncode == 0, r.stderr
    w = js["walls"]
    assert w["checked"] and w["fail_thin"] and w["min_wall_set_mm"] == pytest.approx(CC.CNC_WALL_METAL_MM)
    assert w["thin_spots"] == []          # 1.0 mm wall is above the 0.762 mm metal floor
    assert js["spec"]["process"] == "machined"


def test_printed_walls_not_checked_without_a_value(thin_part):
    r, js = run(thin_part, "--process", "printed")
    assert r.returncode == 0, r.stderr
    assert js["walls"]["checked"] is False and js["spec"]["min_wall_mm"] is None
    assert "Walls: not checked" in r.stdout


def test_thin_wall_fails_cnc(thin_part):
    r, js = run(thin_part, "--min-wall", "1.5")
    assert r.returncode == 0, r.stderr
    w = js["walls"]
    assert w["checked"] and w["fail_thin"] and w["min_wall_set_mm"] == 1.5 and w["source"] == "--min-wall"
    assert w["thin_spots"] and min(s["t_mm"] for s in w["thin_spots"]) == pytest.approx(1.0, abs=0.1)
    assert "FAIL" in r.stdout and js["failed"] is True
    r2, _ = run(thin_part, "--min-wall", "1.5", "--strict")
    assert r2.returncode == 1


def test_value_under_the_wall_passes_walls(thin_part):
    # 0.8 mm is slightly stricter than the 0.762 mm floor; 1.0 mm wall still passes
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
    # 0.5 is looser than the metal floor, so it is raised; 1.0 mm wall still passes
    assert js["walls"]["min_wall_set_mm"] == pytest.approx(CC.CNC_WALL_METAL_MM)
    assert js["walls"]["thin_spots"] == []
    assert "raised" in js["walls"]["source"]


def test_bad_min_wall_exits(thin_part):
    r, _ = run(thin_part, "--min-wall", "-1")
    assert r.returncode != 0 and "minimum wall" in r.stderr


def test_screen_reports_setups_and_corners(thin_part):
    _, js = run(thin_part)
    assert js["n_solids"] == 1 and js["valid"]
    assert js["setups"]
    assert len(js["vertical_corners"]) == 4


def test_corner_rule_1_3_and_exact():
    tools = [5.0]
    # 5 mm corner is an exact standard size and under 1.3×5 = 6.5
    a = CC.corner_rule(5.0, tools)
    assert a["exact_standard"] and a["under_1_3"] and a["required_r"] == pytest.approx(6.5)
    # 6.5 mm with a 5 mm tool passes 1.3× and is not a standard size
    b = CC.corner_rule(6.5, tools)
    assert not b["under_1_3"] and not b["exact_standard"]
    # 6.0 mm with a 5 mm tool is under 1.3× (the bracket's old 1.2×)
    c = CC.corner_rule(6.0, tools)
    assert c["under_1_3"]


def test_fillet_under_1_3_is_flagged(tmp_path):
    """A 5 mm inside fillet next to a 5 mm-radius tool fails the 1.3× rule; 6.5 mm passes."""
    def pocket(r):
        part = Box(40, 40, 12) - Pos(0, 0, 3) * Box(20, 20, 12)
        z_edges = [e for e in part.edges() if e.length > 1 and abs(e.tangent_at(0.5).Z) > 0.98
                   and abs(e.position_at(0.5).X) < 11 and abs(e.position_at(0.5).Y) < 11]
        if len(z_edges) < 4:
            raise AssertionError(f"expected 4 inside vertical edges, got {len(z_edges)}")
        return fillet(z_edges, r)

    low = pocket(5.0)
    high = pocket(6.5)
    p5 = str(tmp_path / "r5.step"); export_step(low, p5)
    p65 = str(tmp_path / "r65.step"); export_step(high, p65)
    spec = tmp_path / "tools.json"
    spec.write_text(json.dumps({"tool_radii_mm": [5.0], "min_wall_mm": 0.8}))
    r5, js5 = run(p5, "--spec", str(spec))
    assert r5.returncode == 0, r5.stderr
    assert js5["guide_corners"], js5.get("guide_corners")
    assert any(c["under_1_3"] or c["exact_standard"] for c in js5["guide_corners"])
    r65, js65 = run(p65, "--spec", str(spec))
    assert r65.returncode == 0, r65.stderr
    assert not js65["guide_corners"], js65.get("guide_corners")
