"""Splitting a stiff patch that misses (stage 30, plan part 4).

A chart that one stiff spline cannot describe is split into what is really
there - flats first (same flat check), then rounds (same round check), then
smaller patches with the same stiff spline - instead of loosening it.
the user's goal: the solid should look like a perfect machined part, so the
simplest surface that is really there wins, and a patch that already passes
is left alone.

Height-field meshes at about the pedal scan's spacing, in true millimetres.
"""
import numpy as np
import trimesh

from fairsolid.stages.s30_fit import (
    assign_freeform, face_normals_smoothed, flat_off_limit,
)

NOISE = 0.092           # the pedal adapter's measured noise
TOL = 0.184             # 2 x noise, as the stage chose for it
SPACING = 0.5
MIN_PATCH = 4.0


def _height_mesh(fz, size=24.0, seed=0, texture=0.02):
    g = np.arange(-size / 2, size / 2 + 1e-9, SPACING)
    x, y = np.meshgrid(g, g)
    z = fz(x, y) + np.random.default_rng(seed).normal(0.0, texture, x.shape)
    V = np.column_stack([x.ravel(), y.ravel(), z.ravel()])
    n = len(g)
    i, j = np.meshgrid(np.arange(n - 1), np.arange(n - 1))
    a = (j * n + i).ravel()
    b, c, d = a + 1, a + n, a + n + 1
    F = np.vstack([np.column_stack([a, b, d]), np.column_stack([a, d, c])])
    return trimesh.Trimesh(vertices=V, faces=F, process=False)


def _run(mesh):
    verts = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    farea = np.asarray(mesh.area_faces, float)
    N = face_normals_smoothed(mesh)
    lab = np.full(len(faces), -1, dtype=np.int64)
    areas: list[dict] = []
    meta = assign_freeform(mesh, verts, faces, farea, N, lab, areas, nf=NOISE,
                           tol=TOL, min_patch=MIN_PATCH, label_dist=max(3 * NOISE, TOL),
                           flat_lim=flat_off_limit(NOISE, TOL),
                           directions=[np.array([0.0, 0.0, 1.0])])
    return meta, areas, lab, np.asarray(mesh.triangles_center, float)


def _shelf(x, y):
    """A gentle curve (R100 by R400) with a flat shelf 1 mm up for x >= 4,
    joined by a ramp of about 25 degrees: a curved patch with a flat in it."""
    bowl = x * x / 200.0 + y * y / 800.0
    top = 4.0 / 200.0 + 1.0
    edge = 2.0 * 2.0 / 200.0 + y * y / 800.0
    ramp = edge + (top - edge) * (x - 2.0) / 2.0
    return np.where(x <= 2.0, bowl, np.where(x >= 4.0, top, ramp))


def test_curved_patch_with_flat_shelf_splits_into_flat_and_curve():
    meta, areas, lab, C = _run(_height_mesh(_shelf))
    sp = meta["split"]
    assert sp is not None and sp["n_missed_patches"] == 1, sp
    flats = [a for a in areas if a["type"] == "flat"]
    curves = [a for a in areas if a["type"] == "freeform" and "split" in a]
    assert flats and curves, [(a["type"], a["area_mm2"]) for a in areas]
    shelf = max(flats, key=lambda a: a["area_mm2"])
    # The flat is the shelf: level, on top, and the curve is not cut into
    # facets (no flat on the gentle curve itself).
    assert abs(shelf["final"]["normal"][2]) > 0.999
    on = lab == shelf["id"]
    assert np.average(C[on, 0] >= 3.5, weights=np.ones(on.sum())) > 0.95
    assert all(np.mean(C[lab == f["id"], 0] >= 3.5) > 0.95 for f in flats)
    assert shelf["within_tol"], shelf["judged"]
    assert shelf["split"]["piece"] == "flat"
    assert all(c["split"]["piece"] == "curve" for c in curves)
    # Stiffness unchanged on every curve piece.
    assert all(c["fit"]["degree"] == 2 for c in curves)


def test_smooth_stiff_patch_that_passes_is_not_split():
    def bowl(x, y):
        return x * x / (2 * 60.0) + y * y / (2 * 90.0)
    meta, areas, lab, _ = _run(_height_mesh(bowl, seed=3, texture=0.06))
    assert len(areas) == 1
    a = areas[0]
    assert a["type"] == "freeform" and a["within_tol"], a["judged"]
    assert "split" not in a
    assert meta["split"] is None
    assert (lab == a["id"]).mean() > 0.99      # corner crumbs only
