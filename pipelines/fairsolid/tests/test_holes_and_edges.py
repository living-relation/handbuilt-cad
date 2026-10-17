"""Hole finder and edge bands (stage 30, second fit chunk).

Built with trimesh + manifold3d only, so these run in a second or two:

* a busy plate - 100 x 80 x 10 with a 6 x 5 grid of square pockets and
  three small through-holes - where the cylinder RANSAC has to draw three
  points from one small hole out of the whole part, and almost never does;
* a flat face with a strip standing off it along one border (the foot of
  a rib) and a bump in its middle: the strip is an edge band, the bump is
  form error and must stay.

Sizes are true millimetres; nothing is rescaled.
"""
import numpy as np
import pytest
import trimesh

from fairsolid.primitives import extract_holes
from fairsolid.stages.s30_fit import edge_bands, face_normals_smoothed

HOLES = {(-35.0, 25.0): 4.0, (35.0, 25.0): 6.0, (0.0, -30.0): 8.5}


@pytest.fixture(scope="module")
def busy_plate():
    plate = trimesh.creation.box(extents=(100.0, 80.0, 10.0))
    cut = []
    for (x, y), d in HOLES.items():
        c = trimesh.creation.cylinder(radius=d / 2, height=14.0, sections=96)
        c.apply_translation((x, y, 0.0))
        cut.append(c)
    for i in range(6):
        for j in range(5):
            p = trimesh.creation.box(extents=(5.0, 5.0, 6.0))
            p.apply_translation((-30.0 + 10.0 * i, -15.0 + 7.5 * j, 3.5))
            cut.append(p)
    part = trimesh.boolean.difference([plate] + cut, engine="manifold")
    part = part.subdivide_to_size(max_edge=1.0)
    rng = np.random.default_rng(5)
    part.vertices = part.vertices + rng.normal(0, 0.02, part.vertices.shape)
    return part


def test_small_holes_found_on_busy_part(busy_plate):
    m = busy_plate
    holes = extract_holes(m, [np.eye(3)[2], np.eye(3)[0], np.eye(3)[1]],
                          normals=face_normals_smoothed(m), max_rms=0.1)
    z = [h for h in holes if abs(abs(h.axis[2]) - 1) < 1e-9]
    for (x, y), d in HOLES.items():
        hit = [h for h in z if np.hypot(h.point[0] - x, h.point[1] - y) < 0.3]
        assert hit, f"d{d} hole at ({x}, {y}) not found: {[(h.point, 2 * h.radius) for h in z]}"
        assert abs(2 * hit[0].radius - d) < 0.1, (d, 2 * hit[0].radius)
    # square pockets are not holes, and nothing is found along X or Y
    assert len(z) == len(HOLES), [(np.round(h.point, 2), 2 * h.radius) for h in z]
    assert len(holes) == len(HOLES)


def test_edge_band_trimmed_but_interior_bump_kept():
    """Strip along the border: trimmed. Bump in the middle: stays and counts."""
    g = trimesh.creation.box(extents=(40.0, 40.0, 1.0)).subdivide_to_size(max_edge=0.5)
    v = g.vertices.copy()
    top = v[:, 2] > 0.4
    strip = top & (v[:, 0] > 18.0)                          # last 2 mm on +X
    bump = top & (np.hypot(v[:, 0], v[:, 1]) < 3.0)          # middle
    v[strip, 2] += 0.5
    v[bump, 2] += 0.5
    m = trimesh.Trimesh(v, g.faces, process=False)
    C = m.triangles_center
    fmask = (m.face_normals[:, 2] > 0.5) & (C[:, 2] > 0.3)
    res = C[:, 2] - 0.5                                      # distance to z = 0.5
    band = edge_bands(m, fmask, res, tol=0.2)
    in_strip = fmask & (C[:, 0] > 18.3)
    in_bump = fmask & (np.hypot(C[:, 0], C[:, 1]) < 2.5)
    assert band[in_strip].mean() > 0.9
    assert not band[in_bump].any()
    assert not band[fmask & (np.abs(res) <= 0.2)].any()     # on-surface faces never go
