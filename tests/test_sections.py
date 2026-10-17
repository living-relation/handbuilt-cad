"""Capped sections only (closed-surface clipping): tools/render/section.py and the drawing engine's section_view."""
import os
import sys

import numpy as np
import pytest

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools", "render"))
sys.path.insert(0, os.path.join(HERE, "..", "drawing"))
import section as SEC  # noqa: E402
from build123d import Box, Cylinder, export_step, export_stl  # noqa: E402


def block():
    """40 x 30 x 20 block with a 10 mm through hole along Z: a hollow-looking section would show at once."""
    return Box(40, 30, 20) - Cylinder(5, 20)


def test_brep_cut_is_closed_and_capped():
    b = block()
    half = SEC.cut_capped(b, (0, 0, 0), (1, 0, 0))
    assert half.solids() and all(s.is_valid for s in half.solids())
    assert SEC._is_closed(half)
    assert half.volume == pytest.approx(b.volume / 2, rel=1e-6)
    caps = SEC.cap_faces(half, (0, 0, 0), (1, 0, 0))
    assert caps and sum(f.area for f in caps) == pytest.approx(30 * 20 - 10 * 20, rel=1e-6)   # wall material only


def test_keep_side():
    b = block()
    below = SEC.cut_capped(b, (10, 0, 0), (1, 0, 0), keep="below")
    above = SEC.cut_capped(b, (10, 0, 0), (1, 0, 0), keep="above")
    assert below.center().X < 10 < above.center().X
    assert below.volume + above.volume == pytest.approx(b.volume, rel=1e-6)


def test_plane_missing_the_part_is_refused():
    with pytest.raises(SEC.OpenSectionError):
        SEC.cut_capped(block(), (0, 0, 100), (0, 0, 1), keep="below")


def test_shell_input_is_refused():
    shell = block().faces()[0]
    from build123d import Compound
    with pytest.raises(SEC.OpenSectionError, match="closed solid"):
        SEC.cut_capped(Compound([shell]), (0, 0, 0), (1, 0, 0))


def test_mesh_clip_is_capped(tmp_path):
    import pyvista as pv
    stl = str(tmp_path / "b.stl")
    export_stl(block(), stl, tolerance=0.02)
    m = pv.read(stl).clean()
    assert SEC.open_edge_count(m) == 0
    c = SEC.clip_mesh_capped(m, (0, 0, 0), (1, 0, 0), keep="below")
    assert SEC.open_edge_count(c) == 0
    assert c.bounds[1] == pytest.approx(0, abs=1e-6)          # x max = the plane
    assert c.volume == pytest.approx(block().volume / 2, rel=0.02)
    body, cap = SEC.section_meshes(stl, (0, 0, 0), (1, 0, 0))
    assert cap.n_cells > 0 and cap.area == pytest.approx(30 * 20 - 10 * 20, rel=0.03)


def test_open_mesh_is_refused():
    import pyvista as pv
    open_box = pv.Box().triangulate().extract_cells(range(10)).extract_surface(algorithm="dataset_surface")    # 2 of 12 triangles missing
    assert SEC.open_edge_count(open_box) > 0
    with pytest.raises(SEC.OpenSectionError, match="open"):
        SEC.clip_mesh_capped(open_box, (0, 0, 0), (1, 0, 0))


def test_render_section_png(tmp_path):
    step = str(tmp_path / "b.step")
    export_step(block(), step)
    out = SEC.render_section(step, str(tmp_path / "sec.png"), (0, 0, 0), (0, 1, 0), size=(400, 300))
    from PIL import Image
    im = np.asarray(Image.open(out).convert("RGB")).astype(int)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    assert ((r > g + 30) & (r > b + 50)).sum() > 200              # the (orange) cap colour is on screen: the cut face is filled
    assert ((abs(r - b) < 25) & (r < 240)).sum() > 200            # and the grey body


def test_parse_section():
    assert SEC.parse_section("0,0,10/0,0,1") == ([0, 0, 10], [0, 0, 1])
    with pytest.raises(ValueError):
        SEC.parse_section("0,0,10")


def test_drawing_section_view_is_capped():
    import dwg
    v = dwg.section_view(block(), "front", (0, 0, 0), 1.0, "section")
    assert v.hatches, "section view must hatch a cap face"
    with pytest.raises(RuntimeError):
        dwg.section_view(block(), "front", (0, 500, 0), 1.0, "section")
