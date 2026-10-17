"""Stage 30 - area map, least-squares fits, snapping, size check, report.

Plan part 3 (docs/SURFACE_FIT_PLAN.md). Two parts with known sizes:

* the stepped part (70 x 70 x 8 plate on a d30 x 20 boss, d12 bore through),
  built from CAD, given scan-like noise and averaged by the real stage 10;
* the existing plate fixture (tests/data/scan.stl, 80 x 50 x 12 plate,
  d26 boss, d16 bore, four d6 holes), run through prepare like a real scan.

Sizes are asserted in true millimetres. Nothing is ever rescaled, and the
unit setting is shown to change only the hole table.
"""
import json
from pathlib import Path

import numpy as np
import pytest
import trimesh

from fairsolid.geom import Frame
from fairsolid.pipeline import Run, fit, prepare
from fairsolid.stages import s30_fit
from fairsolid.stages.s30_fit import (
    SizeCheckError, check_size, guess_units, run_fit, snap_hole,
)
from fairsolid.subproc import run_module

ROOT = Path(__file__).parent.parent
PLATE_SCAN = ROOT / "tests" / "data" / "scan.stl"

PLATE, PLATE_T, BOSS_D, BOSS_H, BORE_D = 70.0, 8.0, 30.0, 20.0, 12.0
INCH = 25.4


# -- unit tests: the guards -----------------------------------------------

def test_size_check_stops_on_inch_mixup():
    scan = np.array([80.0, 50.0, 22.0])
    for wrong in (scan * INCH, scan / INCH):
        with pytest.raises(SizeCheckError, match="25.4"):
            check_size(wrong, scan, 0.1)


def test_size_check_stops_when_off_and_passes_when_close():
    scan = np.array([80.0, 50.0, 22.0])
    with pytest.raises(SizeCheckError, match="off the scan"):
        check_size(scan + [0.0, 0.3, 0.0], scan, 0.1)
    assert check_size(scan + [0.05, -0.05, 0.0], scan, 0.1)["status"] == "PASS"


def test_hole_tables_and_unit_guess():
    assert snap_hole(16.03, "metric", 0.1) == 16.0
    assert snap_hole(6.35, "inch", 0.05) == pytest.approx(0.25 * INCH)
    assert snap_hole(12.0, "inch", 0.1) == pytest.approx(15 / 32 * INCH)
    assert snap_hole(12.5 + 0.21, "metric", 0.05) is None
    assert guess_units([6.0, 16.0, 8.5])[0] == "metric"
    assert guess_units([6.35, 12.7, 9.525])[0] == "inch"
    assert guess_units([])[0] == "metric"


# -- stepped part ------------------------------------------------------------

@pytest.fixture(scope="module")
def stepped_run(tmp_path_factory):
    """Stepped part through stage 10 (the averaged surface), identity frame."""
    import cadquery as cq

    d = tmp_path_factory.mktemp("fit_stepped")
    part = (cq.Workplane("XY").circle(BOSS_D / 2).extrude(BOSS_H)
            .faces(">Z").workplane().rect(PLATE, PLATE).extrude(PLATE_T)
            .faces(">Z").workplane().circle(BORE_D / 2).cutThruAll())
    stl = d / "nominal.stl"
    cq.exporters.export(part, str(stl), tolerance=0.01, angularTolerance=0.1)
    mesh = trimesh.load(stl, force="mesh", process=True)
    mesh = mesh.subdivide_to_size(max_edge=1.0)
    rng = np.random.default_rng(3)
    mesh.vertices = mesh.vertices + rng.normal(0, 0.03, mesh.vertices.shape)
    mesh.export(d / "scan.ply")
    run_module("fairsolid.stages.s10_sanitize", [
        str(d / "scan.ply"), str(d / "10_clean.ply"),
        "--poisson-depth", "8", "--target-faces", "60000"])
    Frame(notes=["identity test frame"]).save(d / "20_frame.json")
    return d


@pytest.fixture(scope="module")
def stepped(stepped_run):
    d = stepped_run
    return run_fit(d / "10_clean.ply", d / "20_frame.json", d / "metric")


