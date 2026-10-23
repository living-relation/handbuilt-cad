"""Round check (stage 30, third fit chunk).

The old circle search kept any circle whose band held points over 55% of
the turn, whichever way those points faced and at whatever height along the
part. On the cast pedal adapter that turned cast texture and freeform
curves into "bosses" of d84, d101, d124 and d243 mm - the worst area of the
part was one of them. A round from the circle search now has to show the
same evidence the hole finder asks of a hole: faces that lie on the circle
AND face along its radius, covering at least 60% of the turn, fitting
within 3x the noise.

These are plain arrays and small trimesh parts, so they run in a second.
Sizes are true millimetres; nothing is rescaled.
"""
import numpy as np
import trimesh

from fairsolid.stages.s30_fit import (
    ROUND_MIN_COVERAGE, face_normals_smoothed, round_check, round_evidence,
)

Z = np.array([0.0, 0.0, 1.0])
NF = 0.02


def _ring(r, start_deg, span_deg, n=720, noise=0.0, facing="out", seed=0):
    """Face centres, normals and areas on an arc of a circle about Z."""
    rng = np.random.default_rng(seed)
    t = np.radians(start_deg + span_deg * (np.arange(n) + 0.5) / n)
    z = rng.uniform(-5.0, 5.0, n)
    rad = np.column_stack([np.cos(t), np.sin(t), np.zeros(n)])
    C = (r + rng.normal(0.0, noise, n))[:, None] * rad + z[:, None] * Z
    if facing == "out":
        N = rad
    elif facing == "in":
        N = -rad
    else:                                   # along the circle, not across it
        N = np.column_stack([-np.sin(t), np.cos(t), np.zeros(n)])
    return C, N, np.full(n, 0.1)


def test_real_boss_mesh_passes():
    boss = trimesh.creation.cylinder(radius=15.0, height=20.0, sections=128)
    boss = boss.subdivide_to_size(max_edge=1.0)
    rng = np.random.default_rng(1)
    boss.vertices = boss.vertices + rng.normal(0.0, NF, boss.vertices.shape)
    C = np.asarray(boss.triangles_center)
    ev = round_evidence(C, face_normals_smoothed(boss), np.asarray(boss.area_faces),
                        Z, [0.0, 0.0, 0.0], 15.0, band=0.4)
    assert ev["side"] == "outward"
    assert ev["coverage"] >= 0.95, ev
    assert round_check(ev, NF) is None


def test_hole_side_is_measured_too():
    ev = round_evidence(*_ring(3.0, 0, 360, facing="in"), Z, [0, 0, 0], 3.0, band=0.4)
    assert ev["side"] == "inward" and ev["coverage"] == 1.0
    assert round_check(ev, NF) is None


def test_short_arc_of_a_big_radius_is_not_a_boss():
    """Area 27 on the pedal adapter: a 20-degree sliver read as a d84 boss."""
    ev = round_evidence(*_ring(42.0, 80, 20), Z, [0, 0, 0], 42.0, band=0.4)
    assert ev["coverage"] < ROUND_MIN_COVERAGE
    assert "of the turn" in round_check(ev, NF)


def test_points_in_the_band_must_face_along_the_radius():
    """Faces that only cross the circle (ribs, texture) do not add up to one."""
    ev = round_evidence(*_ring(30.0, 0, 360, facing="along"), Z, [0, 0, 0], 30.0, band=0.4)
    assert ev["coverage"] == 0.0 and ev["rms_mm"] is None
    assert "faces along its radius" in round_check(ev, NF)


def test_scattered_arcs_on_one_side_count_but_need_the_coverage():
    """Two separate 90-degree arcs make 50% - short of a convincing round."""
    a = _ring(25.0, 0, 90, seed=1)
    b = _ring(25.0, 180, 90, seed=2)
    C, N, W = (np.vstack([x, y]) if x.ndim == 2 else np.concatenate([x, y])
               for x, y in zip(a, b))
    ev = round_evidence(C, N, W, Z, [0, 0, 0], 25.0, band=0.4)
    assert abs(ev["coverage"] - 0.5) < 0.03
    assert round_check(ev, NF) is not None


def test_full_turn_that_does_not_fit_is_rejected():
    ev = round_evidence(*_ring(20.0, 0, 360, noise=0.2), Z, [0, 0, 0], 20.0, band=0.8)
    assert ev["coverage"] == 1.0
    assert "noise" in round_check(ev, NF)
    assert round_check(ev, 0.2) is None          # same arc at 0.2 mm noise is fine


def test_mask_limits_the_faces():
    C, N, W = _ring(10.0, 0, 360)
    half = np.arctan2(C[:, 1], C[:, 0]) > 0
    ev = round_evidence(C, N, W, Z, [0, 0, 0], 10.0, band=np.inf, mask=half)
    assert abs(ev["coverage"] - 0.5) < 0.03
