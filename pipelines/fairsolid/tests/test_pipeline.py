"""End-to-end: simulated scan in, correctly scaled parametric STEP out.

The assertions are dimensional on purpose. A pipeline that produces a
beautifully shaped part at the wrong size, or 1 mm off the origin, passes
every shape-based check - and both of those were real bugs during development.
"""
from pathlib import Path

import pytest

from fairsolid.pipeline import Run, finish, prepare

ROOT = Path(__file__).parent.parent
SCAN = ROOT / "tests" / "data" / "scan.stl"

# Nominal geometry of tests/data/nominal.step
NOMINAL_BBOX = (50.0, 80.0, 22.0)
NOMINAL_HOLES = {16.0, 26.0, 6.0}


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    run_dir = tmp_path_factory.mktemp("run")
    prepare(SCAN, run_dir)
    return finish(run_dir, tol=0.15), Run(run_dir)


def test_orientations_offered(result):
    """Several defensible frames, not a fixed count.

    The count changed from 4 to 6 when bore axes became +Z candidates
    alongside face normals, so asserting an exact number just encodes
    today's heuristics. What matters is that a choice exists.
    """
    state, _ = result
    assert state["frame"]["n_options"] >= 2


def test_previews_rendered(result):
    """The human picks from pictures, so the pictures must exist."""
    state, _ = result
    previews = state["frame"]["previews"]
    assert len(previews) == state["frame"]["n_options"]
    for p in previews:
        assert Path(p).stat().st_size > 10_000, f"{p} looks empty"


def test_measured_diameters_match_nominal(result):
    state, _ = result
    got = [f["diameter"] for f in state["frame"]["features"]["cylinders"]]
    for nominal in NOMINAL_HOLES:
        best = min(got, key=lambda d: abs(d - nominal))
        assert abs(best - nominal) < 0.05, (
            f"no measured diameter near {nominal}; got {sorted(got)}")


def test_step_is_correctly_scaled(result):
    """The invariant the whole project turns on."""
    state, _ = result
    bbox = state["reconstruct"]["bbox_mm"]
    for got, want in zip(sorted(bbox), sorted(NOMINAL_BBOX)):
        assert abs(got - want) < 0.3, f"bbox {bbox} vs nominal {NOMINAL_BBOX}"


def test_part_sits_on_xy_plane(result):
    state, _ = result
    assert abs(state["reconstruct"]["zmin"]) < 1e-6


def test_reconstruction_is_parametric_not_soup(result):
    """A layered prism, not a bag of triangles."""
    state, _ = result
    r = state["reconstruct"]
    assert r["n_layers"] == 2, f"expected plate + boss, got {r['n_layers']}"
    assert r["bytes"] < 1_000_000, "STEP too large to be analytic geometry"
    circles = [h for layer in r["layers"] for h in layer["holes"]
               if h.startswith("circle")]
    assert len(circles) >= 4, f"expected circular holes, got {circles}"


def test_deviation_is_measured_and_graded(result):
    state, _ = result
    dev = state["deviation"]
    assert dev["verdict"] in {"PASS", "MARGINAL", "FAIL"}
    # Median is the honest central measure; p95/max are dominated by the
    # 17% of the surface the fixture deliberately occludes.
    assert dev["median_mm"] < 0.10, f"median deviation {dev['median_mm']:.4f} mm"


def test_faceted_fallback_is_a_solid(result):
    state, _ = result
    assert state["faceted"]["is_solid"] is True


def test_reconstruction_is_stable_across_runs(result):
    """RANSAC is stochastic; the committed frame must not be.

    A junk plane fitted to an occlusion crater once snapped the bottom layer
    to 9.978 mm, floating the whole part off the XY plane - and it only
    reproduced on some runs. Repeating the reconstruction catches that class
    of intermittency, which a single run cannot.
    """
    from fairsolid.stages.s50_reconstruct import reconstruct

    _, run = result
    zmins, bboxes = [], []
    for i in range(3):
        r = reconstruct(run.clean, run.frame, run.root / f"stability_{i}.step")
        zmins.append(r["zmin"])
        bboxes.append(sorted(round(v, 2) for v in r["bbox_mm"]))
    assert all(abs(z) < 1e-6 for z in zmins), f"part left the XY plane: {zmins}"
    assert all(b == bboxes[0] for b in bboxes), f"unstable bbox: {bboxes}"


def test_cli_prepare_and_choose_run_clean(tmp_path):
    """The CLI display path must actually execute.

    Every stage was covered by tests while `cli.py` still referenced
    `texture_reduction`, a key renamed to `flatness_gain` when the
    idealisation metric changed. 16 tests passed and the command died with a
    KeyError on the first real scan. Library-level tests cannot catch a typo in
    a format string, so this drives the commands the way a user does.
    """
    import subprocess
    import sys

    run_dir = tmp_path / "cli"
    for args in (
        ["prepare", str(SCAN), "--run", str(run_dir), "--poisson-depth", "8",
         "--target-faces", "40000"],
        ["choose", "0", "--run", str(run_dir), "--tol", "0.3",
         "--out", str(tmp_path / "part.step")],
        ["status", "--run", str(run_dir)],
        ["licenses"],
    ):
        proc = subprocess.run(
            [sys.executable, "-m", "fairsolid.cli", *args],
            capture_output=True, text=True, cwd=str(ROOT), timeout=1200,
        )
        assert proc.returncode == 0, (
            f"`fairsolid {args[0]}` exited {proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout[-3000:]}\n"
            f"--- stderr ---\n{proc.stderr[-3000:]}"
        )
        # Rich prints tracebacks to stdout and can still exit 0.
        assert "Traceback" not in proc.stdout, (
            f"`fairsolid {args[0]}` printed a traceback:\n{proc.stdout[-3000:]}"
        )
    assert (tmp_path / "part.step").stat().st_size > 1000


def test_faceted_solid_is_valid_and_single_shell(result):
    """A solid that merely imports is not good enough.

    The first knuckle export had the right bounding box, one solid and a
    plausible volume - and isValid() was False. trimesh's decimator had
    shattered a watertight 200k mesh into 25 components, sewing produced 9
    shells with gaps, and OCCT built a "solid" from the largest. It would very
    likely have been rejected on import.

    Checking is_solid alone missed it, which is why validity and shell count
    are asserted separately here.
    """
    state, _ = result
    fac = state["faceted"]
    assert fac["is_solid"] is True
    assert fac["is_valid"] is True, "sewn solid failed OCCT's validity check"
    assert fac["n_shells"] == 1, (
        f"sewing produced {fac['n_shells']} shells; decimation probably broke "
        "topology - stages 10 and 80 must use the same decimator")
    assert fac["watertight"] is True
    assert fac["fragment_warning"] is False
