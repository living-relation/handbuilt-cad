"""Pass check (stage 30, sixth fit chunk): judge the smooth shape.

On the cast pedal adapter ten flats had rms 0.10-0.12 mm - the shape is
right - and still missed the 0.184 mm tolerance at the 95th percentile, on
scan texture peaks alone. the user's models are smooth solids that never carry
the texture, so the 95% rule now compares distances smoothed over each
area's own points (PASS_SMOOTH_MM). Smoothing may take off at most the
texture limit (3x noise) at any point; anything taller is a real feature
and keeps its raw distance. Anything wider than the smoothing reach is shape
and is not smoothed away: a bowed face and a D-shaped hole still fail.

Point grids at about the pedal scan's spacing; true millimetres, nothing
rescaled. Every case is fitted first (plane / cylinder least squares), then
judged, the way the stage does it.
"""
import numpy as np
import pytest

from fairsolid.primitives import refine_plane
from fairsolid.stages.s30_fit import (
    PASS_SMOOTH_MM, ROUND_ARC_SQUEEZE, cyl_residual, fit_cylinder, pass_check,
    pass_coords, plane_residual, texture_limit,
)

NOISE = 0.092           # the pedal adapter's measured noise
TOL = 0.184             # 2 x noise, as the stage chose for it
CAP = texture_limit(NOISE)
SPACING = 0.5           # mm between scan points (pedal: ~0.6 mm edges)


def _grid(size=30.0):
    g = np.arange(-size / 2, size / 2 + 1e-9, SPACING)
    x, y = np.meshgrid(g, g)
    return x.ravel(), y.ravel()


def _texture(n, seed, base=0.06, peak=0.0, frac=0.0):
    """Fine scan texture: base noise plus isolated one-point peaks."""
    rng = np.random.default_rng(seed)
    z = rng.normal(0.0, base, n)
    hit = rng.random(n) < frac
    z[hit] += peak * rng.choice([-1.0, 1.0], hit.sum())
    return z, hit


def _judge_flat(z_shape, z_tex, x, y):
    P = np.column_stack([x, y, z_shape + z_tex])
    n, d, _ = refine_plane(P)
    res = plane_residual(P, n, d)
    pc = pass_check(P, np.ones(len(P)), res, tol=TOL, radius=PASS_SMOOTH_MM, cap=CAP)
    raw_p95 = float(np.percentile(np.abs(res), 95))
    return pc["stats"], raw_p95


def _hole(d=4.0, length=6.0, flat_depth=0.0):
    """Points on a hole wall along Z; flat_depth > 0 cuts a D flat into it."""
    r = d / 2
    nt = int(round(np.pi * d / SPACING))
    t, z = np.meshgrid(np.linspace(0, 2 * np.pi, nt, endpoint=False),
                       np.arange(0, length + 1e-9, SPACING))
    t, z = t.ravel(), z.ravel()
    x, y = r * np.cos(t), r * np.sin(t)
    if flat_depth:
        cut = x > r - flat_depth                  # the wall steps in to a flat
        x = np.where(cut, r - flat_depth, x)
    return np.column_stack([x, y, z]), t


def _judge_hole(P, seed, tex_kw):
    tex, _ = _texture(len(P), seed, **tex_kw)
    rad = P[:, :2] / np.linalg.norm(P[:, :2], axis=1)[:, None]
    P = P + np.column_stack([rad * tex[:, None], np.zeros(len(P))])
    ax, p, r = fit_cylinder(P, np.array([0.0, 0, 1]), np.zeros(3), 2.0)
    res = cyl_residual(P, ax, p, r)
    pc = pass_check(P, np.ones(len(P)), res, tol=TOL, cap=CAP, axis=ax, point=p)
    return pc["stats"], float(np.percentile(np.abs(res), 95)), 2 * r


PEAKS = dict(base=0.06, peak=0.25, frac=0.10)     # peaks under the 0.276 limit


