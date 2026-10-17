"""Stage 80 - place the solid in world coordinates and write STEP.

The de-normalisation step. Everything upstream may have worked in a unit
cube; this stage applies the inverse of the stage-20 frame so the exported
STEP lands on the global planes, at true millimetres, with the origin on the
feature stage 20 chose.

Two export routes:

  build_faceted()   sews the aligned mesh into a genuine B-Rep solid. Always
                    succeeds, no feature tree, and the face count is whatever
                    you decimate to. This is the guaranteed path - it puts a
                    real solid body in Fusion or SOLIDWORKS today.

  place_solid()     takes a solid that a parametric stage already produced
                    (in unit-cube space) and moves it into world coordinates.

Run standalone:
    python -m fairsolid.stages.s80_export MESH FRAME OUT.step [--faces N]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh

from ..geom import Frame
from ..subproc import emit

# A sewn STEP carries one B-Rep face per triangle, so file size and CAD
# performance scale directly with this. 8k is small enough that SOLIDWORKS
# and Fusion stay responsive, and still holds ~0.1 mm of shape on a 100 mm
# part. Raise it for organic surfaces, lower it for simple prismatic ones.
DEFAULT_FACET_BUDGET = 8_000


def align_mesh(mesh: trimesh.Trimesh, frame: Frame) -> trimesh.Trimesh:
    """Move a scan-space mesh into canonical CAD coordinates, in real mm."""
    out = mesh.copy()
    out.vertices = frame.to_canonical(np.asarray(out.vertices, dtype=float))
    return out


def _decimate(mesh: trimesh.Trimesh, budget: int) -> trimesh.Trimesh:
    """Decimate while KEEPING the mesh watertight.

    Stage 10 already decimates with pymeshlab and `preservetopology=True`,
    which is why its output is a single watertight body. This used trimesh's
    `simplify_quadric_decimation` instead, and that offers no topological
    guarantee: taking the idealised knuckle from 200k to 8k faces turned one
    watertight body into 25 components - the part plus two dozen scraps of
    2-22 faces - and the main body stopped being watertight. Sewing that
    produced a solid which imported but failed isValid().

    Using the same decimator in both places fixes it at the source, rather
    than trying to heal the damage afterwards.
    """
    import pymeshlab

    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(
        vertex_matrix=np.asarray(mesh.vertices, dtype=float),
        face_matrix=np.asarray(mesh.faces, dtype=np.int32)))
    ms.apply_filter("meshing_decimation_quadric_edge_collapse",
                    targetfacenum=budget, preserveboundary=True,
                    preservenormal=True, preservetopology=True,
                    planarquadric=True, autoclean=True)
    # Drop any debris the collapse still leaves behind.
    ms.apply_filter("meshing_remove_connected_component_by_face_number",
                    mincomponentsize=max(50, budget // 100))
    m = ms.current_mesh()
    out = trimesh.Trimesh(m.vertex_matrix(), m.face_matrix(), process=False)
    if not out.is_watertight:
        out.fill_holes()
        out.remove_unreferenced_vertices()
    return out


def _sew_solid(mesh: trimesh.Trimesh, tol: float):
    """Sew triangles into an OCCT solid.

    Sewing rather than one loose face per triangle: shared edges get welded,
    so the result is a closed shell that CAD recognises as a solid body
    instead of a bag of surfaces that imports as a surface body.
    """
    from OCP.BRepBuilderAPI import (
        BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon,
        BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing,
    )
    from OCP.gp import gp_Pnt
    from OCP.TopoDS import TopoDS
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer

    sew = BRepBuilderAPI_Sewing(tol)
    verts = np.asarray(mesh.vertices, dtype=float)
    for tri in np.asarray(mesh.faces):
        a, b, c = (gp_Pnt(*verts[i]) for i in tri)
        poly = BRepBuilderAPI_MakePolygon(a, b, c, True)
        if not poly.IsDone():
            continue
        face = BRepBuilderAPI_MakeFace(poly.Wire())
        if face.IsDone():
            sew.Add(face.Face())
    sew.Perform()
    sewn = sew.SewedShape()

    # Collect EVERY shell, not just the first. A watertight mesh sews into one
    # shell and taking exp.Current() works; a mesh with any gap sews into many,
    # and the first one out of the explorer is usually a stray fragment. On a
    # real scan that produced a 20-face solid with a volume of 3 mm^3 in place
    # of a 200 mm casting - structurally valid, entirely wrong, and silent.
    shells = []
    exp = TopExp_Explorer(sewn, TopAbs_SHELL)
    while exp.More():
        shells.append(TopoDS.Shell_s(exp.Current()))
        exp.Next()
    if not shells:
        return sewn, False, 0

    def face_count(shape) -> int:
        n, fe = 0, TopExp_Explorer(shape, TopAbs_FACE)
        while fe.More():
            n += 1
            fe.Next()
        return n

    shells.sort(key=face_count, reverse=True)
    solid = BRepBuilderAPI_MakeSolid(shells[0])
    if not solid.IsDone():
        return sewn, False, len(shells)
    return _heal(solid.Solid()), True, len(shells)


def _heal(shape):
    """Run OCCT Shape Healing over a sewn solid.

    Sewing a decimated scan leaves small gaps, sliver faces and
    self-intersecting wires. ShapeFix is OCCT's toolkit for exactly this: it
    repairs wires, fills gaps between patches and drops degenerate edges, which
    is what turns a shape that merely imports into one that passes isValid()
    and that CAD will accept without complaint.

    Healing is best-effort - if it cannot converge the original shape is
    returned rather than nothing, and the caller reports validity either way.
    """
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.ShapeFix import ShapeFix_Shape

    try:
        fixer = ShapeFix_Shape(shape)
        fixer.SetPrecision(1e-4)
        fixer.SetMaxTolerance(1e-2)
        fixer.Perform()
        fixed = fixer.Shape()
    except Exception:
        return shape
    if fixed is None or fixed.IsNull():
        return shape
    # Only accept the repair if it actually improved matters.
    if (not BRepCheck_Analyzer(shape).IsValid()
            and BRepCheck_Analyzer(fixed).IsValid()):
        return fixed
    return fixed if BRepCheck_Analyzer(fixed).IsValid() else shape


def build_faceted(
    mesh_path: Path,
    frame_path: Path,
    out_step: Path,
    *,
    face_budget: int = DEFAULT_FACET_BUDGET,
) -> dict:
    """Aligned, true-scale, sewn B-Rep STEP. The always-works path."""
    import cadquery as cq

    frame = Frame.load(frame_path)
    mesh = trimesh.load(mesh_path, force="mesh", process=False)
    aligned = align_mesh(mesh, frame)

    faces_before = len(aligned.faces)
    if faces_before > face_budget:
        aligned = _decimate(aligned, face_budget)

    # Sewing tolerance keyed to the mesh's own edge length: too tight and
    # shared edges fail to weld (surface body, not solid); too loose and
    # genuinely distinct features get merged.
    edge = float(np.median(aligned.edges_unique_length))
    shape, is_solid, n_shells = _sew_solid(aligned, tol=edge * 0.25)

    out_step.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(cq.Workplane(obj=cq.Shape.cast(shape)), str(out_step))

    extents = (aligned.bounds[1] - aligned.bounds[0]).astype(float)
    # Sanity gate. Sewing can succeed structurally while producing a fragment,
    # and a "valid solid" that is 1% of the part is worse than a loud failure.
    from OCP.BRepCheck import BRepCheck_Analyzer
    is_valid = bool(BRepCheck_Analyzer(shape).IsValid())
    bb = cq.Shape.cast(shape).BoundingBox()
    got = np.array([bb.xlen, bb.ylen, bb.zlen])
    size_ratio = float(np.min(got / np.maximum(extents, 1e-9)))
    return {
        "step": str(out_step),
        "is_solid": bool(is_solid),
        "is_valid": is_valid,
        "n_shells": n_shells,
        "faces_before": faces_before,
        "faces_exported": int(len(aligned.faces)),
        "sew_tolerance": edge * 0.25,
        "extents_mm": extents.tolist(),
        "watertight": bool(aligned.is_watertight),
        "size_ratio": size_ratio,
        "fragment_warning": size_ratio < 0.5,
        "bytes": out_step.stat().st_size if out_step.exists() else 0,
    }


def place_solid(solid, frame: Frame):
    """Move a unit-cube-space CadQuery solid into world mm.

    This is the inverse no published scan-to-CAD model performs. Applied as a
    single transform on the B-Rep rather than per-vertex, so exact analytic
    surfaces stay exact.
    """
    import cadquery as cq

    wp = cq.Workplane(obj=solid) if not isinstance(solid, cq.Workplane) else solid
    # Undo normalisation only. The frame rotation is intentionally NOT undone:
    # the deliverable should sit on the global planes, not back at the
    # scanner's arbitrary pose.
    return (wp.val()
            .scale(1.0 / frame.scale)
            .translate(cq.Vector(*frame.centre)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mesh", type=Path)
    ap.add_argument("frame", type=Path)
    ap.add_argument("out_step", type=Path)
    ap.add_argument("--faces", type=int, default=DEFAULT_FACET_BUDGET)
    a = ap.parse_args()
    emit(build_faceted(a.mesh, a.frame, a.out_step, face_budget=a.faces))


if __name__ == "__main__":
    main()
