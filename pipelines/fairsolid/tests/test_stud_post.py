"""Stud posts (stage 30 split).

The pedal adapter's three small studs (about 8.5 mm wide, 2 mm tall) have a
convincing round side wall, but a rounded foot, a rounded top edge and a
dimple in the top, so neither end is a flat square to the axis and the
capped-ring rule refuses them. the user wants them as clean round posts: a
plain cylinder with a snapped diameter and a flat top, the dimple ignored.
A dome with no wall, a tall shaft and an open tube are not studs.

Revolved profiles at about the pedal scan's spacing, true millimetres.
"""
import numpy as np
import trimesh

from fairsolid.stages.s30_fit import (
    face_normals_smoothed, find_capped_rings, find_stud_posts, flat_off_limit,
    texture_limit,
)

NOISE = 0.092
TOL = 0.184
Z = np.array([0.0, 0.0, 1.0])


def _revolve(profile, n_turn=120, seed=0, texture=0.02):
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


def _line(p0, p1, step=0.3):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    n = max(2, int(np.ceil(np.linalg.norm(p1 - p0) / step)))
    return list(p0 + np.outer(np.linspace(0, 1, n + 1)[:-1], p1 - p0))


def _arc(c, r, a0, a1, step=0.25):
    n = max(3, int(np.ceil(abs(a1 - a0) * r / step)))
    t = np.linspace(a0, a1, n + 1)[:-1]
    return list(np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)]))


def _stud(r=4.2, h=2.2, foot=0.6, edge=0.8, dimple=True, wall=True, dish=22.0):
    """Floor at z=0 with a shallow dish round the stud (like the pedal
    adapter's, leaning about 20 deg), rounded foot, wall, rounded top edge,
    flat top, dimple. Heights are from the bottom of the dish."""
    rd = r + foot + 3.0                      # dish starts here
    dz = np.tan(np.radians(dish)) * (rd - r - foot)
    prof = _line((16.0, dz), (rd, dz)) + _line((rd, dz), (r + foot, 0.0))
    prof += _arc((r + foot, foot), foot, -np.pi / 2, -np.pi)           # foot, concave
    if wall:
        prof += _line((r, foot), (r, h - edge))
    prof += _arc((r - edge, h - edge), edge, 0.0, np.pi / 2)           # top edge, convex
    if dimple:
        prof += _line((r - edge, h), (2.0, h)) + _line((2.0, h), (0.3, h - 0.9))
        prof += [(0.3, h - 0.9)]
    else:
        prof += _line((r - edge, h), (0.3, h)) + [(0.3, h)]
    m = _revolve(prof)
    m.vertices = np.asarray(m.vertices) - [0.0, 0.0, dz]       # outer floor at z=0
    return m, dz


def _run(mesh, floor_from=None):
    mesh, dz = mesh if isinstance(mesh, tuple) else (mesh, 0.0)
    verts = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    W = np.asarray(mesh.area_faces, float)
    N = face_normals_smoothed(mesh)
    C = np.asarray(mesh.triangles_center, float)
    adj = np.asarray(mesh.face_adjacency)
    rad = np.hypot(C[:, 0], C[:, 1])
    if floor_from is None:
        floor_from = 6.5 if dz == 0 else float(rad[C[:, 2] > -0.05].min()) + 0.5
    floor = (rad > floor_from) & (np.abs(C[:, 2]) < 0.1)
    lab = np.where(floor, 0, -1).astype(np.int64)
    z0 = {"p95_mm": 0.0, "max_mm": 0.0, "rms_mm": 0.0}
    areas = [{"id": 0, "type": "flat", "kind": "plane", "_n": Z.copy(), "_d": 0.0,
              "_fmask": floor, "area_mm2": float(W[floor].sum()), "within_tol": True,
              "final": z0, "judged": z0, "snaps": []}]

    def accept(fm, a):
        lab[fm] = a["id"]
        areas.append(a)
    pool = lab < 0
    kw = dict(nf=NOISE, tol=TOL, label_dist=max(3 * NOISE, TOL),
              flat_lim=flat_off_limit(NOISE, TOL), cap=texture_limit(NOISE), table="metric")
    rings = find_capped_rings(verts, faces, C, N, W, adj, pool, lab, areas, axes=[Z],
                              rng=np.random.default_rng(0), accept=accept, **kw)
    studs = find_stud_posts(verts, faces, C, N, W, adj, pool, lab, areas,
                            guides=rings["_guides"], accept=accept, **kw)
    return rings, studs, areas, lab, C


