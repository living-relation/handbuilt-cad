"""Capped section views: every cut is a closed solid with its cut face filled (a "cap"), never an open shell.

Rule (handbuilt-cad AGENTS.md "CAD and drawing rules", drawing/DRAWING-RULES.md): every rendered section view uses
closed-surface clipping. Clipping only the outer skin (an open cut, e.g. a VTK/pyvista clip of a surface mesh or a
renderer clipping plane) leaves the part looking like a hollow shell, which misreads wall thickness. So:

- B-rep (STEP / build123d): cut_capped() splits the solid with the plane (OCCT boolean). The result is a closed solid
  whose cut faces are real planar faces; it is checked closed and valid, and must have at least one cap face.
- Mesh (STL ...): clip_mesh_capped() uses a closed-surface clip that adds the cap polygons. Input must be a closed
  (watertight, manifold) mesh, the result is checked for open edges. An open mesh is refused, never rendered open.
- render_section() renders the kept half smooth-shaded (no mesh lines) with the caps in their own colour.

    .venv/bin/python tools/render/section.py part.step out.png --origin 0,0,10 --normal 0,0,1 [--view iso] [--keep below]
    .venv/bin/python tools/render/smooth_render.py part.step out.png --section 0,0,10/0,0,1     # same, via smooth_render

keep="below" keeps the side opposite the normal (the camera usually looks along the normal onto the cut face),
keep="above" keeps the side the normal points to.
"""
import argparse
import os
import sys

import numpy as np

CAP_COLOR = "#c8734f"
BODY_COLOR = "#9aa3ad"


class OpenSectionError(RuntimeError):
    """A section would render open (hollow-shell look): refused."""


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ValueError("section normal must not be zero")
    return v / n


# ---------------------------------------------------------------- B-rep
def _is_closed(shape):
    from OCP.BRep import BRep_Tool
    return all(BRep_Tool.IsClosed_s(sh.wrapped) for sh in shape.shells())


def cap_faces(shape, origin, normal, tol=1e-3):
    """Planar faces of shape that lie on the section plane (the caps)."""
    from build123d import GeomType
    o, n = np.asarray(origin, float), _unit(normal)
    out = []
    for f in shape.faces():
        if f.geom_type != GeomType.PLANE:
            continue
        fn = np.array(tuple(f.normal_at()))
        if abs(abs(fn @ n) - 1) < 1e-4 and abs((np.array(tuple(f.center())) - o) @ n) < tol:
            out.append(f)
    return out


def cut_capped(shape, origin, normal, keep="below"):
    """Split a solid (or compound of solids) with the plane; return the kept part as closed, capped solid(s).
    Raises OpenSectionError if the result is not closed/valid or the plane doesn't cut it (no cap face)."""
    from build123d import Keep, Plane
    if keep not in ("below", "above"):
        raise ValueError("keep must be 'below' or 'above'")
    if not shape.solids():
        raise OpenSectionError("no solid to cut: a shell or surface would section open. Make it a closed solid first")
    pl = Plane(origin=tuple(float(x) for x in origin), z_dir=tuple(float(x) for x in _unit(normal)))
    half = shape.split(pl, keep=Keep.BOTTOM if keep == "below" else Keep.TOP)
    if half is None or not half.solids():
        raise OpenSectionError("nothing left on the kept side of the section plane")
    for s in half.solids():
        if not s.is_valid or not _is_closed(s):
            raise OpenSectionError("cut result is not a closed valid solid (it would render as a hollow shell)")
    if not cap_faces(half, origin, normal):
        raise OpenSectionError("the plane does not cut the solid: no cap face on the section plane")
    return half


# ---------------------------------------------------------------- mesh
def open_edge_count(mesh):
    """Boundary (open) edges of a pyvista PolyData; 0 = closed surface."""
    fe = mesh.extract_feature_edges(boundary_edges=True, non_manifold_edges=False, feature_edges=False, manifold_edges=False)
    return int(fe.n_cells)


