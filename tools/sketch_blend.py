"""Generic helpers for clean CNC sketch bodies (build123d). Reusable; no knuckle specifics.
  capsule(c1, r1, c2, r2)        tapered arm outline: two circles + their outer tangent lines (true lines + arcs)
  round_outline(face, rin, rout) close then open the outer wire with arc offsets -> concave corners >= rin, convex >= rout
  plan_union(faces, rin, rout)   union of plan faces -> one rounded outline face
  poly_face(pts, rin, rout)      polygon (e.g. a simplified scan outline) -> rounded outline face
  prism(face, z0, z1)            Z extrusion of a plan face
  skirt(face, z0, r, support)    swept concave blend ring (quarter-round fillet material) where a prism with plan `face`
                                 stands on a flat seat at z0; clipped to `support` (the seat's plan face) so nothing dangles
  strict_fuse / strict_cut       joins that fail loudly (one valid solid, plausible volume) instead of silently skipping
"""
import math
from build123d import *

class JoinError(RuntimeError): pass

def _one(s):
    if isinstance(s, Solid): return s
    ss = s.solids(); return ss[0] if len(ss) == 1 else s

def strict_fuse(a, b, name):
    for tol in (None, 0.01, 0.05):
        try:
            r = _one(a.fuse(b) if tol is None else a.fuse(b, tol=tol))
            if isinstance(r, Solid) and r.is_valid and r.volume >= max(a.volume, b.volume) - 1 and r.volume <= a.volume + b.volume + 1:
                return r
        except Exception: pass
    raise JoinError("join failed: " + name)

def strict_cut(a, b, name, crumbs=20.0, log=print):
    for tol in (None, 0.01, 0.05):
        try:
            if tol is None: r = a.cut(b)
            else:
                from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
                op = BRepAlgoAPI_Cut(); op.SetFuzzyValue(tol); r = a._bool_op((a,), (b,), op)
            ss = sorted(r.solids(), key=lambda x: -x.volume)
            if not ss or not all(x.is_valid for x in ss): continue
            rest = sum(x.volume for x in ss[1:])
            if rest > 0: log("  %s: %d crumbs %.1f mm3" % (name, len(ss) - 1, rest))
            if rest < crumbs and ss[0].volume <= a.volume + 1: return ss[0]
        except Exception as ex: log("  %s exception %s" % (name, ex))
    raise JoinError("cut failed: " + name)

def _circle_face(c, r): return Face(Wire.make_circle(r, Plane(origin=(c[0], c[1], 0))))

def capsule(c1, r1, c2, r2):
    (x1, y1), (x2, y2) = c1, c2; dx, dy = x2 - x1, y2 - y1; d = math.hypot(dx, dy)
    if d <= abs(r1 - r2) + 1e-6: return _circle_face(c1 if r1 > r2 else c2, max(r1, r2))
    ux, uy = dx / d, dy / d; s = (r1 - r2) / d; h = math.sqrt(max(0.0, 1 - s * s)); pts = []
    for sg in (1, -1):
        nx, ny = s * ux - sg * h * uy, s * uy + sg * h * ux      # outward normal of the tangent line
        pts.append(((x1 + r1 * nx, y1 + r1 * ny), (x2 + r2 * nx, y2 + r2 * ny)))
    (a1, a2), (b1, b2) = pts
    far2 = (x2 + r2 * ux, y2 + r2 * uy); far1 = (x1 - r1 * ux, y1 - r1 * uy)
    V = lambda p: Vector(p[0], p[1], 0)
    w = Wire([Edge.make_line(V(a1), V(a2)), Edge.make_three_point_arc(V(a2), V(far2), V(b2)),
              Edge.make_line(V(b2), V(b1)), Edge.make_three_point_arc(V(b1), V(far1), V(a1))])
    return Face(w)