def test_domed_stud_with_a_dimple_is_a_clean_post_with_a_flat_top():
    rings, studs, areas, lab, C = _run(_stud())
    assert not [a for a in areas if a.get("capped_ring")], rings["tried"]   # caps refuse it
    posts = [a for a in areas if a.get("stud_post")]
    assert len(posts) == 1, studs["tried"]
    post = posts[0]
    assert post["kind"] == "boss" and post["type"] == "round"
    assert abs(abs(post["final"]["axis"][2]) - 1.0) < 1e-9                 # on the part axis
    d = post["final"]["diameter_mm"]
    assert abs(d / 0.5 - round(d / 0.5)) < 1e-9, d                          # snapped to 0.5 mm
    assert abs(d - 8.5) <= 0.5
    top = [a for a in areas if a.get("stud_top_of") == post["id"]]
    assert len(top) == 1
    top = top[0]
    assert abs(abs(top["_n"] @ Z) - 1.0) < 1e-12                           # exactly square
    h = abs(top["_d"])          # floor flat is at 0, the top 2.2 above the dish bottom
    assert abs(h / 0.1 - round(h / 0.1)) < 1e-6, h                          # height snapped
    assert top["within_tol"], top["judged"]
    dim = post["stud"]["dimple_ignored"]
    assert dim["area_mm2"] > 2.0 and dim["depth_mm"] > 0.5                  # reported, not fitted
    in_dimple = (np.hypot(C[:, 0], C[:, 1]) < 1.2)
    assert np.all(lab[in_dimple] < 0)                                       # left uncovered


def test_three_studs_of_nearly_one_size_share_one_snapped_diameter():
    from fairsolid.stages import s30_fit as f
    # one shared size from slightly different measured diameters
    sizes = []
    for r in (4.15, 4.25, 4.32):
        rings, studs, areas, lab, C = _run(_stud(r=r))
        sizes += [a["final"]["diameter_mm"] for a in areas if a.get("stud_post")]
    assert len(sizes) == 3
    assert all(abs(s / f.STUD_D_STEP["metric"] - round(s / f.STUD_D_STEP["metric"])) < 1e-9
               for s in sizes)


def test_dome_without_a_wall_is_not_a_stud():
    prof = [(14.0 - k * 0.3, 0.0) for k in range(int((14.0 - 6.0) / 0.3))]
    rr = np.linspace(6.0, 0.3, 40)
    prof += [(x, 2.0 * np.exp(-(x / 3.0) ** 2) - 2.0 * np.exp(-4.0)) for x in rr]
    rings, studs, areas, lab, C = _run(_revolve(prof))
    assert not [a for a in areas if a.get("stud_post")], studs["tried"]


def test_tall_shaft_is_not_a_stud():
    rings, studs, areas, lab, C = _run(_stud(r=2.0, h=9.0, foot=0.4, edge=0.4, dimple=False))
    assert not [a for a in areas if a.get("stud_post")], studs["tried"]


def test_open_tube_end_is_not_a_stud():
    prof = _line((14.0, 0.0), (4.6, 0.0)) + _arc((4.6, 0.6), 0.6, -np.pi / 2, -np.pi)
    prof += _line((4.0, 0.6), (4.0, 2.0)) + [(4.0, 2.0)]
    rings, studs, areas, lab, C = _run(_revolve(prof))
    assert not [a for a in areas if a.get("stud_post")], studs["tried"]
