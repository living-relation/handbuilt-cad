"""Short rings capped by flats at both ends (stage 30 split).

A boss 1 mm tall is all turn and no length: its wall is under the minimum
patch, so neither the round check nor the partial-round finder takes it. It
is a round when its axis is a part direction, it goes most of the way round,
it fits one radius within the noise multiple, and BOTH ends along the axis
stop at a flat square to the axis - the floor it stands on and its own top.
The top, unfitted, becomes a flat whose normal is exactly the axis. The same
ring with nothing on top (an open tube end) is not accepted.

Revolved profiles at about the pedal scan's spacing, true millimetres.
"""
import numpy as np
import trimesh

from fairsolid.stages.s30_fit import (
    face_normals_smoothed, find_capped_rings, flat_off_limit, texture_limit,
)

NOISE = 0.092
TOL = 0.184
Z = np.array([0.0, 0.0, 1.0])


def _revolve(profile, n_turn=120, seed=0, texture=0.02):
    """Mesh of an (r, z) polyline turned about Z; normals point away from
    the material for a profile running outside-in along the top."""
    pr = np.asarray(profile, float)
    th = np.linspace(0, 2 * np.pi, n_turn, endpoint=False)
    V = np.zeros((len(pr), n_turn, 3))
    V[:, :, 0] = pr[:, 0, None] * np.cos(th)[None, :]
    V[:, :, 1] = pr[:, 0, None] * np.sin(th)[None, :]
    V[:, :, 2] = pr[:, 1, None]
    V = V.reshape(-1, 3) + np.random.default_rng(seed).normal(0.0, texture, (len(pr) * n_turn, 3))
    i, j = np.meshgrid(np.arange(len(pr) - 1), np.arange(n_turn), indexing="ij")
    a = (i * n_turn + j).ravel()
    b = (i * n_turn + (j + 1) % n_turn).ravel()
    c, d = a + n_turn, b + n_turn
    F = np.vstack([np.column_stack([a, b, c]), np.column_stack([b, d, c])])
    m = trimesh.Trimesh(vertices=V, faces=F, process=False)
    if np.mean(m.face_normals[m.triangles_center[:, 2] < 0.1][:, 2]) < 0:
        m.invert()
    return m


def _line(p0, p1, step=0.4):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    n = max(2, int(np.ceil(np.linalg.norm(p1 - p0) / step)))
    return list(p0 + np.outer(np.linspace(0, 1, n + 1)[:-1], p1 - p0))


def _boss(top=True, r=4.0, h=1.0):
    prof = _line((14.0, 0.0), (r, 0.0)) + _line((r, 0.0), (r, h))
    prof += _line((r, h), (0.6, h)) + [(0.6, h)] if top else [(r, h)]
    return _revolve(prof)


def _run(mesh, floor_from=5.5):
    verts = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    W = np.asarray(mesh.area_faces, float)
    N = face_normals_smoothed(mesh)
    C = np.asarray(mesh.triangles_center, float)
    adj = np.asarray(mesh.face_adjacency)
    rad = np.hypot(C[:, 0], C[:, 1])
    floor = (rad > floor_from) & (C[:, 2] < 0.1)        # fitted, edge band trimmed off
    lab = np.where(floor, 0, -1).astype(np.int64)
    z0 = {"p95_mm": 0.0, "max_mm": 0.0, "rms_mm": 0.0}
    areas = [{"id": 0, "type": "flat", "kind": "plane", "_n": Z.copy(), "_d": 0.0,
              "_fmask": floor, "area_mm2": float(W[floor].sum()), "within_tol": True,
              "final": z0, "judged": z0, "snaps": []}]

    def accept(fm, a):
        lab[fm] = a["id"]
        areas.append(a)
    pool = lab < 0
    meta = find_capped_rings(verts, faces, C, N, W, adj, pool, lab, areas, axes=[Z],
                             nf=NOISE, tol=TOL, label_dist=max(3 * NOISE, TOL),
                             flat_lim=flat_off_limit(NOISE, TOL), cap=texture_limit(NOISE),
                             table="metric", rng=np.random.default_rng(0), accept=accept)
    return meta, areas, lab, C


def test_short_boss_capped_by_floor_and_top_is_a_round_with_a_top_flat():
    mesh = _boss(top=True)
    meta, areas, lab, C = _run(mesh)
    rings = [a for a in areas if a.get("capped_ring")]
    assert len(rings) == 1, meta["tried"]
    ring = rings[0]
    assert ring["kind"] == "boss"
    assert abs(ring["final"]["diameter_mm"] - 8.0) < 0.1, ring["final"]
    assert abs(abs(ring["final"]["axis"][2]) - 1.0) < 1e-9          # fixed to the part axis
    assert ring["round_check"]["coverage"] >= 0.75
    assert ring["round_check"]["length_mm"] < 2.0                    # short
    assert ring["area_mm2"] < 30.0                                   # under the minimum patch
    assert all(s >= 0.5 for s in ring["round_check"]["cap_share"])
    assert ring["within_tol"], ring["judged"]
    tops = [a for a in areas if a.get("ring_cap_of") == ring["id"]]
    assert tops, meta["tried"]
    top = max(tops, key=lambda a: a["area_mm2"])
    assert abs(abs(top["_n"] @ Z) - 1.0) < 1e-12                     # exactly the axis
    assert abs(abs(top["_d"]) - 1.0) < 0.05
    assert top["within_tol"], top["judged"]
    on_top = (np.hypot(C[:, 0], C[:, 1]) < 3.0) & (C[:, 2] > 0.9)
    assert np.mean(lab[on_top] == top["id"]) > 0.8


def test_ring_with_an_open_end_is_not_capped():
    mesh = _boss(top=False)
    meta, areas, lab, C = _run(mesh)
    assert not [a for a in areas if a.get("capped_ring")], meta["tried"]
    assert any("not capped" in t.get("why", "") for t in meta["tried"]), meta["tried"]