def round_outline(face, rin=10.0, rout=4.0):
    w0 = face.outer_wire(); a0 = face.area
    for ri, ro in ((rin, rout), (rin, rout / 2), (rin * 0.75, rout / 2), (rin / 2, rout / 4)):
        try:
            w = w0
            for d in ([ri, -ri] if ri else []) + ([-ro, ro] if ro else []): w = w.offset_2d(d, kind=Kind.ARC)
            f = Face(w)
            if abs(f.area - a0) < 0.15 * a0: return f
        except Exception: pass
    raise JoinError("outline rounding failed")

def plan_union(faces, rin=10.0, rout=4.0):
    """union of plan faces via thin prisms (2D face fuse does not always merge coplanar pieces), then rounded."""
    u = prism(faces[0], 0, 1)
    for f in faces[1:]: u = u.fuse(prism(f, 0, 1))
    u = u.clean(); ss = u.solids()
    if len(ss) != 1: raise JoinError("plan pieces do not touch (%d islands)" % len(ss))
    top = max([f for f in ss[0].faces() if f.normal_at().Z > 0.99 and abs(f.center().Z - 1) < 1e-6], key=lambda f: f.area)
    return round_outline(top.moved(Location((0, 0, -1))), rin, rout)

def poly_face(pts, rin=10.0, rout=4.0):
    return round_outline(Face(Wire.make_polygon([Vector(x, y, 0) for x, y in pts], close=True)), rin, rout)

def prism(face, z0, z1):
    s = Solid.extrude(face.moved(Location((0, 0, z0))), Vector(0, 0, z1 - z0))
    return s if s.volume > 0 else Solid(s.wrapped.Reversed())

def skirt(face, z0, r, support=None, down=False, inset=0.0):
    """Concave blend ring at the foot of prism(face) standing on a flat seat at z0 (down=True: hanging below a seat)."""
    w = face.outer_wire().offset_2d(r, kind=Kind.ARC)
    sg = -1 if down else 1
    blk = prism(Face(w), z0, z0 + sg * r) if not down else prism(Face(w), z0 - r, z0)
    path = w.moved(Location((0, 0, z0 + sg * r)))
    e0 = path.edges()[0]
    tube = Solid.sweep(Face(Wire.make_circle(r, Plane(origin=e0.position_at(0), z_dir=e0.tangent_at(0)))), path, transition=Transition.ROUND)
    sk = _one(blk.cut(tube)); sk = _one(sk.cut(prism(face, z0 - r - 1, z0 + r + 1)))
    if support is not None:     # inset = the seat's own edge round: clip short of it, or the skirt end overhangs it as a 0 mm lip
        sup = support if inset <= 0 else Face(support.outer_wire().offset_2d(-inset, kind=Kind.ARC))
        sk = _one(sk.intersect(prism(sup, z0 - r - 1, z0 + r + 1)))
    return sk

def round_edges(solid, radii=(4.0, 3.0, 2.0, 1.5), select=None, name="", log=print, chamfers=(1.5, 1.0, 0.5)):
    """Edge-round ONE region on its own (before any join), where the kernel copes: all edges, or those `select(edge)` keeps.
    Tries each radius; returns (solid, radius) - radius None when nothing worked (caller reports it)."""
    es = [e for e in solid.edges() if select is None or select(e)]
    if not es: return solid, None
    for r in radii:
        try:
            s = solid.fillet(r, es)
            if s.is_valid and len(s.solids()) == 1: return s.solids()[0], r
        except Exception: pass
    for c in chamfers:          # fallback (the owner): break the outside edges with a small 45 deg chamfer instead
        try:
            s = solid.chamfer(c, None, es)
            if s.is_valid and len(s.solids()) == 1: log("  %s: fillet failed -> chamfer %.1f x 45" % (name, c)); return s.solids()[0], "ch%.1f" % c
        except Exception: pass
    log("  edge round AND chamfer failed: %s (%d edges)" % (name, len(es))); return solid, None

def above(z):   return lambda e: min(e.position_at(0).Z, e.position_at(1).Z, e.position_at(0.5).Z) > z + 0.01
def not_at(*zs): return lambda e: not any(abs(e.position_at(t).Z - z) < 0.01 for z in zs for t in (0, 0.5, 1))
