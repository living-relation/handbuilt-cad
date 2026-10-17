"""Partial rounds (stage 30): fillets and part-bosses a machined part has.

The round check asks for 60% of a circle, so a rounded edge (a quarter
turn) or the side of a boss running into a flat was never a round - it was
left uncovered or fitted with a stiff spline. A strip between two fitted
flats that is a constant-radius arc tangent to both is now a fillet with a
standard radius; an arc on a part axis whose ends stop at fitted faces is a
partial round. A strip that only looks curved is still turned away.

Extruded profiles at about the pedal scan's spacing, true millimetres.
"""
import numpy as np
import trimesh

from fairsolid.stages.s30_fit import (
    _partial_pass, _radius_table, face_normals_smoothed, texture_limit,
)

NOISE = 0.092           # the pedal adapter's measured noise
TOL = 0.184             # 2 x noise, as the stage chose for it
STEP = 0.5
MIN_PATCH = 4.0
X, Y, Z = np.eye(3)


def _profile(segments):
    """Points (y, z) and a segment tag every STEP mm along line/arc segments.

    ('line', (y0, z0), (y1, z1)) or ('arc', (cy, cz), r, deg0, deg1)."""
    pts, tags = [], []
    for k, s in enumerate(segments):
        if s[0] == "line":
            p0, p1 = np.array(s[1], float), np.array(s[2], float)
            n = max(2, int(np.ceil(np.linalg.norm(p1 - p0) / STEP)))
            t = np.linspace(0, 1, n + 1)[:-1]
            pts += list(p0 + np.outer(t, p1 - p0))
        else:
            c, r, a0, a1 = np.array(s[1], float), s[2], np.radians(s[3]), np.radians(s[4])
            n = max(2, int(np.ceil(abs(a1 - a0) * r / STEP)))
            t = np.linspace(a0, a1, n + 1)[:-1]
            pts += list(c + r * np.column_stack([np.cos(t), np.sin(t)]))
        tags += [k] * (len(pts) - len(tags))
    last = segments[-1]
    if last[0] == "line":
        pts.append(np.array(last[2], float))
    else:
        c, r, a1 = np.array(last[1], float), last[2], np.radians(last[4])
        pts.append(c + r * np.array([np.cos(a1), np.sin(a1)]))
    tags.append(len(segments) - 1)
    return np.array(pts), np.array(tags)


def _extrude(segments, length=24.0, seed=0, texture=0.02, warp=None):
    """Mesh of the profile swept along X; face normal = X cross tangent."""
    prof, tags = _profile(segments)
    xs = np.arange(-length / 2, length / 2 + 1e-9, STEP)
    nP, nX = len(prof), len(xs)
    V = np.zeros((nP, nX, 3))
    V[:, :, 0] = xs[None, :]
    V[:, :, 1] = prof[:, 0, None]
    V[:, :, 2] = prof[:, 1, None]
    if warp is not None:
        V = warp(V, tags)
    V = V.reshape(-1, 3) + np.random.default_rng(seed).normal(0.0, texture, (nP * nX, 3))
    i, j = np.meshgrid(np.arange(nP - 1), np.arange(nX - 1), indexing="ij")
    a = (i * nX + j).ravel()
    b, c, d = a + 1, a + nX, a + nX + 1
    F = np.vstack([np.column_stack([a, b, c]), np.column_stack([b, d, c])])
    ftag = np.repeat(np.minimum(tags[:-1], tags[1:]), nX - 1)
    ftag = np.concatenate([ftag, ftag])
    # a face belongs to a segment only if both its profile ends do
    same = np.repeat(tags[:-1] == tags[1:], nX - 1)
    ftag = np.where(np.concatenate([same, same]), ftag, -1)
    return trimesh.Trimesh(vertices=V, faces=F, process=False), ftag


def _grid_faces(nr, nc, flip=False):
    i, j = np.meshgrid(np.arange(nr - 1), np.arange(nc - 1), indexing="ij")
    a = (i * nc + j).ravel()
    b, c, d = a + 1, a + nc, a + nc + 1
    F = np.vstack([np.column_stack([a, b, c]), np.column_stack([b, d, c])])
    return F[:, ::-1] if flip else F


def _flat(aid, fm, n, d, W):
    z = {"p95_mm": 0.0, "max_mm": 0.0, "rms_mm": 0.0}
    return {"id": aid, "type": "flat", "kind": "plane", "_n": np.asarray(n, float),
            "_d": float(d), "_fmask": fm, "area_mm2": float(W[fm].sum()),
            "within_tol": True, "final": z, "judged": z, "snaps": []}


def _run(mesh, flats):
    """flats: list of (face mask, normal, offset) already fitted. Runs the
    fillet and partial-round finder the split uses on everything else."""
    verts = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    W = np.asarray(mesh.area_faces, float)
    N = face_normals_smoothed(mesh)
    C = np.asarray(mesh.triangles_center, float)
    adj = np.asarray(mesh.face_adjacency)
    lab = np.full(len(faces), -1, dtype=np.int64)
    areas = []
    for fm, n, d in flats:
        lab[fm] = len(areas)
        areas.append(_flat(len(areas), fm, n, d, W))

    def accept(fm, a):
        lab[fm] = a["id"]
        areas.append(a)
    meta = _partial_pass(verts, faces, C, N, W, adj, lab < 0, lab, areas, nf=NOISE,
                         tol=TOL, cap=texture_limit(NOISE), label_dist=max(3 * NOISE, TOL),
                         min_patch=MIN_PATCH, directions=[X, Y, Z], table="metric",
                         rng=np.random.default_rng(0), accept=accept)
    return meta, areas, lab


