"""Scan noise measured on the clean flat faces, not on the capture band.

The plane finder keeps every point within 0.4 mm of a plane. On the cast
pedal adapter most of what it returns are chords across curves (points
spread evenly over the band) and even real faces carry the feet of their
neighbours, so the rms of the capture read 0.179 mm against faces that fit
to 0.06-0.09 mm. That number set the join distance, the round check, the
flat check and the default tolerance.

Plain arrays and small trimesh parts; true millimetres, nothing rescaled.
"""
import numpy as np
import trimesh

from fairsolid.primitives import NOISE_CORE_MIN, plane_noise
from fairsolid.stages.s30_fit import flat_off_limit, label_faces
from fairsolid.primitives import Cylinder

BAND = 0.4
Z = np.array([0.0, 0.0, 1.0])


def _flat(n, sigma, rng, size=40.0):
    xy = rng.uniform(-size / 2, size / 2, (n, 2))
    return np.column_stack([xy, rng.normal(0.0, sigma, n)])


def test_clean_face_reads_its_own_noise():
    rng = np.random.default_rng(0)
    ev = plane_noise(_flat(20_000, 0.05, rng), Z, 0.0, BAND)
    assert abs(ev["sigma"] - 0.05) < 0.005, ev
    assert ev["core"] >= NOISE_CORE_MIN


def test_neighbours_in_the_band_do_not_inflate_it():
    """A face plus 25% of points spread over the band (rib feet, edges)."""
    rng = np.random.default_rng(1)
    face = _flat(15_000, 0.05, rng)
    junk = _flat(5_000, 0.0, rng)
    junk[:, 2] = rng.uniform(-BAND, BAND, len(junk))
    pts = np.vstack([face, junk])
    plain = float(np.sqrt(np.mean(pts[:, 2] ** 2)))
    ev = plane_noise(pts, Z, 0.0, BAND)
    assert plain > 0.1                          # what the capture-band rms reads
    assert abs(ev["sigma"] - 0.05) < 0.01, ev   # what the face is
    assert ev["core"] >= NOISE_CORE_MIN


def test_chord_across_a_curve_is_not_a_face():
    """A cylinder r=20 cut by a plane: its points fill the band evenly."""
    rng = np.random.default_rng(2)
    t = rng.uniform(-0.5, 0.5, 20_000)
    y = rng.uniform(-20, 20, len(t))
    pts = np.column_stack([20 * np.sin(t), y, 20 * np.cos(t) - 19.8])
    ev = plane_noise(pts, Z, 0.0, BAND)
    assert ev["core"] < NOISE_CORE_MIN, ev


def test_flat_limit_follows_noise_inside_the_range():
    assert flat_off_limit(0.092, 0.184, floor=0.1) == 0.184    # pedal adapter
    assert flat_off_limit(0.011, 0.1, floor=0.1) == 0.1        # clean, large part
    assert flat_off_limit(0.03, 0.1, floor=0.02) == 0.06       # small part: 2 x noise
    assert flat_off_limit(0.011, 0.05, floor=0.1) == 0.05      # never over tolerance


def test_hole_joins_faces_by_its_own_scatter():
    """A rough d6 wall: the face-noise distance loses most of it."""
    m = trimesh.creation.cylinder(radius=3.0, height=6.0, sections=96)
    m = m.subdivide_to_size(max_edge=0.3)
    rng = np.random.default_rng(4)
    v = m.vertices.copy()
    side = np.abs(v[:, 2]) < 2.99
    r = np.linalg.norm(v[:, :2], axis=1)
    v[side, :2] *= ((r[side] + rng.normal(0, 0.12, side.sum())) / r[side])[:, None]
    m = trimesh.Trimesh(v, m.faces, process=False)
    hole = Cylinder(axis=[0.0, 0.0, 1.0], point=[0.0, 0.0, 0.0], radius=3.0,
                    n_points=100, rms=0.12)
    W = np.asarray(m.area_faces)
    lab_tight, _ = label_faces(m, [], [hole], label_dist=0.1, min_patch=1.0)
    lab_own, _ = label_faces(m, [], [hole], label_dist=0.1, min_patch=1.0,
                             own_dist={0: 0.36})
    assert W[lab_own == 0].sum() > 1.2 * W[lab_tight == 0].sum()
