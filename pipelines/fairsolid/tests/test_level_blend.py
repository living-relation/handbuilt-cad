"""Level blends (stage 30 split).

Two fitted flats facing the same way at different heights, joined by an
unfitted ramp, get a clean blend swept straight along the step: a chamfer,
an ogee round tangent to both flats, or a smooth tangent cubic, whichever
fits best, with its angle, radius or width snapped. the user: the solid should
look like a perfect machined part. A bumpy band is not a blend, and flats at
the same height are not a step.

Height fields at about the pedal scan's spacing, true millimetres.
"""
import numpy as np
import trimesh

from fairsolid.stages.s30_fit import (
    blend_residual, face_normals_smoothed, find_level_blends, texture_limit,
)

NOISE = 0.092
TOL = 0.184
Z = np.array([0.0, 0.0, 1.0])


def _field(zfun, x0=-8.0, x1=12.0, y1=20.0, step=0.3, seed=0, texture=0.02):
    xs = np.arange(x0, x1 + 1e-9, step)
    ys = np.arange(0.0, y1 + 1e-9, step)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Zs = zfun(X, Y) + np.random.default_rng(seed).normal(0.0, texture, X.shape)
    V = np.column_stack([X.ravel(), Y.ravel(), Zs.ravel()])
    nx, ny = X.shape
    i, j = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1), indexing="ij")
    a = (i * ny + j).ravel()
    b, c, d = a + ny, a + 1, a + ny + 1
    F = np.vstack([np.column_stack([a, b, c]), np.column_stack([b, d, c])])
    m = trimesh.Trimesh(vertices=V, faces=F, process=False)
    if m.face_normals[:, 2].mean() < 0:
        m.invert()
    return m


def _run(mesh, lo_until, hi_from, h):
    verts = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    W = np.asarray(mesh.area_faces, float)
    N = face_normals_smoothed(mesh)
    C = np.asarray(mesh.triangles_center, float)
    adj = np.asarray(mesh.face_adjacency)
    lo = C[:, 0] < lo_until
    hi = C[:, 0] > hi_from
    lab = np.full(len(W), -1, dtype=np.int64)
    lab[lo], lab[hi] = 0, 1
    z0 = {"p95_mm": 0.0, "max_mm": 0.0, "rms_mm": 0.0}
    areas = []
    for k, (fm, d) in enumerate(((lo, 0.0), (hi, h))):
        vi = np.unique(faces[fm])
        areas.append({"id": k, "type": "flat", "kind": "plane", "_n": Z.copy(), "_d": d,
                      "_fmask": fm, "_pts": verts[vi], "area_mm2": float(W[fm].sum()),
                      "within_tol": True, "final": z0, "judged": z0, "snaps": []})

    def accept(fm, a):
        lab[fm] = a["id"]
        areas.append(a)
    meta = find_level_blends(verts, faces, C, N, W, adj, lab < 0, lab, areas, nf=NOISE,
                             tol=TOL, label_dist=max(3 * NOISE, TOL),
                             cap=texture_limit(NOISE), table="metric", accept=accept)
    return meta, areas, lab, C


def _chamfer(h=3.0, w=3.0):
    return lambda X, Y: h * np.clip(X / w, 0, 1)


def _ogee(h=3.0, R=2.0):
    phi = np.arccos(1 - h / (2 * R))
    w = 2 * R * np.sin(phi)

    def z(X, Y):
        out = np.where(X <= 0, 0.0, h)
        a = (X > 0) & (X <= w / 2)
        out = np.where(a, R - np.sqrt(np.maximum(R * R - X * X, 0)), out)
        b = (X > w / 2) & (X < w)
        out = np.where(b, h - (R - np.sqrt(np.maximum(R * R - (w - X) ** 2, 0))), out)
        return out
    return z, w


def test_45_degree_ramp_between_two_levels_is_a_snapped_chamfer():
    meta, areas, lab, C = _run(_field(_chamfer()), lo_until=-1.0, hi_from=4.0, h=3.0)
    bl = [a for a in areas if a["type"] == "blend"]
    assert len(bl) == 1, meta["tried"]
    b = bl[0]
    assert b["kind"] == "level_blend"
    assert b["blend"]["profile"] == "chamfer", meta["tried"]
    assert abs(b["blend"]["angle_deg"] - 45.0) < 1e-6, b["blend"]                # snapped
    assert set(b["blend"]["between_flats"]) == {0, 1}
    assert b["within_tol"], b["judged"]
    ramp = (C[:, 0] > 0.4) & (C[:, 0] < 2.6)
    assert np.mean(lab[ramp] == b["id"]) > 0.8


def test_rounded_step_is_an_ogee_round_tangent_to_both_flats():
    z, w = _ogee(h=3.0, R=2.0)
    meta, areas, lab, C = _run(_field(z), lo_until=-1.0, hi_from=w + 1.0, h=3.0)
    bl = [a for a in areas if a["type"] == "blend"]
    assert len(bl) == 1, meta["tried"]
    b = bl[0]
    assert b["blend"]["profile"] in ("round", "smooth"), meta["tried"]
    assert b["blend"]["tangent_to_both"]
    if b["blend"]["profile"] == "round":
        assert abs(b["blend"]["radius_mm"] - 2.0) < 1e-6, b["blend"]           # snapped
    assert b["within_tol"], b["judged"]


def test_blend_distance_is_zero_on_the_blend_and_signed_off_it():
    from fairsolid.stages.s30_fit import _blend_from
    bl = _blend_from("chamfer", 0.0, 3.0, 3.0, 0.0, Z, np.array([1.0, 0, 0]))
    P = np.array([[1.5, 0, 1.5], [-3.0, 0, 0.0], [6.0, 0, 3.0], [-3.0, 0, 0.5], [6.0, 0, 2.5]])
    r = blend_residual(P, bl)
    assert np.allclose(r[:3], 0.0, atol=0.01)
    assert r[3] > 0.45 and r[4] < -0.45


def test_bumpy_band_between_levels_is_not_a_blend():
    def z(X, Y):
        return 3.0 * np.clip(X / 3.0, 0, 1) + np.where((X > 0) & (X < 3), 0.6 * np.sin(Y * 1.3), 0)
    meta, areas, lab, C = _run(_field(z), lo_until=-1.0, hi_from=4.0, h=3.0)
    assert not [a for a in areas if a["type"] == "blend" and a["within_tol"]], meta["tried"]
    assert not [a for a in areas if a["type"] == "blend"], meta["tried"]


def test_flats_at_the_same_height_are_not_a_step():
    def z(X, Y):
        return np.where((X > 0) & (X < 3), 0.8 * np.sin(np.pi * X / 3), 0.0)
    meta, areas, lab, C = _run(_field(z), lo_until=-1.0, hi_from=4.0, h=0.0)
    assert not [a for a in areas if a["type"] == "blend"]
    assert meta["tried"] == []