@pytest.fixture(scope="module")
def stepped_inch(stepped_run):
    d = stepped_run
    return run_fit(d / "10_clean.ply", d / "20_frame.json", d / "inch", units="inch")


def _rounds(rep, kind):
    return [a for a in rep["areas"] if a["kind"] == kind]


def test_stepped_tolerance_recorded(stepped):
    t = stepped["tolerance"]
    assert t["set_by"] == "default" and t["in_band"]
    assert 0.1 <= t["value_mm"] <= 0.2          # 70 mm part: large-object band
    assert stepped["scale_applied"] == 1.0 and stepped["scale_locked"]


def test_stepped_area_map(stepped):
    assert stepped["summary"]["n_flat"] >= 7    # top, underside, boss bottom, 4 sides
    assert len(_rounds(stepped, "hole")) == 1
    assert len(_rounds(stepped, "boss")) == 1
    assert stepped["faces"]["other_area_frac"] < 0.15
    png = Path(stepped["preview"])
    assert png.exists() and png.stat().st_size > 20_000
    labels = np.load(stepped["labels"])
    assert labels.shape == (stepped["faces"]["total"],)


def test_stepped_bore_snaps_to_metric_size(stepped):
    assert stepped["units"]["guess"] == "metric"
    bore = _rounds(stepped, "hole")[0]
    assert abs(bore["fit"]["diameter_mm"] - BORE_D) < 0.1
    assert bore["final"]["diameter_mm"] == BORE_D
    boss = _rounds(stepped, "boss")[0]
    assert abs(boss["final"]["diameter_mm"] - BOSS_D) < 0.1
    assert "not snapped" in boss["standard_size"]["note"]


def test_stepped_bore_and_boss_exactly_coaxial(stepped):
    bore, boss = _rounds(stepped, "hole")[0], _rounds(stepped, "boss")[0]
    groups = [g for g in stepped["snaps"]["coaxial"] if g["snapped"]]
    assert any({bore["id"], boss["id"]} <= set(g["snapped"]) for g in groups)
    a1, a2 = np.array(bore["final"]["axis"]), np.array(boss["final"]["axis"])
    assert abs(abs(a1 @ a2) - 1) < 1e-12
    dp = np.array(bore["final"]["point_mm"]) - np.array(boss["final"]["point_mm"])
    assert np.linalg.norm(dp - (dp @ a1) * a1) < 1e-3


def test_stepped_real_boss_passes_round_check(stepped):
    """The round check turns away freeform, not a real d30 boss."""
    rc = stepped["round_check"]
    assert "60%" in rc["rule"]
    assert stepped["summary"]["n_rounds_rejected"] == len(rc["rejected"])
    assert not any(r["stage"] == "area" and abs(r["diameter_mm"] - BOSS_D) < 1.0
                   for r in rc["rejected"]), rc["rejected"]


def test_stepped_real_flats_pass_flat_check(stepped):
    """The flat check turns away curves, not the stepped part's real faces."""
    fc = stepped["flat_check"]
    assert "bends" in fc["rule"] and fc["limit_mm"] <= stepped["tolerance"]["value_mm"]
    assert stepped["summary"]["n_flats_rejected"] == sum(f["rejected"] for f in fc["areas"])
    assert stepped["summary"]["n_flats_rejected"] == 0, fc["areas"]
    for f in fc["areas"]:                      # at most a sliver along an edge
        assert f["dropped_mm2"] <= 0.05 * f["area_mm2_before"], f


def test_stepped_planes_exactly_parallel_and_square(stepped):
    for a in stepped["areas"]:
        if a["type"] == "flat":
            n = np.abs(np.array(a["final"]["normal"]))
            assert sorted(np.round(n, 12)) == [0.0, 0.0, 1.0], a
    dists = sorted(p["distance_mm"] for p in stepped["parallel_pairs"]
                   if p["exactly_parallel"])
    for want in (PLATE_T, BOSS_H + PLATE_T, PLATE, PLATE):
        assert min(abs(np.array(dists) - want)) <= stepped["tolerance"]["value_mm"], (want, dists)


