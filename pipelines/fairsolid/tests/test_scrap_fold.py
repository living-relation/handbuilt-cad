"""Folding unfitted scraps into the fitted surface they continue (stage 30).

After fitting, much of what is still 'other' is crumbs: the strip along a
flat's edge, a crumb between split pieces. A scrap face joins the area next
to it only when it lies within the tolerance of that area's surface AS
FITTED (the flat is not refitted, so it stays exactly as straight), and only
when the area still passes - or, if it already missed, misses by no more
than before.

Flat plates at about the pedal scan's spacing, true millimetres.
"""
import numpy as np
import trimesh

from fairsolid.stages.s30_fit import (
    _fold_ok, face_normals_smoothed, flat_off_limit, fold_scraps, texture_limit,
)

NOISE = 0.092
TOL = 0.184
STEP = 0.5
MIN_PATCH = 30.0
Z = np.array([0.0, 0.0, 1.0])


def _plate(nx, ny, height=None, seed=0, texture=0.02):
    """Grid plate in x-y; `height(x, y)` lifts parts of it."""
    xs = np.arange(nx) * STEP
    ys = np.arange(ny) * STEP
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    H = np.zeros_like(X) if height is None else height(X, Y)
    V = np.column_stack([X.ravel(), Y.ravel(), H.ravel()])
    V += np.random.default_rng(seed).normal(0.0, texture, V.shape)
    i, j = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1), indexing="ij")
    a = (i * ny + j).ravel()
    b, c, d = a + 1, a + ny, a + ny + 1
    F = np.vstack([np.column_stack([a, c, b]), np.column_stack([b, c, d])])
    return trimesh.Trimesh(vertices=V, faces=F, process=False)


def _flat_area(aid, fm, W, p95=0.02, within=True):
    st = {"rms_mm": 0.0, "mean_abs_mm": 0.0, "p95_mm": p95, "max_mm": p95, "n_points": 0}
    return {"id": aid, "type": "flat", "kind": "plane", "_n": Z.copy(), "_d": 0.0,
            "_fmask": fm.copy(), "area_mm2": float(W[fm].sum()), "n_faces": int(fm.sum()),
            "within_tol": within, "within_tol_raw": within,
            "final": dict(st), "judged": dict(st, within_tol=within), "snaps": []}


def _fold(mesh, lab, areas):
    verts = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    return fold_scraps(verts, faces, np.asarray(mesh.triangles_center, float),
                       face_normals_smoothed(mesh), np.asarray(mesh.area_faces, float),
                       np.asarray(mesh.face_adjacency), lab, areas, tol=TOL,
                       cap=texture_limit(NOISE), min_patch=MIN_PATCH,
                       flat_lim=flat_off_limit(NOISE, TOL))


def test_small_strip_continuing_a_flat_joins_it():
    mesh = _plate(41, 41)                      # 20 x 20 mm
    C = np.asarray(mesh.triangles_center)
    W = np.asarray(mesh.area_faces)
    strip = (C[:, 0] > 19.0)                   # 1 mm along one edge: 20 mm2
    assert 15.0 < W[strip].sum() < MIN_PATCH
    lab = np.where(strip, -1, 0).astype(np.int64)
    areas = [_flat_area(0, ~strip, W)]
    meta = _fold(mesh, lab, areas)
    assert np.all(lab[strip] == 0)
    a = areas[0]
    assert a["within_tol"], a["judged"]
    assert abs(a["area_mm2"] - W.sum()) < 0.01
    assert a["scraps_folded"]["faces"] == int(strip.sum())
    assert abs(meta["folded_mm2"] - W[strip].sum()) < 0.01
    assert meta["uncovered_after_mm2"] == 0.0
    # the flat itself was not refitted: still exactly z = 0
    assert np.array_equal(a["_n"], Z) and a["_d"] == 0.0


def test_scrap_off_the_flat_does_not_join_and_flat_is_unchanged():
    # the strip is a step 0.5 mm up: more of something else, not this flat
    mesh = _plate(41, 41, height=lambda X, Y: np.where(X > 19.0 - 1e-9, 0.5, 0.0))
    C = np.asarray(mesh.triangles_center)
    W = np.asarray(mesh.area_faces)
    strip = C[:, 0] > 19.0
    lab = np.where(strip, -1, 0).astype(np.int64)
    flat_faces = ~strip
    areas = [_flat_area(0, flat_faces, W)]
    before = dict(areas[0])
    meta = _fold(mesh, lab, areas)
    assert np.all(lab[strip] == -1)
    assert np.array_equal(areas[0]["_fmask"], flat_faces)
    assert areas[0]["area_mm2"] == before["area_mm2"]
    assert "scraps_folded" not in areas[0]
    assert meta["folded_mm2"] == 0.0
    assert meta["uncovered_after_mm2"] > 0.0


def test_fold_that_would_worsen_the_neighbour_is_refused():
    passed = {"within_tol": True, "judged": {"p95_mm": 0.10}}
    missed = {"within_tol": False, "judged": {"p95_mm": 0.50}}

    def trial(p95, ok):
        return {"pc": {"stats": {"p95_mm": p95, "within_tol": ok}}}
    assert _fold_ok(passed, trial(0.15, True))
    assert not _fold_ok(passed, trial(0.19, False))       # would stop passing
    assert _fold_ok(missed, trial(0.45, False))           # misses by less
    assert not _fold_ok(missed, trial(0.55, False))       # would miss by more
