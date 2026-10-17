"""F10: 0.3 x 45 deg edge break on convex edges of machined enclosure parts, excluding sealing faces
(body rim top + O-ring groove, lid underside contact face, HD34 sealing face) and edges shorter than 1 mm."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from build123d import *
import fxlib

def candidates(s, exclude_face):
    m = fxlib.edge_faces(s)
    from OCP.TopoDS import TopoDS
    out = []
    for e in s.edges():
        if e.length < 1.0: continue
        fl = [Face(TopoDS.Face(f) if hasattr(TopoDS,"Face") else f) for f in m.FindFromKey(e.wrapped)]
        if any(exclude_face(f) for f in fl): continue
        if fxlib.convexity(s, e, m) == 'convex': out.append(e)
    return out

def apply(s, exclude_face, d=0.3):
    ed = candidates(s, exclude_face)
    try:
        r = s.chamfer(d, None, ed); r, n = fxlib.one(r)
        if n == 1 and r.is_valid: return r, len(ed), 0
    except Exception: pass
    # greedy fallback in batches
    done, failed = 0, 0; cur = s
    for i in range(0, len(ed), 8):
        batch = [e for e in cur.edges() if any(e.is_same(x) or (abs((e.center() - x.center()).length) < 1e-4 and abs(e.length - x.length) < 1e-4) for x in ed[i:i + 8])]
        try:
            r = cur.chamfer(d, None, batch); r, n = fxlib.one(r)
            if n == 1 and r.is_valid: cur = r; done += len(batch); continue
        except Exception: pass
        failed += len(batch)
    return cur, done, failed
