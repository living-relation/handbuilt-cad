"""Freeform patches (stage 30, plan part 4): the first measuring step.

What flat and round fitting leave as "other" gets one stiff spline per
patch, scored with the same smoothed 95% check as every other area. The
stiffness is the plan's user setting. The default is PROPOSED, at the stiff
end: a fair simple surface, the way a machined part would be. The scan is
never perfect, and a patch that only passes by bending to the scan's bumps
is reported outside tolerance. Stiffness is not loosened to chase a pass.

Point grids at about the pedal scan's spacing, in true millimetres.
"""
import numpy as np

from fairsolid.stages.s30_fit import (
    SPLINE_STIFFNESS_PROPOSED, fit_spline_patch, freeform_charts,
    spline_degree, texture_limit,
)

NOISE = 0.092           # the pedal adapter's measured noise
TOL = 0.184             # 2 x noise, as the stage chose for it
CAP = texture_limit(NOISE)
SPACING = 0.5


def _grid(size=24.0):
    g = np.arange(-size / 2, size / 2 + 1e-9, SPACING)
    x, y = np.meshgrid(g, g)
    return x.ravel(), y.ravel()


def _texture(n, seed, base=0.06):
    return np.random.default_rng(seed).normal(0.0, base, n)


def test_proposed_stiffness_is_the_stiff_end():
    assert SPLINE_STIFFNESS_PROPOSED == 1.0
    assert spline_degree(SPLINE_STIFFNESS_PROPOSED) == 2      # 3 x 3 control points
    assert spline_degree(0.0) > spline_degree(1.0)


def test_smooth_curved_patch_with_texture_is_fitted_inside_tolerance():
    """A cast-like curve (R60 by R90 bowl) under scan texture passes."""
    x, y = _grid()
    z = x * x / (2 * 60.0) + y * y / (2 * 90.0) + _texture(len(x), 3)
    P = np.column_stack([x, y, z])
    fit = fit_spline_patch(P, np.ones(len(P)), tol=TOL, cap=CAP)
    assert fit is not None
    assert fit["degree"] == 2
    assert fit["within_tol"], fit["judged"]
    assert fit["judged"]["p95_mm"] <= TOL
    # The fit is the shape, not the texture: residual is about the noise.
    assert fit["final"]["rms_mm"] < 0.09


def test_sharp_crease_is_not_smoothed_into_passing():
    """A 30 degree crease under the same texture still fails.

    A stiff spline cannot turn a sharp corner. Smoothing in the pass check
    takes off texture, not a shape a millimetre wide, so the crease shows.
    """
    x, y = _grid()
    z = 0.27 * np.abs(x) + _texture(len(x), 4)          # ~30 deg between the sides
    P = np.column_stack([x, y, z])
    fit = fit_spline_patch(P, np.ones(len(P)), tol=TOL, cap=CAP)
    assert fit is not None
    assert not fit["within_tol"], fit["judged"]
    assert fit["judged"]["p95_mm"] > 2 * TOL


def test_stiff_patch_does_not_chase_waviness_to_pass():
    """Waviness 0.3 mm high and 8 mm long is not followed. The stiff fit
    misses and reports it, instead of bending to pass."""
    x, y = _grid()
    z = 0.3 * np.sin(2 * np.pi * x / 8.0) + _texture(len(x), 5, base=0.03)
    P = np.column_stack([x, y, z])
    fit = fit_spline_patch(P, np.ones(len(P)), tol=TOL, cap=CAP)
    assert fit is not None and fit["degree"] == 2
    assert not fit["within_tol"]


def test_charts_do_not_cross_a_crease():
    """Two flat sheets meeting at 90 degrees become two charts, not one."""
    import trimesh
    a = trimesh.creation.box(extents=[20.0, 20.0, 20.0])
    a = a.subdivide_to_size(max_edge=1.0)
    other = np.ones(len(a.faces), dtype=bool)
    charts, _ = freeform_charts(other, np.asarray(a.face_adjacency),
                                np.asarray(a.face_normals), np.asarray(a.area_faces),
                                min_patch=4.0)
    assert len(charts) == 6
    for c in charts:
        n = np.asarray(a.face_normals)[c]
        assert np.all(n @ n[0] > 0.99)
