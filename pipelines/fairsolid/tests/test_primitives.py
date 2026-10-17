"""Regression tests: dimensional accuracy on a scan with known ground truth.

These assert on RECOVERED SIZE, not just recovered shape. A pipeline that
produces a beautifully shaped part at the wrong scale is the exact failure
this project exists to prevent, and only a dimensional assertion catches it.
"""
from pathlib import Path

import numpy as np
import pytest
import trimesh

from fairsolid.primitives import (
    extract_planes, extract_cylinders, noise_floor, dedupe_cylinders,
)
from fairsolid.stages.s20_frame import candidate_axes

DATA = Path(__file__).parent / "data"
CLEAN = Path(__file__).parent.parent / "work" / "clean.ply"


@pytest.fixture(scope="module")
def measured():
    mesh = trimesh.load(CLEAN, force="mesh")
    planes = extract_planes(mesh)
    cands = candidate_axes(planes)
    nf = noise_floor(planes)
    cyls = dedupe_cylinders(extract_cylinders(
        mesh, [c["axis"] for c in cands[:3]], max_rms=3 * nf))
    return planes, cands, cyls, nf


def test_noise_floor_matches_injected_noise(measured):
    """The estimator should recover the 0.04 mm sigma the fixture injected."""
    *_, nf = measured
    assert 0.02 < nf < 0.08, f"noise floor {nf:.4f} implausible"


def test_three_orthogonal_axes_recovered(measured):
    _, cands, _, _ = measured
    assert len(cands) >= 3
    a, b, c = (np.asarray(x["axis"]) for x in cands[:3])
    for u, v in ((a, b), (b, c), (a, c)):
        assert abs(float(np.dot(u, v))) < 0.02, "axes not orthogonal"


@pytest.mark.parametrize("nominal_d, tol", [(16.0, 0.05), (26.0, 0.05), (6.0, 0.05)])
def test_cylinder_diameters(measured, nominal_d, tol):
    _, _, cyls, _ = measured
    diams = [2 * c.radius for c in cyls]
    best = min(diams, key=lambda d: abs(d - nominal_d))
    assert abs(best - nominal_d) < tol, (
        f"nearest diameter to {nominal_d} was {best:.4f}; found {sorted(diams)}"
    )


def test_all_four_corner_holes_found(measured):
    """Guards max_per_axis: at 12 only one of the four was ever reached."""
    _, _, cyls, _ = measured
    corners = [c for c in cyls if abs(2 * c.radius - 6.0) < 0.1]
    assert len(corners) == 4, f"expected 4 corner holes, got {len(corners)}"


def test_plate_dimensions_from_plane_pairs(measured):
    """80 x 50 x 12 plate, recovered from antiparallel plane offsets."""
    planes, _, _, _ = measured
    got = []
    for i, a in enumerate(planes[:8]):
        for b in planes[i + 1:8]:
            if np.dot(a.normal, b.normal) < -0.995:
                got.append(a.offset + b.offset)
    for nominal in (80.0, 50.0, 12.0):
        best = min(got, key=lambda g: abs(g - nominal))
        assert abs(best - nominal) < 0.25, (
            f"no plane pair near {nominal}; got {sorted(round(g, 3) for g in got)}"
        )