def test_limit_and_reach():
    """3x noise; on a round the reach runs along the axis, not around."""
    assert CAP == pytest.approx(3 * NOISE)
    P = np.array([[2.0, 0, 0], [2.0, 0, 0.9], [2.0 * np.cos(0.2), 2.0 * np.sin(0.2), 0]])
    X = pass_coords(P, np.array([0.0, 0, 1]), np.zeros(3))
    assert np.linalg.norm(X[1] - X[0]) == pytest.approx(0.9)          # along: in reach
    assert np.linalg.norm(X[2] - X[0]) > PASS_SMOOTH_MM               # 0.4 mm around: not
    assert np.allclose(pass_coords(P), P)                              # flats untouched


def test_flat_with_texture_peaks_under_the_limit_passes():
    """Raw, the peaks fail the 95% rule; the smooth face is inside it."""
    x, y = _grid()
    tex, _ = _texture(len(x), 1, **PEAKS)
    st, raw = _judge_flat(0.0 * x, tex, x, y)
    assert raw > TOL, raw                     # the old test failed this face
    assert st["within_tol"] and st["p95_mm"] <= TOL, st
    assert st["raw_kept_frac"] < 0.05, st     # only the odd peak+noise pile-up


def test_truly_bowed_flat_still_fails():
    """A 0.5 mm bow over 30 mm with the same texture: shape, not texture."""
    x, y = _grid()
    tex, _ = _texture(len(x), 2, **PEAKS)
    st, raw = _judge_flat(0.5 * (x / 15.0) ** 2, tex, x, y)
    assert not st["within_tol"] and st["p95_mm"] > TOL, st


def test_peaks_taller_than_the_limit_are_not_texture():
    """Isolated 0.5 mm spikes stand more than 3x noise off their
    surroundings: they keep their raw distance and the face fails."""
    x, y = _grid()
    tex, hit = _texture(len(x), 3, base=0.06, peak=0.5, frac=0.08)
    st, raw = _judge_flat(0.0 * x, tex, x, y)
    assert not st["within_tol"], st
    assert st["raw_kept_frac"] >= 0.07, st


def test_narrow_ridges_still_fail():
    """1.5 mm wide, 0.6 mm tall ridges on 10% of a face are a feature."""
    x, y = _grid()
    tex, _ = _texture(len(x), 4)
    ridge = np.where(np.abs(((x + 15.0) % 15.0) - 7.5) < 0.75, 0.6, 0.0)
    assert 0.08 < (ridge > 0).mean() < 0.12
    st, raw = _judge_flat(ridge, tex, x, y)
    assert not st["within_tol"], st


def test_round_hole_with_texture_passes():
    st, raw, d = _judge_hole(_hole()[0], 5, PEAKS)
    assert raw > TOL, raw
    assert st["within_tol"], st
    assert d == pytest.approx(4.0, abs=0.05)


def test_d_shaped_hole_still_fails():
    """A d4 hole with a 0.5 mm D flat (~80 deg of the wall), same texture.
    The flat is far wider than the smoothing reach, so the judged p95 is the
    D's own shape error - which is over the tolerance - and the hole fails."""
    P, _ = _hole(flat_depth=0.5)
    ax, p, r = fit_cylinder(P, np.array([0.0, 0, 1]), np.zeros(3), 2.0)
    shape_p95 = float(np.percentile(np.abs(cyl_residual(P, ax, p, r)), 95))
    assert shape_p95 > TOL                       # the D itself is out
    st, raw, d = _judge_hole(P, 6, PEAKS)
    assert not st["within_tol"] and st["p95_mm"] > TOL, st
    assert st["p95_mm"] >= shape_p95 - 0.03       # never smoothed below the D


def test_smoothing_never_hides_shape():
    """With no texture at all, judged and raw p95 agree on a D and a bow."""
    P, _ = _hole(flat_depth=0.5)
    ax, p, r = fit_cylinder(P, np.array([0.0, 0, 1]), np.zeros(3), 2.0)
    res = cyl_residual(P, ax, p, r)
    st = pass_check(P, np.ones(len(P)), res, tol=TOL, cap=CAP, axis=ax, point=p)["stats"]
    assert st["p95_mm"] == pytest.approx(np.percentile(np.abs(res), 95), abs=0.02)
    x, y = _grid()
    st, raw = _judge_flat(0.5 * (x / 15.0) ** 2, 0.0 * x, x, y)
    assert st["p95_mm"] == pytest.approx(raw, abs=0.02)
