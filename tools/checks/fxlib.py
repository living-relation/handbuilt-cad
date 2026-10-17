"""Shared helpers for the 2026-10-16 scratch fixes (build123d / OCP)."""
import math
from build123d import *

def stadium_cut(cx0, cx1, y, r, z0, z1):
    """Through slot along X: centres cx0..cx1 at y, radius r, z0..z1."""
    p = Plane(origin=(0, 0, z0))
    L = cx1 - cx0
    with BuildPart() as bp:
        with BuildSketch(p):
            with Locations(((cx0 + cx1) / 2, y)):
                SlotOverall(L + 2 * r, 2 * r)
        extrude(amount=z1 - z0)
    return bp.part.solids()[0]

def edge_faces(sol):
    from OCP.TopExp import TopExp
    from OCP.collections import IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    m = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(sol.wrapped, TopAbs_EDGE, TopAbs_FACE, m)
    return m

def convexity(sol, e, m, eps=0.02):
    """'concave' = inside corner, 'convex' = outside edge, None if undecidable (seam / tangent)."""
    from OCP.TopoDS import TopoDS
    fl = [Face(TopoDS.Face(f) if hasattr(TopoDS,"Face") else f) for f in m.FindFromKey(e.wrapped)]
    if len(fl) < 2: return None
    p = e.position_at(0.5)
    try: n1 = fl[0].normal_at(p); n2 = fl[1].normal_at(p)
    except Exception: return None
    if (n1 - n2).length < 0.05: return None
    a = sol.is_inside(p + (n1 - n2) * eps); b = sol.is_inside(p + (n2 - n1) * eps)
    if a and b: return 'concave'
    if not a and not b: return 'convex'
    return None

def one(shape):
    s = shape.solids()
    s = sorted(s, key=lambda x: -x.volume)
    assert len(s) >= 1
    return s[0], len(s)

def fuzzy_cut(sol, tools, fuzz=1e-4):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.collections import List_TopoDS_Shape as TopTools_ListOfShape
    a = TopTools_ListOfShape(); a.Append(sol.wrapped)
    t = TopTools_ListOfShape()
    for x in tools: t.Append(x.wrapped)
    op = BRepAlgoAPI_Cut(); op.SetArguments(a); op.SetTools(t); op.SetFuzzyValue(fuzz); op.SetRunParallel(True); op.Build()
    assert op.IsDone()
    r = Compound(op.Shape())
    ss = r.solids()
    return ss[0] if len(ss) == 1 else r

def fix_shape(sol):
    from OCP.ShapeFix import ShapeFix_Shape
    f = ShapeFix_Shape(sol.wrapped); f.Perform()
    ss = Compound(f.Shape()).solids()
    return ss[0] if len(ss) == 1 else Compound(ss)
