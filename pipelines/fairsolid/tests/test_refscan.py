"""Reference scan mode (stage 40, plan part 10).

A synthetic 'space' scan in true millimetres: an open floor panel, a wall
leaning back from it at a crease, a gently curved roof panel, and a small
floating scrap. It is built in the canonical frame and moved out by a frame
with a real rotation and origin, so the stage has to move it back (rigidly,
never scaled). Nothing here is a closed solid and none of it should become one.
"""
import json
from pathlib import Path

import numpy as np
import pytest
import trimesh

from fairsolid.geom import Frame, orthonormalise
from fairsolid.pipeline import refscan
from fairsolid.stages.s40_refscan import (
    grow_patches, point_to_mesh, raw_outline, rigid_to_frame, tidy_outline, turning,
)
from fairsolid.subproc import run_module

NOISE = 0.04


def _grid(f, u, v):
    U, V = np.meshgrid(u, v, indexing="ij")
    P = f(U, V).reshape(-1, 3)
    nu, nv = len(u), len(v)
    i, j = np.meshgrid(np.arange(nu - 1), np.arange(nv - 1), indexing="ij")
    a = (i * nv + j).ravel(); b = a + nv
    F = np.vstack([np.column_stack([a, b, a + 1]), np.column_stack([b, b + 1, a + 1])])
    return trimesh.Trimesh(P, F, process=False)


def _space(seed=0):
    """Floor z=0 (x 0..60, y 0..40) running into a wall that leans back 20 deg
    from x=60 (one connected sheet with a 70 deg crease), a curved roof (sag
    3 mm over 50 mm), and a 3 mm scrap floating free."""
    t = np.radians(20)

    def sheet(U, V):
        w = np.clip(U - 60, 0, None)
        return np.stack([np.minimum(U, 60) + w * np.sin(t), V, w * np.cos(t)], -1)
    floor_wall = _grid(sheet, np.arange(0, 95.01, 0.6), np.arange(0, 40.01, 0.6))
    roof = _grid(lambda U, V: np.stack([U, V, 45 - 3 * np.sin(np.pi * U / 50)], -1),
                 np.arange(0, 50.01, 0.6), np.arange(0, 40.01, 0.6))
    scrap = trimesh.creation.icosphere(subdivisions=2, radius=1.5); scrap.apply_translation([20, 20, 20])
    m = trimesh.util.concatenate([floor_wall, roof, scrap])
    m.vertices = m.vertices + np.random.default_rng(seed).normal(0, NOISE, m.vertices.shape)
    return m


def _frame():
    R = orthonormalise(np.array([0.2, -0.3, 1.0]), np.array([1.0, 0.4, 0.0]))
    return Frame(rotation=R.tolist(), origin=[12.0, -7.0, 30.0])


def _write_run(tmp_path: Path) -> Path:
    fr = _frame()
    canon = _space()
    scan = trimesh.Trimesh(fr.from_canonical(canon.vertices), canon.faces, process=False)
    run = tmp_path / "run"; run.mkdir()
    scan.export(run / "00_scan.ply")
    fr.save(run / "20_frame.json")
    return run


# -- helpers -------------------------------------------------------------------

def test_rigid_move_never_scales():
    m = _space()
    out, info = rigid_to_frame(m, _frame())
    assert info["scale_applied"] is False
    assert info["edge_length_ratio"] == pytest.approx(1.0, abs=1e-9)
    assert out.extents.prod() > 0
    bad = Frame(rotation=(np.eye(3) * 25.4).tolist())
    with pytest.raises(ValueError, match="size"):
        rigid_to_frame(m, bad)


def test_patches_split_at_crease_and_drop_scrap():
    m = _space()
    patches = grow_patches(m)
    assert len(patches) == 3                      # floor, wall, roof; scrap too small
    normals = [np.asarray(m.face_normals)[p].mean(0) for p in patches]
    assert any(abs(n[2]) > 0.95 for n in normals)


def test_tidy_outline_removes_stair_steps_keeps_size():
    rng = np.random.default_rng(1)
    th = rng.uniform(0, 2 * np.pi, 4000); r = 20 * np.sqrt(rng.uniform(0, 1, 4000))
    uv = np.column_stack([r * np.cos(th), r * np.sin(th)])
    raw = raw_outline(uv, 2.5)
    tidy = tidy_outline(raw, 2.5)
    assert turning(tidy) < 0.5 * turning(raw.simplify(2.5 / 3))
    assert turning(tidy) < 1.3
    # the cell union overshoots the true footprint by about half a cell; the tidy outline is back on it
    assert tidy.area == pytest.approx(np.pi * 20 ** 2, rel=0.05)
    assert tidy.area <= raw.area
    assert tidy.is_valid


def test_point_to_mesh_is_exact_distance():
    plane = trimesh.creation.box(extents=[50, 50, 1]); plane.apply_translation([0, 0, -0.5])
    pts = np.array([[0, 0, 2.0], [5, -3, 0.25], [-10, 10, 7.5]])
    assert np.allclose(point_to_mesh(pts, plane), [2.0, 0.25, 7.5], atol=1e-6)


def test_refscan_needs_a_frame(tmp_path):
    run = tmp_path / "r"; run.mkdir()
    trimesh.creation.box().export(run / "00_scan.ply")
    with pytest.raises(FileNotFoundError, match="frame"):
        refscan(run)


# -- the stage, end to end --------------------------------------------------------

def test_refscan_open_surfaces_and_datums(tmp_path):
    run = _write_run(tmp_path)
    res = refscan(run)
    rep = json.loads(Path(res["report"]).read_text())
    assert rep["scale_applied"] is False
    assert res["n_surfaces"] >= 3
    for k in ("surfaces_step", "surfaces_stl", "datums_step", "render"):
        assert Path(res["files"][k]).exists()
    assert "OPEN_SHELL" in Path(res["files"]["surfaces_step"]).read_text() or \
           "ADVANCED_FACE" in Path(res["files"]["surfaces_step"]).read_text()
    on = res["metrics"]["on_panels"]
    assert on["share_of_scan_pct"] > 90
    assert on["median_mm"] < 0.06 and on["pct_within_0.2mm"] > 95
    # back in the canonical frame: the floor is a datum plane at z=0, normal +-Z
    planes = res["datums"]["planes"]
    floor = [p for p in planes if abs(p["normal"][2]) > 0.999 and abs(p["point"][2]) < 0.1]
    assert floor, planes
    wall = [p for p in planes if abs(abs(p["normal"][0]) - np.cos(np.radians(20))) < 0.01]
    assert wall, planes
    assert any(p["plane_rms_mm"] > 0.5 for p in res["datums"]["points"])   # the curved roof
    assert res["edges"]["mean_turns_tidy"] <= res["edges"]["mean_turns_raw"]
    st = json.loads((run / "state.json").read_text())
    assert st["mode"] == "reference"


def test_refscan_knit_and_patch_box(tmp_path):
    run = _write_run(tmp_path)
    res = run_module("fairsolid.stages.s40_refscan",
                     [str(run / "00_scan.ply"), str(run / "20_frame.json"), str(run),
                      "--knit", "--knit-tol", "2.0", "--patch-box", "50", "-1", "-1", "70", "41", "15"])
    assert res["knit"]["tolerance_mm"] == 2.0
    assert res["knit"]["free_edges"] > 0          # an open scan stays open
    rep = json.loads(Path(res["report"]).read_text())
    boxes = [p for p in rep["patches"] if "patch_box" in p]
    assert boxes and boxes[0]["ok"] and boxes[0]["n_points"] > 30