def _corner(r=3.0):
    return [("line", (-12.0, 0.0), (0.0, 0.0)),
            ("arc", (0.0, -r), r, 90.0, 0.0),
            ("line", (r, -r), (r, -r - 12.0))]


def test_strip_between_square_flats_is_a_fillet_with_its_radius():
    mesh, tag = _extrude(_corner(3.0))
    C = np.asarray(mesh.triangles_center)
    top = (tag == 0) & (C[:, 1] < -1.0)          # edges trimmed off, as stage 30 does
    side = (tag == 2) & (C[:, 2] < -4.0)
    meta, areas, lab = _run(mesh, [(top, Z, 0.0), (side, Y, 3.0)])
    fil = [a for a in areas if a["kind"] == "fillet"]
    assert len(fil) == 1, [(a["type"], a["kind"]) for a in areas]
    f = fil[0]
    assert f["fillet"]["between_flats"] == [0, 1]
    assert f["fillet"]["convex"] and f["fillet"]["tangent_to_both"]
    assert abs(f["final"]["diameter_mm"] / 2 - 3.0) < 1e-9, f["final"]  # snapped to R3
    assert f["snaps"] and "radius" in f["snaps"][0]
    assert abs(abs(f["final"]["axis"][0]) - 1.0) < 1e-9          # along the edge
    assert f["within_tol"], f["judged"]
    arc = tag == 1
    assert np.mean(lab[arc] == f["id"]) > 0.9


def test_fillet_radius_snaps_only_to_the_table():
    t = _radius_table("metric")
    assert 3.0 in t and 0.5 in t and 12.0 in t
    assert np.all(np.diff(t) > 0)


def test_partial_boss_arc_bounded_by_flats_is_a_round():
    # A 60-degree arc of R8 (17% of the turn) rising 1.07 mm between two
    # lands, with a 30-degree crease at each end - the side of a boss.
    # The part's end faces (normal +-X) close it along the axis, as the top
    # and the floor of a real boss do.
    c = 8.0 * np.sin(np.radians(60.0))
    prof = [("line", (-12.0, 0.0), (-4.0, 0.0)),
            ("arc", (0.0, -c), 8.0, 120.0, 60.0),
            ("line", (4.0, 0.0), (12.0, 0.0))]
    body, tag = _extrude(prof, seed=2)
    caps = []
    for x0, sgn in ((-12.25, -1.0), (12.25, 1.0)):
        g = np.arange(-12.0, 12.0 + 1e-9, STEP)
        h = np.arange(-4.0, 1.0 + 1e-9, STEP)
        yy, zz = np.meshgrid(g, h)
        cap = trimesh.Trimesh(np.column_stack([np.full(yy.size, x0), yy.ravel(), zz.ravel()]),
                              _grid_faces(len(h), len(g), flip=sgn < 0), process=False)
        caps.append(cap)
    mesh = trimesh.util.concatenate([body] + caps)
    tag = np.concatenate([tag, np.full(len(mesh.faces) - len(tag), -2)])
    left, right = tag == 0, tag == 2
    meta, areas, lab = _run(mesh, [(left, Z, 0.0), (right, Z, 0.0)])
    rounds = [a for a in areas if a["type"] == "round"]
    assert len(rounds) == 1, [(a["type"], a["kind"]) for a in areas]
    b = rounds[0]
    assert b["kind"] == "boss" and b["partial"]
    assert b["round_check"]["coverage"] < 0.6
    assert abs(b["final"]["diameter_mm"] - 16.0) < 0.1, b["final"]
    assert abs(abs(b["final"]["axis"][0]) - 1.0) < 1e-9
    assert all(e is None or e >= 0.5 for e in b["round_check"]["end_share"])
    assert b["within_tol"]
    assert np.mean(lab[tag == 1] == b["id"]) > 0.8


def test_wavy_strip_between_flats_is_not_a_round():
    # Same corner, but the strip bulges in and out by 1 mm along the edge:
    # curved, not a constant radius.
    def warp(V, tags):
        on = tags == 1
        y, z = V[on, :, 1], V[on, :, 2] + 3.0
        th = np.arctan2(z, y)
        bump = 1.0 * np.sin(2 * np.pi * V[on, :, 0] / 8.0) * np.sin(2 * th)
        V[on, :, 1] = (3.0 + bump) * np.cos(th)
        V[on, :, 2] = (3.0 + bump) * np.sin(th) - 3.0
        return V
    mesh, tag = _extrude(_corner(3.0), warp=warp, seed=4)
    C = np.asarray(mesh.triangles_center)
    top = (tag == 0) & (C[:, 1] < -1.0)
    side = (tag == 2) & (C[:, 2] < -4.0)
    meta, areas, lab = _run(mesh, [(top, Z, 0.0), (side, Y, 3.0)])
    assert not [a for a in areas if a["type"] == "round"], \
        [(a["kind"], a.get("fillet"), a.get("round_check")) for a in areas if a["type"] == "round"]
    pm = meta
    assert pm["accepted"] == []
    # both were looked at and turned down, with the reason written down
    assert pm["fillets_tried"] and all("why" in t for t in pm["fillets_tried"])
    assert pm["partial_rounds_tried"] and all("why" in t for t in pm["partial_rounds_tried"])
