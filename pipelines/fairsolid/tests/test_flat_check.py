"""Flat check (stage 30, fourth fit chunk).

A face joined a flat area whenever it lay within 3x noise of the plane
(0.54 mm on the cast pedal adapter) and faced roughly its way. A gentle
curve passes both tests over a strip several millimetres wide, so once the
round check sent the fake bosses back, their curved faces joined the
nearest plane, and a coarse curved patch became the worst "flat" of the
part (p95 0.66 mm). A flat now has to show that it is flat:

* per face, the scan AROUND it (averaged over FLAT_SMOOTH_MM, measured at
  the vertices) sits on the plane and faces its way - texture averages out,
  a curve does not;
* per area, its best second-order surface does not bend off a plane by
  more than the limit.

Plain arrays and small trimesh parts; true millimetres, nothing rescaled.
"""
import numpy as np
import trimesh

from fairsolid.stages.s30_fit import (
    FLAT_OFF_NOISE_FACTOR, face_normals_smoothed, flat_bend, flat_off_faces,
    flat_off_limit, local_mean,
)

Z = np.array([0.0, 0.0, 1.0])
LIMIT = 0.2


def _sheet(height, size=40.0, edge=0.5, noise=0.0, seed=0):
    """A square sheet z = height(x, y) centred on the origin, as a mesh."""
    g = trimesh.creation.box(extents=(size, size, 1.0)).subdivide_to_size(max_edge=edge)
    top = g.face_normals[:, 2] > 0.9
    g.update_faces(top)
    g.remove_unreferenced_vertices()
    v = g.vertices.copy()
    v[:, 2] = height(v[:, 0], v[:, 1])
    rng = np.random.default_rng(seed)
    v[:, 2] += rng.normal(0.0, noise, len(v))
    return trimesh.Trimesh(v, g.faces, process=False)


def _check(m, n=Z, d=0.0, limit=LIMIT):
    C = np.asarray(m.triangles_center)
    W = np.asarray(m.area_faces)
    mask = np.ones(len(C), dtype=bool)
    off = flat_off_faces(np.asarray(m.vertices), np.asarray(m.faces), C,
                         face_normals_smoothed(m), W, mask, n, d, limit=limit)
    return C, W, mask, off


def test_limit_is_noise_based_and_never_over_tolerance():
    assert flat_off_limit(0.02, 0.1) == FLAT_OFF_NOISE_FACTOR * 0.02
    assert flat_off_limit(0.18, 0.2) == 0.2


def test_local_mean_averages_noise_and_counts_itself():
    rng = np.random.default_rng(3)
    X = np.column_stack([rng.uniform(0, 20, 4000), rng.uniform(0, 20, 4000), np.zeros(4000)])
    v = rng.normal(0.0, 0.1, 4000)
    m = local_mean(X, np.ones(4000), v, 2.5)
    assert np.abs(m).max() < 0.06            # 0.1 mm noise averages out
    lone = local_mean(np.array([[0.0, 0, 0], [50.0, 0, 0]]), np.ones(2),
                      np.array([1.0, -1.0]), 2.5)
    assert np.allclose(lone, [1.0, -1.0])     # nothing in reach: own value


def test_noisy_flat_keeps_every_face():
    """Texture as rough as the tolerance still averages onto the plane."""
    m = _sheet(lambda x, y: 0.0 * x, noise=0.1, seed=1)
    C, W, mask, off = _check(m)
    assert W[off].sum() / W.sum() < 0.005, W[off].sum()
    assert flat_bend(np.asarray(m.vertices), np.asarray(m.faces), W, mask, Z)[
        "bend_p95_mm"] < 0.05


def test_curve_that_joined_the_plane_is_dropped():
    """Flat for x < 10, then rolling away as a 30 mm radius: within the old
    0.54 mm joining distance out to x = 15.7, but not a flat face there."""
    m = _sheet(lambda x, y: -np.where(x > 10.0, (x - 10.0) ** 2, 0.0) / 60.0,
               noise=0.03, seed=2)
    C, W, _, off = _check(m)
    joined = np.abs(C[:, 2]) <= 0.54                       # what used to join
    assert not off[joined & (C[:, 0] < 9.0)].any()          # the flat stays
    assert off[joined & (C[:, 0] > 14.5)].all()             # the curve goes
    assert off[C[:, 0] > 15.7].all()


def test_coarse_patch_is_judged_at_its_corners():
    """Big triangles whose corners zigzag +-0.45 mm: the centres sit within
    0.15 mm of the plane, the surface does not."""
    g = trimesh.creation.box(extents=(30.0, 30.0, 1.0)).subdivide_to_size(max_edge=5.0)
    g.update_faces(g.face_normals[:, 2] > 0.9)
    g.remove_unreferenced_vertices()
    v = g.vertices.copy()
    k = np.round(v[:, 0] / 3.75).astype(int) + np.round(v[:, 1] / 3.75).astype(int)
    v[:, 2] = np.where(k % 2 == 0, 0.45, -0.45)
    m = trimesh.Trimesh(v, g.faces, process=False)
    C, W, _, off = _check(m)
    assert np.abs(C[:, 2]).max() <= 0.16
    assert off.mean() > 0.9


def test_whole_area_bend_finds_a_shallow_trough_and_a_saddle():
    """Each face is within reach of the plane; the area as a whole is not flat."""
    trough = _sheet(lambda x, y: x ** 2 / 1000.0, noise=0.05, seed=4)   # 0.4 mm over 40
    saddle = _sheet(lambda x, y: (x ** 2 - y ** 2) / 1500.0, noise=0.05, seed=5)
    for m in (trough, saddle):
        W = np.asarray(m.area_faces)
        b = flat_bend(np.asarray(m.vertices), np.asarray(m.faces), W,
                      np.ones(len(W), dtype=bool), Z)
        assert b["bend_p95_mm"] > LIMIT, b
        assert min(r for r in b["radii_mm"] if r) < 1000.0, b