def clip_mesh_capped(mesh, origin, normal, keep="below"):
    """Closed-surface clip of a closed pyvista PolyData; the cut is capped. Refuses open input, checks the output."""
    import pyvista as pv
    m = mesh.extract_surface().triangulate().clean() if not isinstance(mesh, pv.PolyData) else mesh.triangulate().clean()
    if open_edge_count(m):
        raise OpenSectionError(f"mesh has {open_edge_count(m)} open edge(s): a clip would render open. "
                               "Section the STEP (cut_capped) or repair the mesh to a closed surface first")
    o, n = np.asarray(origin, float), _unit(normal)
    out = None
    for nn in (n, -n):                          # vtk keeps one side; take the call that keeps the requested side
        c = m.clip_closed_surface(normal=tuple(nn), origin=tuple(o))
        if c.n_points == 0:
            continue
        side = (np.asarray(c.center) - o) @ n
        if (side < 0) == (keep == "below"):
            out = c
            break
    if out is None:
        raise OpenSectionError("nothing left on the kept side of the section plane")
    out = out.triangulate().clean()
    if open_edge_count(out):
        raise OpenSectionError("clipped mesh is not closed (it would render as a hollow shell)")
    return out


# ---------------------------------------------------------------- render
def _tess(faces, tol=0.02, ang=0.2):
    import pyvista as pv
    parts = []
    for f in faces:
        vs, ts = f.tessellate(tol, ang)
        if not ts:
            continue
        parts.append(pv.PolyData(np.array([[p.X, p.Y, p.Z] for p in vs]), np.hstack([[3, *t] for t in ts])))
    if not parts:
        return None
    return parts[0].merge(parts[1:]) if len(parts) > 1 else parts[0]


def section_meshes(src, origin, normal, keep="below"):
    """(body mesh, cap mesh) of the capped section of a STEP/STL path or a build123d shape."""
    import pyvista as pv
    if isinstance(src, str) and src.lower().endswith((".stl", ".ply", ".obj", ".vtk")):
        m = clip_mesh_capped(pv.read(src), origin, normal, keep).compute_normals(cell_normals=True, point_normals=False)
        o, n = np.asarray(origin, float), _unit(normal)
        cn = m.cell_data["Normals"]
        on_plane = np.abs((m.cell_centers().points - o) @ n) < 1e-3
        is_cap = on_plane & (np.abs(cn @ n) > 0.9999)
        return (m.extract_cells(~is_cap).extract_surface(algorithm="dataset_surface"),
            m.extract_cells(is_cap).extract_surface(algorithm="dataset_surface"))
    if isinstance(src, str):
        from build123d import import_step
        src = import_step(src)
    half = cut_capped(src, origin, normal, keep)
    caps = cap_faces(half, origin, normal)
    body = [f for f in half.faces() if not any(f.is_same(c) for c in caps)]
    return _tess(body), _tess(caps)


def render_section(src, out, origin, normal, keep="below", view="iso", body_color=BODY_COLOR, cap_color=CAP_COLOR,
                   size=(1600, 1200)):
    """Smooth-shaded render of a capped section (no mesh lines); caps in cap_color. Returns out."""
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    import pyvista as pv
    body, cap = section_meshes(src, origin, normal, keep)
    if cap is None or cap.n_cells == 0:
        raise OpenSectionError("no cap faces to draw: refusing to render an open section")
    p = pv.Plotter(off_screen=True, window_size=size)
    p.set_background("white")
    if body is not None and body.n_cells:
        p.add_mesh(body.compute_normals(split_vertices=True, feature_angle=35), color=body_color, smooth_shading=True,
                   show_edges=False, specular=0.3)
    p.add_mesh(cap, color=cap_color, show_edges=False)
    {"iso": p.view_isometric, "top": p.view_xy, "front": p.view_xz, "right": p.view_yz}.get(view, p.view_isometric)()
    p.enable_parallel_projection()
    p.reset_camera()
    p.screenshot(out)
    p.close()
    return out


def parse_section(text):
    """'ox,oy,oz/nx,ny,nz' -> (origin, normal)."""
    try:
        o, n = text.split("/")
        return [float(x) for x in o.split(",")], [float(x) for x in n.split(",")]
    except Exception:
        raise ValueError(f"can't read section {text!r}: use 'ox,oy,oz/nx,ny,nz', e.g. 0,0,10/0,0,1")


def main(argv=None):
    a = argparse.ArgumentParser(description="Capped section render (closed-surface clipping, never open cut faces).")
    a.add_argument("src")
    a.add_argument("out")
    a.add_argument("--origin", required=True, help="point on the plane, e.g. 0,0,10")
    a.add_argument("--normal", required=True, help="plane normal, e.g. 0,0,1")
    a.add_argument("--keep", default="below", choices=["below", "above"])
    a.add_argument("--view", default="iso")
    g = a.parse_args(argv)
    o, n = parse_section(f"{g.origin}/{g.normal}")
    print(render_section(g.src, g.out, o, n, g.keep, g.view))


if __name__ == "__main__":
    sys.exit(main())