def test_stepped_size_check_and_fit_errors(stepped):
    sc = stepped["size_check"]
    assert sc["status"] == "PASS"
    assert np.allclose(sc["model_extents_mm"], [PLATE, PLATE, BOSS_H + PLATE_T], atol=0.2)
    worst = stepped["summary"]["worst_area"]
    assert worst["p95_mm"] < 0.2
    assert stepped["summary"]["n_within_tol"] >= stepped["summary"]["n_areas"] - 2


def test_unit_choice_only_picks_the_table(stepped, stepped_inch):
    """Inch changes the bore's snapped size to 15/32" and NOTHING else."""
    bore_in = _rounds(stepped_inch, "hole")[0]
    assert bore_in["final"]["diameter_mm"] == pytest.approx(15 / 32 * INCH, abs=1e-4)
    assert stepped_inch["units"]["table"] == "inch"
    assert stepped_inch["units"]["guess"] == "metric"     # the guess is still reported
    assert stepped_inch["size_check"]["scan_extents_mm"] == stepped["size_check"]["scan_extents_mm"]
    assert stepped_inch["size_check"]["model_extents_mm"] == stepped["size_check"]["model_extents_mm"]
    assert ([p["distance_mm"] for p in stepped_inch["parallel_pairs"]]
            == [p["distance_mm"] for p in stepped["parallel_pairs"]])


def test_size_check_stops_the_stage(stepped_run, monkeypatch, tmp_path):
    """A model 25.4x off its scan stops the run, after writing the report."""
    real = s30_fit.slab_extents

    def inflated(scan_pts, model_pts, band):
        me, se = real(scan_pts, model_pts, band)
        return me * INCH, se
    monkeypatch.setattr(s30_fit, "slab_extents", inflated)
    d = stepped_run
    with pytest.raises(SizeCheckError, match="25.4"):
        run_fit(d / "10_clean.ply", d / "20_frame.json", tmp_path)
    rep = json.loads((tmp_path / "30_fit.json").read_text())
    assert rep["status"] == "STOPPED" and rep["size_check"]["status"] == "STOPPED"
    assert rep["review"] and Path(rep["review"][0]).exists()


def test_bad_areas_get_review_pictures(stepped):
    bad = [a for a in stepped["areas"] if not a["within_tol"]]
    if not bad:
        assert stepped["review"] == []
        return
    paths = [Path(p) for p in stepped["review"]]
    assert paths[0].name == "30_deviation_overview.png" and paths[0].exists()
    for a in bad:
        assert any(p.name.startswith(f"30_area_{a['id']:02d}_") and p.exists() for p in paths)


# -- plate fixture, as a real run --------------------------------------------

@pytest.fixture(scope="module")
def plate(tmp_path_factory):
    run_dir = tmp_path_factory.mktemp("fit_plate")
    prepare(PLATE_SCAN, run_dir, poisson_depth=9, target_faces=100_000)
    res = fit(run_dir)
    return json.loads(Path(res["report"]).read_text()), Run(run_dir)


def test_plate_report_and_guards(plate):
    rep, run = plate
    assert rep["status"] == "OK" and rep["size_check"]["status"] == "PASS"
    assert rep["scale_applied"] == 1.0
    assert rep["tolerance"]["band"].startswith("large object")
    assert rep["units"]["guess"] == "metric"
    assert (run.root / "30_areas.png").exists()
    assert run.state()["fit"]["status"] == "OK"


def test_plate_holes_snap_to_nominal(plate):
    rep, _ = plate
    holes = [a["final"]["diameter_mm"] for a in rep["areas"] if a["kind"] == "hole"]
    bosses = [a["final"]["diameter_mm"] for a in rep["areas"] if a["kind"] == "boss"]
    assert 16.0 in holes, holes
    assert holes.count(6.0) >= 3, holes          # four corner holes, scan occludes some
    assert any(abs(b - 26.0) < 0.2 for b in bosses), bosses


def test_plate_dimensions_from_parallel_faces(plate):
    rep, _ = plate
    tol = rep["tolerance"]["value_mm"]
    dists = np.array([p["distance_mm"] for p in rep["parallel_pairs"] if p["exactly_parallel"]])
    for want in (80.0, 50.0, 12.0):
        assert np.min(np.abs(dists - want)) <= tol, (want, sorted(dists))
