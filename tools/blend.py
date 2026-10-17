"""Rolling-ball blend (fillet-equivalent) solids for build123d / OCC, for junctions where kernel fillets fail.
Needs shapely (2-D section regions); demo/compare reference volumes need scipy.

    from blend import blend, fuse_blend
    res = blend(arm, plate, r=6)                  # BlendResult: .pieces (solids to fuse), .expected_mm3, .samples, .notes
    part, rep = fuse_blend(arm + plate, res)      # fused part + checks (valid, 1 solid, added volume vs expected)

    .venv/bin/python tools/blend.py demo --angle 45 --r 6 -o runs/tilt45  # tilted cylinder on a plate, STEP + JSON report
    .venv/bin/python tools/blend.py pair A.step B.step --r 6 [--base body.step] -o out
    .venv/bin/python tools/blend.py compare --angle 45 --r 6              # tube / classic approaches side by side (volume checks)

How it works ("section loft", what blend() does):
 1. crease = BRepAlgoAPI_Section of the two solids (or the wire(s) you pass as paths=): where their surfaces cross.
 2. Ball sections: at points along the crease solve for the rolling-ball centre c with dist(c, A) = dist(c, B) = r
    (Newton on two BRepExtrema distance queries); the closest points are the tangent points, nA, nB = (c - p) / r.
    Each section lies in the plane of nA, nB (normal to the ball-centre curve) = a true rolling ball.
    If a section would reach further from c than the centre curve's turning radius (acute wedges on curved bodies:
    neighbouring sections would cross and the loft self-intersects), the loop is redone with crease-normal sections:
    each plane is normal to the crease and the circle is tangent to the two 2-D section curves (constant-radius
    cross-section blend; within ~3 % of the rolling-ball volume in the tests).
 3. Each section: the r arc between the tangent points, trimmed 4 deg short of each, a steep line to 0.3 mm under the
    tangent point, closed through the crease point pushed 0.6 mm into both solids. The blend surface therefore crosses
    each face at ~35 deg (robust boolean) instead of touching it (the step left is r (1 - cos 4 deg) = 0.015 mm at r6).
 4. Section spacing (adaptive, default): start at 2 x step, then halve every interval whose ruled strip is more than
    chord_tol (0.005 mm) off the true blend surface, measured against a section built half-way (strip_deviation()).
    Curved / twisting roots get dense sections, straight ones stay coarse, so no flat "teeth" between sections.
 5. Failed sections (crease over a small round or edge): retried nudged along the crease, then with a locally shrunk
    radius; sections that cross a neighbour's plane (concave round smaller than r: the loft would fold) are removed.
    Whatever is left out is listed in res.skipped (loop, u, xyz, reason) and logged as a WARNING; gaps up to 3 x step
    are bridged, wider ones split the loft into separate runs. Nothing is dropped silently.
 6. Ruled loft through the sections (closed loop -> closed loft; loft='auto' / 'smooth' tries a B-spline loft with the
    ruled one as fallback), fuse, check.
No offsets of the input bodies and no pipe sweeps, so it works on lofted / multi-face bodies where BRepOffsetAPI and
MakePipeShell fail.

Checks: fuse_blend() returns valid, solid count (single_valid_solid), STEP re-import, skipped_sections, and the volume check: the fused part must gain the
expected volume within 10 %. Expected = sum over sections of the true 2-D region (section profile minus A and B, cut
in each section plane, so it follows a dihedral angle that changes along the crease) times the slab between
neighbouring sections. The gain is measured locally as vol(pieces - base) with a mesh cross-check (added_volume),
never as part.volume - base.volume: OCC's volume integral can be ~1 % off on extrusion / B-spline bodies, and the
difference of two big volumes then swamps the fillet. A fake / twisted / inside-out solid (the ~4 % tubes) fails
the check. For flat faces expected = r^2 (cot(t/2) - (pi - t)/2) per mm for dihedral angle t ((1 - pi/4) r^2 at
90 deg), reported as planar_formula_mm3.

Also here: ball_tube() (rolling-ball swept volume along a path, MakePipeShell with CorrectedFrenet / Frenet / fixed
binormal, or a chain of capsules, checked against pi r^2 L) and blend_classic() (offset(A, r) & offset(B, r) - tube
- A - B), kept for comparison: the classic construction is exact only at 90 deg (it overfills obtuse wedges, stops
short in acute ones) and also fills every place where A and B come within 2 r of each other.
"""
import math, time, resource, json, os
from dataclasses import dataclass, field
from build123d import *
from build123d.topology.shape_core import Shape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCP.gp import gp_Pnt, gp_Dir
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopoDS import TopoDS
_to_edge = getattr(TopoDS, "Edge_s", None) or TopoDS.Edge          # OCP 7.7 vs 7.8 naming

# ------------------------------------------------------------------ small helpers
def pos(s):
    """Solid with outward orientation (lofts sometimes come out inside-out with negative volume)."""
    return Solid(s.wrapped.Reversed()) if s.volume < 0 else s

def one(x):
    """Single solid from a boolean result, or a Compound of the non-trivial solids."""
    ss = [s for s in (x.solids() if hasattr(x, "solids") else [x]) if abs(s.volume) > 1e-3]
    return ss[0] if len(ss) == 1 else Compound(ss)

def peak_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

def section_area(t, r):
    """Cross-section area of a rolling-ball fillet of radius r in a wedge of dihedral angle t (radians)."""
    return r * r * (1 / math.tan(t / 2) - (math.pi - t) / 2)

class Dist:
    """Fast repeated point-to-shape distance (closest point) queries."""
    def __init__(self, shape):
        self.s = shape.wrapped
    def __call__(self, p):
        v = BRepBuilderAPI_MakeVertex(gp_Pnt(p.X, p.Y, p.Z)).Vertex()
        d = BRepExtrema_DistShapeShape(v, self.s); d.Perform()
        if not d.IsDone() or d.NbSolution() == 0: raise RuntimeError("distance query failed")
        q = d.PointOnShape2(1); return d.Value(), Vector(q.X(), q.Y(), q.Z())

def outward_normal(S, p, tol=1e-3):
    """Outward normal of solid S at a point p on its boundary (from the face that contains p)."""
    best = None
    for f in S.faces():
        bb = f.bounding_box()
        if not (bb.min.X - tol <= p.X <= bb.max.X + tol and bb.min.Y - tol <= p.Y <= bb.max.Y + tol and bb.min.Z - tol <= p.Z <= bb.max.Z + tol):
            continue
        d, _ = Dist(f)(p)
        if best is None or d < best[0]: best = (d, f)
    if best is None or best[0] > 10 * tol: raise RuntimeError("no face at %s" % p)
    return best[1].normal_at(p).normalized()

# ------------------------------------------------------------------ crease + ball centres
def crease_loops(A, B, tol=1e-3):
    """Wires where the surfaces of A and B cross (the edge a fillet would run along)."""
    sec = BRepAlgoAPI_Section(A.wrapped, B.wrapped); sec.Build()
    es = []; ex = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
    while ex.More(): es.append(Edge(_to_edge(ex.Current()))); ex.Next()
    return list(Wire.combine(es, tol=tol)) if es else []

def is_closed(w, tol=0.05):
    return (w.position_at(0) - w.position_at(1)).length < tol

def kinks(loop, ds=0.2, max_deg=25.0):
    """Wire parameters where the crease turns by more than max_deg within ds (it runs over a sharp edge of A or B,
    e.g. a flat end cap). A ruled loft cannot turn such a corner, so blend() splits the loop there."""
    n = max(64, int(loop.length / ds)); P = [loop.position_at(i / n) for i in range(n + 1)]
    closed = is_closed(loop); out = []
    for i in range(1, n):
        a, b = P[i] - P[i - 1], P[i + 1] - P[i]
        if a.length < 1e-9 or b.length < 1e-9: continue
        if math.degrees(math.acos(max(-1.0, min(1.0, a.normalized().dot(b.normalized()))))) > max_deg: out.append(i / n)
    if closed:
        a, b = P[n] - P[n - 1], P[1] - P[0]
        if a.length > 1e-9 and b.length > 1e-9 and math.degrees(math.acos(max(-1.0, min(1.0, a.normalized().dot(b.normalized()))))) > max_deg: out.append(0.0)
    merged = []
    for u in sorted(out):
        if not merged or (u - merged[-1]) * loop.length > 1.0: merged.append(u)
    if closed and len(merged) > 1 and (1 - merged[-1] + merged[0]) * loop.length < 1.0: merged.pop()
    return merged

def segments(loop, step, phase=0.5, min_len=2.0):
    """Sample parameters per smooth stretch of the crease: [(us, closed)]. One closed list if there is no kink.
    Parameters of a stretch that runs over the loop's start are UNWRAPPED (> 1, increasing): evaluate with _uw()."""
    L = loop.length; ks = kinks(loop); closed = is_closed(loop)
    if not ks:
        n = max(16, int(math.ceil(L / step)))
        if closed: return [([(i + phase) / n for i in range(n)], True)], ks
        return [([0.0] + [(i + phase) / n for i in range(n)] + [1.0], False)], ks
    cuts = ks + ([ks[0] + 1.0] if closed else [])
    if not closed: cuts = [0.0] + cuts + [1.0]
    out = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        ln = (b - a) * L
        if ln < min_len: continue
        n = max(3, int(math.ceil(ln / step)))
        out.append(([a + (b - a) * (i + phase) / n for i in range(n)], False))
    return out, ks

def _uw(u):
    """Wire parameter in [0, 1] for an unwrapped parameter (1.0 itself stays 1.0: the end of an open wire)."""
    return u - math.floor(u) if u > 1.0 else u

def ball_at(c, dA, dB, r, it=30, tol=1e-4):
    """Newton: move c until dist(c, A) = dist(c, B) = r. Returns dict or None."""
    for _ in range(it):
        a, pA = dA(c); b, pB = dB(c)
        if a < 1e-6 or b < 1e-6: return None
        nA, nB = (c - pA) / a, (c - pB) / b; k = nA.dot(nB)
        if abs(a - r) < tol and abs(b - r) < tol:
            t = math.pi - math.acos(max(-1.0, min(1.0, k)))
            return dict(c=c, pA=pA, pB=pB, nA=nA, nB=nB, t=t)
        det = 1 - k * k
        if det < 1e-6: return None                               # faces nearly tangent: no crease to fill here
        x = ((r - a) - k * (r - b)) / det; y = ((r - b) - k * (r - a)) / det
        step = nA * x + nB * y
        if step.length > r / 2: step = step * (r / 2 / step.length)
        c = c + step
    return None

def ball_sample(loop, u, A, B, r, dA=None, dB=None, prev=None):
    """One rolling-ball section at wire parameter u: (sample, None) or (None, reason)."""
    dA, dB = dA or Dist(A), dB or Dist(B)
    q = loop.position_at(_uw(u))
    try:
        nA, nB = outward_normal(A, q), outward_normal(B, q)
    except Exception:
        return None, "no face normal at the crease point"
    k = max(-0.999, min(0.999, nA.dot(nB))); t = math.pi - math.acos(k)
    w = (nA + nB); w = w / w.length if w.length > 1e-9 else nA
    c0 = q + w * (r / math.sin(t / 2))
    s = ball_at(c0, dA, dB, r) or (ball_at(prev["c"], dA, dB, r) if prev else None)
    if s is None: return None, "no ball position (faces tangent here, or the ball does not fit)"
    s["q"], s["wq"], s["u"], s["r"] = q, -w, u, r                       # crease point + direction into both solids
    return s, None

def normal_sample(loop, u, A, B, r, dA=None, dB=None, prev=None):
    """One crease-normal section at wire parameter u (circle tangent to the two 2-D section curves): (sample, None)
    or (None, reason)."""
    uu = _uw(u); q = loop.position_at(uu); e_ = 1e-4
    T = loop.position_at(min(1.0, uu + e_)) - loop.position_at(max(0.0, uu - e_))   # chord tangent: right at seams too
    if T.length < 1e-9: return None, "no crease tangent"
    T = T.normalized()
    try:
        nA, nB = outward_normal(A, q), outward_normal(B, q)
    except Exception:
        return None, "no face normal at the crease point"
    nA, nB = nA - T * nA.dot(T), nB - T * nB.dot(T)
    if nA.length < 1e-6 or nB.length < 1e-6: return None, "face normal along the crease"
    nA, nB = nA.normalized(), nB.normalized()
    k = max(-0.999, min(0.999, nA.dot(nB))); t = math.pi - math.acos(k)
    w = (nA + nB); w = w / w.length if w.length > 1e-9 else nA
    reach = r / math.sin(t / 2) + 3 * r
    pl = Plane(origin=q, z_dir=T)
    eA, eB = _section_edges(A, pl, reach), _section_edges(B, pl, reach)
    if eA is None or eB is None: return None, "empty 2-D section"
    s = ball_at(q + w * (r / math.sin(t / 2)), Dist(eA), Dist(eB), r)
    if s is None: return None, "no section circle (the circle does not fit)"
    s["q"], s["wq"], s["u"], s["r"] = q, -w, u, r
    return s, None

def _default_us(loop, r, step, phase):
    L = loop.length; step = step or min(1.0, r / 4); n = max(16, int(math.ceil(L / step)))
    closed = is_closed(loop)
    return ([(i + phase) / n for i in range(n)] if closed else [0.0] + [(i + phase) / n for i in range(n)] + [1.0]), closed

def trace(loop, A, B, r, step=None, phase=0.5, log=print, us=None, closed=None):
    """Ball positions along one crease loop. Each sample: c, tangent points pA/pB, normals nA/nB, dihedral t, crease
    point q, wire parameter u, radius r. phase: offset of the samples in steps. The crease wire starts on a vertex (often
    a face seam) and a section plane through a seam makes the later boolean misclassify, so samples sit between the
    wire's vertices by default. Misses are logged as a WARNING with their positions."""
    dA, dB = Dist(A), Dist(B)
    if us is None: us, closed = _default_us(loop, r, step, phase)
    out, miss, prev = [], [], None
    for u in us:
        s, why = ball_sample(loop, u, A, B, r, dA, dB, prev)
        if s is None: miss.append(u); continue
        out.append(s); prev = s
    if miss: log("  WARNING trace: %d of %d crease points had no ball position (skipped) at u = %s"
                 % (len(miss), len(us), ", ".join("%.4f" % m for m in miss[:12])))
    return out, closed

def _section_edges(S, plane, radius):
    """Edges of solid S cut by a disc of `radius` in `plane` (the 2-D section near the plane origin)."""
    disc = Face(Wire.make_circle(radius, plane))
    x = S.intersect(disc)
    es = x.edges() if x is not None else []
    return Compound(list(es)) if es else None

def trace_normal(loop, A, B, r, step=None, phase=0.5, log=print, us=None, closed=None):
    """Like trace(), but every section lies in the plane NORMAL TO THE CREASE and the circle of radius r is tangent to
    the two 2-D section curves (a constant-radius cross-section blend). Sections then fan out from the crease and never
    overlap, also where the rolling-ball centre curve turns tighter than r / sin(t/2) (acute wedges on curved bodies)."""
    if us is None: us, closed = _default_us(loop, r, step, phase)
    out, miss = [], []
    for u in us:
        s, why = normal_sample(loop, u, A, B, r)
        if s is None: miss.append(u); continue
        out.append(s)
    if miss: log("  WARNING trace: %d of %d crease points had no section circle (skipped) at u = %s"
                 % (len(miss), len(us), ", ".join("%.4f" % m for m in miss[:12])))
    return out, closed

def centre_min_radius(samples, closed):
    """Smallest turning radius of the ball-centre polyline (a tube or loft self-intersects if it is < r)."""
    P = [s["c"] for s in samples]; n = len(P); best = 1e9
    rng = range(n) if closed else range(2, n - 2)
    for i in rng:
        a, b, c = P[(i - 2) % n], P[i], P[(i + 2) % n]
        ab, bc, ca = (b - a).length, (c - b).length, (a - c).length; s = (ab + bc + ca) / 2
        ar = max(s * (s - ab) * (s - bc) * (s - ca), 1e-18) ** 0.5
        best = min(best, ab * bc * ca / (4 * ar))
    return best

# ------------------------------------------------------------------ sections, expected volume, loft
def _slerp(a, b, f):
    th = math.acos(max(-1.0, min(1.0, a.dot(b))))
    if th < 1e-9: return a
    return (a * math.sin((1 - f) * th) + b * math.sin(f * th)) / math.sin(th)

def section_wire(s, r, trim_deg=4.0, depth=0.6, dip=0.3):
    """Closed section: the exact r arc between the two tangent points, trimmed trim_deg short of each one, then a short
    steep line down to dip below the tangent point, closed through the crease point pushed depth into both solids
    (NOT the planar-wedge apex: on curved faces that point can land outside the material). The fillet surface
    therefore CROSSES each face at ~35 deg (robust boolean) instead of touching it tangentially; the step this leaves is
    r (1 - cos trim) high (0.015 mm at r6)."""
    c, nA, nB, t = s["c"], s["nA"], s["nB"], s["t"]
    dA, dB = -nA, -nB; th = math.acos(max(-1.0, min(1.0, dA.dot(dB))))
    e = min(math.radians(trim_deg), th / 4)
    aA, mid, aB = (c + _slerp(dA, dB, f) * r for f in (e / th, 0.5, 1 - e / th))
    kA, kB = c + dA * (r + dip), c + dB * (r + dip)                    # just under each tangent point
    n = nA.cross(nB); n = n / n.length                                  # section plane normal (= crease direction)
    q = s["q"] - n * (s["q"] - c).dot(n); wq = s["wq"] - n * s["wq"].dot(n); wq = wq / wq.length
    inner = q + wq * depth                                              # the real crease point (in the plane), pushed into both solids
    pts = [aB, kB, inner, kA, aA]
    return Wire([Edge.make_three_point_arc(aA, mid, aB)] + [Edge.make_line(pts[i], pts[i + 1]) for i in range(4)])

def _poly2d(S, plane, radius, e1, e2, o, ds=0.25):
    """2-D (shapely) region of solid S in `plane` within `radius` of the plane origin, in the (e1, e2) frame at o."""
    from shapely.geometry import Polygon as SPoly
    from shapely.ops import unary_union
    x = S.intersect(Face(Wire.make_circle(radius, plane)))
    fs = x.faces() if x is not None else []
    out = []
    for f in fs:
        def ring(w):
            n = max(64, int(w.length / ds))
            return [((p - o).dot(e1), (p - o).dot(e2)) for p in (w.position_at(i / n) for i in range(n))]
        try:
            out.append(SPoly(ring(f.outer_wire()), [ring(h) for h in f.inner_wires()]).buffer(0))
        except Exception: pass
    return unary_union(out) if out else None

def _sub_ring(ring, a, b, m):
    """m + 1 points along the closed ring from its nearest point to a to its nearest point to b, the shorter way."""
    L = ring.length; sa, sb = ring.project(a), ring.project(b)
    d = (sb - sa) % L
    if d > L / 2: d -= L
    return [ring.interpolate((sa + d * k / m) % L) for k in range(m + 1)]

def section_wire_follow(s, r, A, B, trim_deg=4.0, depth=0.6, dip=0.3, m=8):
    """Like section_wire(), but the closing path FOLLOWS the two 2-D section curves (dip under them) from each tangent
    point to the crease instead of cutting straight across. Needed where a face is concave in the section (a plate wall
    between lobes, an arm flank), where the straight chord would leave the solid and cross the blend.
    Fixed edge count (arc + 2 m + 2 lines) so all sections loft together. None if it cannot be built."""
    from shapely.geometry import Point as SPt, LinearRing
    c, nA, nB, t = s["c"], s["nA"], s["nB"], s["t"]
    n = nA.cross(nB); n = n / n.length; e1 = (-nA); e2 = n.cross(e1)
    to2 = lambda p: ((p - c).dot(e1), (p - c).dot(e2))
    to3 = lambda x, y: c + e1 * x + e2 * y
    q = s["q"] - n * (s["q"] - c).dot(n)
    reach = (q - c).length + 2 * r
    pl = Plane(origin=c, x_dir=e1, z_dir=n)
    SA, SB = _poly2d(A, pl, reach, e1, e2, c), _poly2d(B, pl, reach, e1, e2, c)
    if SA is None or SB is None or SA.is_empty or SB.is_empty: return None
    def inward(S):
        g = S.buffer(-dip)
        if g.is_empty: return None
        if g.geom_type == "MultiPolygon": g = max(g.geoms, key=lambda x: x.area)
        return g
    Ai, Bi = inward(SA), inward(SB)
    if Ai is None or Bi is None: return None
    # each offset ring: the polygon piece nearest the crease
    def ring_near(g, p):
        return g.exterior
    pA2, pB2, q2 = SPt(*to2(s["pA"])), SPt(*to2(s["pB"])), SPt(*to2(q))
    pathB = _sub_ring(ring_near(Bi, q2), pB2, q2, m)
    pathA = _sub_ring(ring_near(Ai, q2), q2, pA2, m)
    AB = SA.intersection(SB).buffer(-min(depth, dip))
    if AB.is_empty: AB = SA.intersection(SB)
    if AB.is_empty: return None
    from shapely.ops import nearest_points
    I = nearest_points(AB, q2)[0]
    dA, dB = -nA, -nB; th = math.acos(max(-1.0, min(1.0, dA.dot(dB))))
    e = min(math.radians(trim_deg), th / 4)
    aA, mid, aB = (c + _slerp(dA, dB, f) * r for f in (e / th, 0.5, 1 - e / th))
    pts2 = [to2(aB)] + [(p.x, p.y) for p in pathB] + [(I.x, I.y)] + [(p.x, p.y) for p in pathA] + [to2(aA)]
    # the closing polyline + the arc must be a simple ring
    arc2 = [to2(c + _slerp(dA, dB, f) * r) for f in [e / th + (1 - 2 * e / th) * k / 16 for k in range(17)]]
    ringpts = arc2 + pts2[1:-1]
    if not LinearRing(ringpts).is_simple: return None
    for i in range(len(pts2) - 1):
        if math.dist(pts2[i], pts2[i + 1]) < 1e-3: return None
    P3 = [to3(*p) for p in pts2]
    return Wire([Edge.make_three_point_arc(aA, mid, aB)] + [Edge.make_line(P3[i], P3[i + 1]) for i in range(len(P3) - 1)])

def section_centroid(s, r, m=24):
    """Area and centroid of the exact fillet cross-section (kite minus ball sector) at sample s."""
    c, nA, nB, t = s["c"], s["nA"], s["nB"], s["t"]
    w = -(nA + nB); w = w / w.length
    pA, pB, apex = c - nA * r, c - nB * r, c + w * (r / math.sin(t / 2))
    e1 = (pA - c) / r; e2 = w - e1 * w.dot(e1); e2 = e2 / e2.length    # in-plane basis
    a1 = math.atan2((pB - c).dot(e2), (pB - c).dot(e1))
    arc = [c + (e1 * math.cos(a1 * i / m) + e2 * math.sin(a1 * i / m)) * r for i in range(m + 1)]
    poly = [apex] + arc                                                 # apex -> pA ... pB -> apex
    xy = [((p - c).dot(e1), (p - c).dot(e2)) for p in poly]
    A2 = cx = cy = 0.0
    for i in range(len(xy)):
        (x0, y0), (x1, y1) = xy[i], xy[(i + 1) % len(xy)]; cr = x0 * y1 - x1 * y0
        A2 += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
    A = abs(A2) / 2
    return A, (c + e1 * (cx / (3 * A2)) + e2 * (cy / (3 * A2))) if A > 1e-12 else c

def section_region(s, wire, body):
    """Area and centroid of (section profile - body) in the section plane: what the loft SHOULD add there."""
    try:
        f = Face(wire); reg = f.cut(body)
        fs = reg.faces() if reg is not None else []
        a = sum(x.area for x in fs)
        if a <= 1e-9: return 0.0, s["c"]
        cen = sum((x.center() * x.area for x in fs), Vector()) / a
        return a, cen
    except Exception:
        return None

def expected_from_sections(samples, wires, body, closed, every=1):
    """Pappus sum of the true 2-D section regions (profile minus the bodies), every `every`-th section."""
    idx = list(range(0, len(samples), every)); ac = []
    for i in idx:
        x = section_region(samples[i], wires[i], body)
        if x is not None:
            s = samples[i]; nrm = s["nA"].cross(s["nB"]).normalized(); ac.append((x[0], x[1], nrm))
    n = len(ac); V = 0.0
    for i in range(n if closed else n - 1):
        (a0, c0, n0), (a1, c1, n1) = ac[i], ac[(i + 1) % n]
        nm = n0 + n1 if n0.dot(n1) > 0 else n0 - n1; nm = nm.normalized()
        V += 0.5 * (a0 + a1) * abs((c1 - c0).dot(nm))          # slab between two (rotating) section planes
    return V, len(ac)

def expected_volume(samples, r, closed):
    """Pappus sum of the exact section areas along the section centroids."""
    ac = [section_centroid(s, s.get("r", r)) for s in samples]; n = len(ac); V = 0.0
    for i in range(n if closed else n - 1):
        (a0, c0), (a1, c1) = ac[i], ac[(i + 1) % n]; V += 0.5 * (a0 + a1) * (c1 - c0).length
    return V

def loft_sections(wires, closed, chunk=40, ruled=True):
    """Closed (or open) loft through the sections; if one loft fails, abutting chunks that share their end sections.
    ruled=True: one ruled strip per section pair (flat facets between sections: 'teeth' on curved roots unless the
    sections are close, see blend(adaptive=True)). ruled=False: B-spline (approximated) loft through the sections."""
    try:
        s = pos(Solid.make_loft(wires + [wires[0]] if closed else wires, ruled=ruled))
        if s.is_valid and s.volume > 0: return [s], "one %s loft" % ("ruled" if ruled else "smooth")
    except Exception: pass
    W = wires + [wires[0]] if closed else wires; out = []
    for i in range(0, len(W) - 1, chunk):
        part = W[i:i + chunk + 1]
        if len(part) < 2: break
        s = pos(Solid.make_loft(part, ruled=ruled))
        if not s.is_valid: raise RuntimeError("loft chunk %d invalid" % (i // chunk))
        out.append(s)
    return out, "%d %s chunks" % (len(out), "ruled" if ruled else "smooth")

def loft_auto(wires, closed, mode="auto", vol_tol=0.02):
    """Pieces for one run of sections. mode 'ruled' | 'smooth' | 'auto'. auto: the smooth B-spline loft if it is one
    valid solid whose volume is within vol_tol of the ruled loft (no wiggle / overshoot), else the ruled one.
    Returns (pieces, fallback pieces or None, description). fuse_blend() falls back to the ruled pieces when a smooth
    piece will not fuse into one valid solid or fails the volume check."""
    if mode == "ruled": p, how = loft_sections(wires, closed, ruled=True); return p, None, how
    try: sp, shw = loft_sections(wires, closed, ruled=False)
    except Exception as ex: sp, shw = None, "smooth loft failed (%s)" % str(ex)[:40]
    if mode == "smooth":
        if sp is None: raise RuntimeError(shw)
        return sp, None, shw
    rp, rhw = loft_sections(wires, closed, ruled=True)
    if sp is not None and len(sp) == 1 and len(rp) == 1 and sp[0].is_valid:
        vs, vr = sp[0].volume, rp[0].volume
        if vr > 0 and abs(vs / vr - 1) <= vol_tol: return sp, rp, shw + " (ruled kept as fallback)"
        shw = "smooth loft volume x%.3f of ruled" % (vs / vr if vr else 0)
    return rp, None, rhw + " (smooth rejected: %s)" % (shw if sp is None or len(sp) != 1 else (shw if "x" in shw else "not one valid solid"))

def arc_point(s, f):
    """Point at fraction f (0 = tangent point on A, 1 = on B) of the TRUE blend arc of section s."""
    dA, dB = -s["nA"], -s["nB"]
    return s["c"] + _slerp(dA, dB, f) * s.get("r", 1.0)

def strip_deviation(s0, s1, sm, fs=(0.25, 0.5, 0.75)):
    """How far the ruled strip between sections s0 and s1 is from the true blend surface at the section sm half-way
    between them: the strip point (average of the two arc points) vs the ball of sm. This is the tooth height."""
    return max(abs(((arc_point(s0, f) + arc_point(s1, f)) * 0.5 - sm["c"]).length - sm.get("r", 1.0)) for f in fs)

@dataclass
class BlendResult:
    pieces: list = field(default_factory=list)
    fallback: list = field(default_factory=list)    # per piece: ruled replacement (smooth piece) or None
    expected_mm3: float = 0.0
    loops: list = field(default_factory=list)       # per run: dict(n, length, closed, t range, min centre radius, loft)
    samples: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    skipped: list = field(default_factory=list)     # sections that could not be built: dict(loop, u, xyz, reason, bridged)
    adjusted: list = field(default_factory=list)    # sections built only after a fix: dict(loop, u, xyz, fix)
    seconds: float = 0.0

class _Sections:
    """Builds sections for one stretch of one crease loop, with recovery: if a section fails at u (the crease crosses
    a small round or edge), try u nudged by +-15 / 30 % of the local spacing, then a locally shrunk radius
    (0.8, 0.6, 0.4 r). What still fails is reported (never dropped silently)."""
    def __init__(self, lp, A, B, r, how, follow, trim_deg, depth):
        self.lp, self.A, self.B, self.r, self.how, self.follow = lp, A, B, r, how, follow
        self.trim, self.depth = trim_deg, depth; self.dA, self.dB = Dist(A), Dist(B); self.prev = None
    def one(self, u, r):
        f = ball_sample if self.how == "ball" else normal_sample
        s, why = f(self.lp, u, self.A, self.B, r, self.dA, self.dB, self.prev)
        if s is None: return None, None, why
        w = section_wire_follow(s, r, self.A, self.B, self.trim, self.depth) if self.follow else section_wire(s, r, self.trim, self.depth)
        if w is None: return None, None, "section profile could not be built (the crease crosses a small round / edge?)"
        return s, w, None
    def robust(self, u, du, lo=None, hi=None):
        s, w, why = self.one(u, self.r)
        if s is not None: self.prev = s; return s, w, None, None
        for k in (0.15, -0.15, 0.3, -0.3):
            uu = u + k * du
            if (lo is not None and uu <= lo) or (hi is not None and uu >= hi) or uu < 0: continue
            s, w, _ = self.one(uu, self.r)
            if s is not None: self.prev = s; return s, w, None, "moved %+.0f %% of the spacing" % (100 * k)
        for k in (0.8, 0.6, 0.4):
            s, w, _ = self.one(u, self.r * k)
            if s is not None: self.prev = s; return s, w, None, "radius shrunk to %.2f" % (self.r * k)
        return None, None, why, None

def _build_stretch(S, us, closed, L, tag, res, log):
    """Sections at us (sorted, unwrapped). Returns entries [(u, s, w)] and failures [(u, reason)]."""
    ok, bad = [], []
    for i, u in enumerate(us):
        du = (us[i + 1] - u) if i + 1 < len(us) else (u - us[i - 1] if i else 0.01)
        s, w, why, fix = S.robust(u, du, us[i - 1] if i else None, us[i + 1] if i + 1 < len(us) else None)
        if s is None: bad.append((u, why)); continue
        if fix: res.adjusted.append(dict(loop=tag, u=round(s["u"], 5), xyz=[round(x, 2) for x in s["q"]], fix=fix))
        ok.append((s["u"], s, w))
    return ok, bad

def _refine(S, ok, bad, closed, L, tol, step_min, max_sections, tag, res):
    """Adaptive spacing: halve every interval whose ruled strip deviates from the true blend by more than tol (checked
    against a section built half-way) until it fits or the spacing reaches step_min (crease mm)."""
    ok = sorted(ok, key=lambda e: e[0]); n_probe = 0
    i = 0
    while len(ok) < max_sections:
        n = len(ok); last = n if closed else n - 1
        if i >= last: break
        (u0, s0, w0), (u1, s1, w1) = ok[i], ok[(i + 1) % n]
        if i + 1 >= n: u1 = u1 + 1.0
        span = (u1 - u0) * L
        if span <= 2 * step_min or any(u0 < b[0] < u1 or u0 < b[0] + 1 < u1 for b in bad): i += 1; continue
        um = 0.5 * (u0 + u1); n_probe += 1
        s, w, why = S.one(um, S.r if abs(s0.get("r", S.r) - S.r) < 1e-9 else s0["r"])
        if s is None: i += 1; continue  # failed probe: leave interval coarse; do not count as a skipped section
        if strip_deviation(s0, s1, s) > tol:
            ok.insert(i + 1, (um, s, w))                                 # re-check the left half next
        else: i += 1
    if closed: ok = sorted(((u - math.floor(u), s, w) for u, s, w in ok), key=lambda e: e[0])
    return ok, n_probe

def _profile_points(s, depth, dip=0.3):
    r = s.get("r", 1.0); nrm = s["nA"].cross(s["nB"]).normalized()
    q = s["q"] - nrm * (s["q"] - s["c"]).dot(nrm); wq = s["wq"] - nrm * s["wq"].dot(nrm)
    wq = wq.normalized() if wq.length > 1e-9 else wq
    return [arc_point(s, f) for f in (0.0, 0.5, 1.0)] + [s["c"] - s["nA"] * (r + dip), s["c"] - s["nB"] * (r + dip), q + wq * depth]

def _crossing(ok, closed, depth, eps=1e-3):
    """Indices of sections whose profile crosses a neighbour's section plane (the crease turns tighter than the blend
    reaches, e.g. over a concave round smaller than r: the loft would fold over itself and the fuse fails)."""
    n = len(ok); P = [_profile_points(e[1], depth) for e in ok]; Q = [e[1]["c"] for e in ok]   # ball centre: in the plane
    N = []
    for i in range(n):
        a, b = Q[(i - 1) % n if closed or i else i], Q[(i + 1) % n if closed or i + 1 < n else i]
        d = b - a; nrm = ok[i][1]["nA"].cross(ok[i][1]["nB"]).normalized()
        N.append(nrm if d.length < 1e-12 or nrm.dot(d) >= 0 else nrm * -1)
    bad = set()
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        if any((p - Q[i]).dot(N[i]) < -eps for p in P[j]) or any((p - Q[j]).dot(N[j]) > eps for p in P[i]): bad.update((i, j))
    return sorted(bad)

def _drop_crossing(ok, bad, closed, depth, rounds=50):
    """Remove crossing sections (repeat until none cross) and record them as failures."""
    for _ in range(rounds):
        if len(ok) < 3: break
        ix = _crossing(ok, closed, depth)
        if not ix: break
        for i in ix: bad.append((ok[i][0], "sections cross: the crease turns tighter than the blend reaches (concave round / corner smaller than r)"))
        ok = [e for k, e in enumerate(ok) if k not in set(ix)]
    return ok

def _runs(ok, bad, closed, L, max_bridge):
    """Split the sections into runs at failed spots wider than max_bridge (crease mm); narrower gaps are bridged."""
    us = [e[0] for e in ok]; cut = []
    n = len(ok)
    for i in range(n if closed else n - 1):
        u0, u1 = us[i], us[(i + 1) % n] + (1.0 if i + 1 >= n else 0.0)
        hit = [b for b in bad if u0 < b[0] < u1 or (closed and u0 < b[0] + 1.0 < u1)]
        if hit: cut.append((i, (u1 - u0) * L > max_bridge, hit))
    splits = [i for i, wide, _ in cut if wide]
    if not splits: return [(ok, closed)], cut
    if closed:
        k = splits[0] + 1; ok = ok[k:] + ok[:k]; splits = sorted(((i - k) % n) for i in splits)
    runs, start = [], 0
    for i in splits:
        runs.append(ok[start:i + 1]); start = i + 1
    runs.append(ok[start:])
    return [(r_, False) for r_ in runs if len(r_) >= 2], cut

def blend(A, B, r, paths=None, step=None, trim_deg=4.0, depth=0.6, min_loop=2.0, loops=None, phase=0.5, section_every=1,
          method="auto", ruled=None, follow=True, adaptive=True, chord_tol=0.005, step_min=None, max_bridge=None,
          loft="ruled", max_sections=3000, log=print):
    """Rolling-ball blend solids between solids A and B along all crease loops (or the given loop indices, or your own
    crease wires via paths=). method: 'auto' (ball sections, crease-normal where they would cross), 'ball', 'normal'.
    adaptive (default): start at 2 x step and halve every interval whose ruled strip is more than chord_tol (mm) off the
    true blend surface (measured against a section half-way), down to step_min (default step / 8): fine where the root
    curves or twists, coarse where it is straight. adaptive=False: uniform step (the old behaviour).
    loft: 'ruled' (default), 'auto' (B-spline loft through the sections when it is one valid solid within 2 % of the
    ruled volume; the ruled loft is kept and used whenever the smooth piece does not fuse or fails the volume check),
    'smooth'. The B-spline loft is closer to the true surface between sections (p99 0.0007 vs 0.005 mm on the boss
    test) but overshoots at the closing seam of closed loops and where the spacing changes fast (up to 0.2 mm), so
    adaptive ruled is the default. ruled=True/False is the old switch and overrides loft.
    Sections whose profile crosses a neighbour's plane (the crease turns tighter than the blend reaches: a concave round
    smaller than r) are removed and reported like failed ones; the loft is split there, never folded over itself.
    Sections that fail (crease crossing a small round / edge) are retried nudged along the crease, then with a locally
    shrunk radius; what still fails is skipped with a WARNING and listed in res.skipped (loop, u, xyz, reason). Gaps
    wider than max_bridge (default 3 x step) split the loft into separate runs instead of bridging across.
    Expected volume per run = Pappus sum of the true section regions (profile minus A and B, cut in each section plane);
    planar_formula_mm3 = the same with r^2 (cot(t/2) - (pi - t)/2), exact for flat faces only."""
    t0 = time.time(); res = BlendResult(); body = A + B
    if ruled is not None: loft = "ruled" if ruled else "smooth"
    ls = list(paths) if paths is not None else crease_loops(A, B)
    log("  crease: %d loop(s), lengths %s" % (len(ls), [round(w.length, 1) for w in ls]))
    step = step or min(1.0, r / 4); step_min = step_min or step / 8; max_bridge = max_bridge or 3 * step
    for i, lp in enumerate(ls):
        if (loops is not None and i not in loops) or lp.length < min_loop: continue
        L = lp.length
        segs, ks = segments(lp, 2 * step if adaptive else step, phase)
        if ks: res.notes.append("loop %d: crease has %d sharp corner(s) (it runs over a sharp edge, e.g. a flat end cap); "
                                "blended as %d open stretch(es), corners left without a vertex blend" % (i, len(ks), len(segs)))
        for j_, (us, closed) in enumerate(segs):
            tag = "%d" % i if len(segs) == 1 else "%d.%d" % (i, j_)
            how_sec = "ball"
            S = _Sections(lp, A, B, r, "ball", follow, trim_deg, depth)
            ok, bad = _build_stretch(S, us, closed, L, tag, res, log)
            smp = [e[1] for e in ok]
            mr = centre_min_radius(smp, closed) if len(smp) > 5 else 1e9
            reach = max((r / math.sin(s_["t"] / 2) for s_ in smp), default=0) + depth
            if len(smp) >= 3 and (method == "normal" or (method == "auto" and reach > 0.9 * mr)):
                res.adjusted = [a_ for a_ in res.adjusted if a_["loop"] != tag]
                S = _Sections(lp, A, B, r, "normal", follow, trim_deg, depth); how_sec = "crease-normal"
                ok, bad = _build_stretch(S, us, closed, L, tag, res, log)
            n_probe = 0
            if adaptive and len(ok) >= 2:
                ok, n_probe = _refine(S, ok, bad, closed, L, chord_tol, step_min, max_sections, tag, res)
            if len(ok) >= 3: ok = _drop_crossing(ok, bad, closed, depth)
            bad.sort(key=lambda b: b[0])
            for u, why in bad:
                q = lp.position_at(_uw(u))
                res.skipped.append(dict(loop=tag, u=round(_uw(u), 5), xyz=[round(x, 2) for x in q], reason=why))
            runs, cuts = _runs(ok, bad, closed, L, max_bridge) if len(ok) >= 2 else ([], [])
            if bad:
                groups = []                                              # consecutive failures with the same reason
                for u, why in bad:
                    if groups and groups[-1][2] == why and u - groups[-1][1] <= 4 * step / L: groups[-1][1] = u; groups[-1][3] += 1
                    else: groups.append([u, u, why, 1])
                fmt = lambda u: "(%.1f, %.1f, %.1f)" % tuple(lp.position_at(_uw(u)))
                where = "; ".join(("%d at u=%.4f %s" % (g[3], _uw(g[0]), fmt(g[0])) if g[3] == 1 else
                                   "%d between u=%.4f %s and u=%.4f %s" % (g[3], _uw(g[0]), fmt(g[0]), _uw(g[1]), fmt(g[1]))) + ": " + g[2]
                                  for g in groups[:10]) + (" ..." if len(groups) > 10 else "")
                msg = ("WARNING loop %s: %d section(s) could not be built and were skipped: %s; %d gap(s) bridged, %d split into "
                       "separate runs (no blend in the split gaps)" % (tag, len(bad), where, sum(1 for c in cuts if not c[1]), sum(1 for c in cuts if c[1])))
                res.notes.append(msg); log("  " + msg)
            if not runs: res.notes.append("WARNING loop %s: too few sections, no blend here" % tag); continue
            for k_, (run, rclosed) in enumerate(runs):
                rtag = tag if len(runs) == 1 else "%s/%d" % (tag, k_)
                smp, wires = [e[1] for e in run], [e[2] for e in run]
                if len(wires) < 2: continue
                mr = centre_min_radius(smp, rclosed) if len(smp) > 5 else 1e9
                span = L if rclosed else ((run[-1][0] - run[0][0]) % 1.0 or 1.0) * L
                info = dict(loop=rtag, length=round(span, 1), closed=rclosed, samples=len(smp), sections=how_sec,
                            adaptive=adaptive, probes=n_probe, skipped=len(bad),
                            min_spacing=round(min(((b[0] - a[0]) % 1.0) * L for a, b in zip(run[:-1], run[1:])), 3),
                            t_min_deg=round(math.degrees(min(s_["t"] for s_ in smp)), 1), t_max_deg=round(math.degrees(max(s_["t"] for s_ in smp)), 1),
                            centre_min_radius=round(mr, 2))
                if mr < r: res.notes.append("loop %s: ball-centre curve turns tighter (%.2f) than r (%.2f): the true rolling ball would self-intersect" % (rtag, mr, r))
                pcs, fb, how = loft_auto(wires, rclosed, loft)
                info["loft"] = how; info["planar_formula_mm3"] = round(expected_volume(smp, r, rclosed), 1)
                ve, ns = expected_from_sections(smp, wires, body, rclosed, every=section_every)
                info["expected_mm3"] = round(ve, 1); info["expected_sections"] = ns
                res.pieces += pcs; res.fallback += (fb if fb and len(fb) == len(pcs) else [None] * len(pcs))
                res.expected_mm3 += info["expected_mm3"]; res.loops.append(info); res.samples += smp
                log("  loop %s: %d %s sections (min spacing %.3f mm, %d probes), dihedral %.0f..%.0f deg, centre radius >= %.1f, %s, expected %.0f mm3 (flat-face formula %.0f)"
                    % (rtag, len(smp), how_sec, info["min_spacing"], n_probe, info["t_min_deg"], info["t_max_deg"], mr, how, info["expected_mm3"], info["planar_formula_mm3"]))
    if res.adjusted: res.notes.append("%d section(s) built only after a local fix (moved along the crease / smaller radius): %s"
                                      % (len(res.adjusted), "; ".join("%s u=%.4f %s" % (a_["loop"], a_["u"], a_["fix"]) for a_ in res.adjusted[:8])))
    res.seconds = time.time() - t0
    return res

# ------------------------------------------------------------------ fuse + checks
def check_solid(S, step_path=None):
    r = dict(valid=bool(S.is_valid), solids=len(S.solids()), volume_mm3=round(S.volume, 1))
    if step_path:
        export_step(S, step_path); b = import_step(step_path)
        r.update(step=step_path, reimport_valid=bool(b.is_valid), reimport_solids=len(b.solids()),
                 reimport_volume_mm3=round(b.volume, 1))
    r["ok"] = r["valid"] and r["solids"] == 1 and (not step_path or (r["reimport_valid"] and r["reimport_solids"] == 1
                                                                      and abs(r["reimport_volume_mm3"] - r["volume_mm3"]) < 1e-3 * r["volume_mm3"] + 1))
    return r

def volume_verdict(actual, expected, tol=0.1):
    if expected <= 0: return "no expected volume"
    q = actual / expected
    return "PASS" if abs(q - 1) <= tol else ("FAKE/EMPTY" if q < 0.5 else "MISMATCH")

def mesh_volume(S, tol=0.005):
    """Volume of a fine triangulation (signed tetrahedra). Independent of OCC's volume integration."""
    vs, ts = S.tessellate(tol, 0.05); v = 0.0
    P = [(p.X, p.Y, p.Z) for p in vs]
    for a, b, c in ts:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = P[a], P[b], P[c]
        v += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
    return v / 6.0

def added_volume(base, pieces, part=None):
    """Volume the blend pieces add to base, measured locally as vol(pieces - base) (a small solid), with a mesh-volume
    cross-check. Not part.volume - base.volume: OCC's volume integration (GProp) can be off by 0.5-1 % on big bodies
    with extrusion / B-spline faces (lf20 tongue: 220101 mm3 by GProp, 218591 by a 0.003 mm mesh), and the error
    changes when the fuse re-trims those faces, so the difference of two big volumes can be off by more than a whole
    fillet (lf20 tongue + plate: 1148 vs 870 mm3 -> a false x1.31 MISMATCH). Returns (added, report fields)."""
    rep = {}
    if part is not None: rep["added_gprop_diff_mm3"] = round(part.volume - base.volume, 1)   # old metric, for reference
    try:
        U = pieces[0] if len(pieces) == 1 else pieces[0].fuse(*pieces[1:]).clean()
        D = U.cut(base); sols = D.solids() if D is not None else []
        if not sols: raise RuntimeError("empty")
        vg = sum(s.volume for s in sols)
        try: vm = sum(mesh_volume(s) for s in sols)
        except Exception: vm = None
        rep.update(added_method="pieces - base", added_local_gprop_mm3=round(vg, 1),
                   added_local_mesh_mm3=round(vm, 1) if vm is not None else None)
        added = vg
        if vm is not None and abs(vm - vg) > 0.02 * max(abs(vm), 1.0):        # GProp unreliable on these faces
            added = vm; rep["added_method"] = "pieces - base (mesh volume; GProp disagreed by %.1f %%)" % (100 * (vg / vm - 1))
    except Exception as ex:
        if part is None: raise
        added = part.volume - base.volume; rep["added_method"] = "part - base GProp difference (local cut failed: %s)" % str(ex)[:60]
    return added, rep

def fuse_blend(base, res, step_path=None, tol=0.1, log=print):
    """Fuse the blend pieces into base; checks validity, single solid, STEP re-import and added volume vs expected.
    A smooth (B-spline) piece that will not fuse into one valid solid is replaced by its ruled fallback; if the volume
    check then fails with smooth pieces in, the whole fuse is redone with the ruled pieces."""
    fb = list(res.fallback) + [None] * (len(res.pieces) - len(res.fallback))
    def run(pieces):
        part, used, swaps = base, [], 0
        for i, p in enumerate(pieces):
            cands = [p] + ([fb[i]] if fb[i] is not None and fb[i] is not p else [])
            for j, cand in enumerate(cands):
                done = False
                for f in (lambda: part + cand, lambda: part.fuse(cand).clean()):
                    try: q = f()
                    except Exception: continue
                    if len(q.solids()) == 1 and q.is_valid: part = q; used.append(cand); swaps += j; done = True; break
                if done: break
            else: raise RuntimeError("fuse of blend piece %d failed" % i)
        return part, used, swaps
    part, used, swaps = run(res.pieces)
    added, vrep = added_volume(base, used, part); notes = []
    if swaps: notes.append("%d smooth piece(s) would not fuse cleanly: ruled fallback used" % swaps)
    if volume_verdict(added, res.expected_mm3, tol) != "PASS" and any(f is not None for f in fb):
        rp = [f if f is not None else p for p, f in zip(res.pieces, fb)]
        part2, used2, _ = run(rp); added2, vrep2 = added_volume(base, used2, part2)
        # expected_mm3 can be 0 (no expected volume): never divide by it; prefer the closer absolute added volume.
        closer = (abs(added2 / res.expected_mm3 - 1) < abs(added / res.expected_mm3 - 1)
                  if res.expected_mm3 else abs(added2) < abs(added))
        if volume_verdict(added2, res.expected_mm3, tol) == "PASS" or closer:
            notes.append("volume check failed with the smooth lofts (added %.1f of %.1f mm3): redone with the ruled ones" % (added, res.expected_mm3))
            part, used, added, vrep = part2, used2, added2, vrep2
    res.used = used                                                     # the pieces actually fused (smooth or ruled)
    rep = check_solid(part, step_path); rep.update(vrep)
    rep["loft_used"] = "smooth" if any(u is p for u, p, f in zip(used, res.pieces, fb) if f is not None) else "ruled"
    rep["single_valid_solid"] = bool(rep["valid"] and rep["solids"] == 1)
    rep.update(added_mm3=round(added, 1), expected_mm3=round(res.expected_mm3, 1),
               ratio=round(added / res.expected_mm3, 4) if res.expected_mm3 else None,
               volume_check=volume_verdict(added, res.expected_mm3, tol),
               sections=sum(l.get("samples", 0) for l in res.loops), skipped_sections=len(res.skipped),
               skipped=res.skipped, adjusted_sections=len(res.adjusted), fuse_notes=notes)
    rep["ok"] = rep["ok"] and rep["single_valid_solid"] and rep["volume_check"] == "PASS"
    log("  fused: valid %s, solids %d, added %.1f vs expected %.1f mm3 (x%.3f) -> %s%s"
        % (rep["valid"], rep["solids"], added, res.expected_mm3, rep["ratio"] or 0, rep["volume_check"],
           ("; WARNING %d section(s) skipped" % len(res.skipped)) if res.skipped else ""))
    for n_ in notes: log("  " + n_)
    return part, rep

# ------------------------------------------------------------------ tubes and the classic construction (comparison)
def ball_tube(path, r, method="pipe", mode="corrected", seg=None):
    """Swept ball (tube with round ends) along a wire. method 'pipe' (MakePipeShell: mode 'corrected' | 'frenet' |
    'binormal' (fixed auxiliary binormal = the path's mean plane normal)) or 'capsules' (cylinders + spheres on a polyline).
    Returns (solid, check dict) where check compares the volume with pi r^2 L (+ 4/3 pi r^3 for open ends)."""
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
    L = path.length; closed = is_closed(path)
    if method == "pipe":
        mk = BRepOffsetAPI_MakePipeShell(path.wrapped)
        if mode == "frenet": mk.SetMode(True)
        elif mode == "corrected": mk.SetMode(False)
        elif mode == "binormal":
            P = [path.position_at(i / 64) for i in range(64)]; o = sum(P, Vector()) / 64
            nrm = Vector()
            for i in range(64): nrm += (P[i] - o).cross(P[(i + 1) % 64] - o)
            nrm = nrm.normalized(); mk.SetMode(gp_Dir(nrm.X, nrm.Y, nrm.Z))
        p0, t0 = path.position_at(0), path.tangent_at(0)
        mk.Add(Wire.make_circle(r, Plane(origin=p0, z_dir=t0)).wrapped, False, False); mk.Build()
        if not mk.IsDone(): raise RuntimeError("pipe shell not built")
        mk.MakeSolid(); s = pos(Shape.cast(mk.Shape()) if not isinstance(Shape.cast(mk.Shape()), Compound) else Shape.cast(mk.Shape()).solids()[0])
        if not closed:
            s = s + Solid.make_sphere(r, Plane(origin=p0)) + Solid.make_sphere(r, Plane(origin=path.position_at(1)))
    else:
        n = max(8, int(L / (seg or r / 2))); P = [path.position_at(i / n) for i in range(n + (0 if closed else 1))]
        parts = [Solid.make_sphere(r, Plane(origin=p)) for p in P]
        for i in range(len(P) - (0 if closed else 1)):
            a, b = P[i], P[(i + 1) % len(P)]; d = b - a
            parts.append(Solid.make_cylinder(r, d.length, Plane(origin=a, z_dir=d)))
        s = parts[0].fuse(*parts[1:]).clean(); s = one(s)
    want = math.pi * r * r * L + (0 if closed else 4 / 3 * math.pi * r ** 3)
    chk = dict(method=method + ("/" + mode if method == "pipe" else ""), valid=bool(s.is_valid), solids=len(s.solids()),
               volume_mm3=round(s.volume, 1), expected_mm3=round(want, 1), ratio=round(s.volume / want, 4))
    chk["volume_check"] = volume_verdict(s.volume, want, 0.03); chk["ok"] = chk["valid"] and chk["solids"] == 1 and chk["volume_check"] == "PASS"
    return s, chk

def offset_solid(S, r):
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape
    from OCP.BRepOffset import BRepOffset_Skin
    from OCP.GeomAbs import GeomAbs_Arc
    mk = BRepOffsetAPI_MakeOffsetShape(); mk.PerformByJoin(S.wrapped, r, 1e-3, BRepOffset_Skin, False, False, GeomAbs_Arc)
    o = Shape.cast(mk.Shape())
    if isinstance(o, Solid): return pos(o)
    if o.solids(): return pos(o.solids()[0])
    sh = o if isinstance(o, Shell) else o.shells()[0]               # boxes come back as a closed shell
    return pos(Solid(sh))

def blend_classic(A, B, r, tube_method="pipe", mode="corrected"):
    """offset(A, r) & offset(B, r) - ball tube along the centre curve - A - B. Exact only for 90 deg wedges."""
    oA, oB = offset_solid(A, r), offset_solid(B, r)
    region = one(oA.intersect(oB)); tubes = []
    for w in crease_loops(oA, oB):
        P = [w.position_at(i / 300) for i in range(300)]
        path = Wire([Edge.make_spline(P, periodic=True)]) if is_closed(w) else w
        t, chk = ball_tube(path, r, tube_method, mode); tubes.append(chk); region = one(region.cut(t))
    region = one(one(region.cut(A)).cut(B))
    return [s for s in region.solids() if s.volume > 1.0], tubes

# ------------------------------------------------------------------ demo geometry + CLI
def tilt_demo(angle, rc=10.0, plate=(160.0, 120.0, 10.0), length=80.0):
    """Plate (top at z = 0) and a cylinder of radius rc whose axis is `angle` degrees above the plate, starting inside it."""
    a = math.radians(angle); ax = Vector(math.cos(a), 0, math.sin(a))
    P = Box(*plate, align=(Align.CENTER, Align.CENTER, Align.MAX))
    o = Vector(0, 0, -5.0) - ax * (rc / math.tan(a) + 2)
    C = Solid.make_cylinder(rc, length, Plane(origin=o, z_dir=ax))
    C = one(C.intersect(Box(400, 400, 400, align=(Align.CENTER, Align.CENTER, Align.MIN)).moved(Location((0, 0, -5)))))
    return pos(C), pos(P)

def tilt_truth(angle, r, rc=10.0, hs=(0.3, 0.2)):
    """Reference fillet volume for tilt_demo, independent of OCC: morphological closing of (plate + cylinder) by a ball
    of radius r on voxel grids (fillet = outside the body and outside every ball that fits), linearly extrapolated to
    zero voxel size from two grid sizes. Needs scipy. About 1-2 % accurate (90 deg: 544 vs exact 552 mm3 at r6)."""
    import numpy as np
    from scipy.ndimage import distance_transform_edt as edt
    a = math.radians(angle); ax = np.array([math.cos(a), 0, math.sin(a)]); out = []
    for h in hs:
        reach = r / math.tan(a / 2) + rc / math.sin(a) + 3 * r
        xs = np.arange(-reach - 5, reach + 5, h); ys = np.arange(-rc - 3 * r - 5, rc + 3 * r + 5, h); zs = np.arange(-3, 3 * r + 12, h)
        X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
        o = np.array([0, 0, -5.0]) - ax * (rc / math.tan(a) + 2)
        Px, Py, Pz = X - o[0], Y - o[1], Z - o[2]; sx = Px * ax[0] + Pz * ax[2]
        rad2 = (Px - sx * ax[0]) ** 2 + Py ** 2 + (Pz - sx * ax[2]) ** 2
        body = (Z <= 0) | ((rad2 <= rc * rc) & (sx >= 0) & (Z >= -5)); del Px, Py, Pz, sx, rad2, X, Y
        C = edt(~body, sampling=h) >= r
        fil = (~body) & ~(edt(~C, sampling=h) <= r); del C
        fil[:, :, -int(2 * r / h):] = False
        out.append(float(fil.sum()) * h ** 3); del fil, body
    (h0, v0), (h1, v1) = zip(hs, out)
    return v1 + (v1 - v0) * h1 / (h0 - h1)

def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Rolling-ball blend (fillet-equivalent) solid between two solids, fused and checked.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="tilted cylinder on a plate"); d.add_argument("--angle", type=float, default=45); d.add_argument("--r", type=float, default=6)
    d.add_argument("-o", "--out", default=None, help="output prefix (STEP + JSON), default runs/tilt<angle>_r<r> (runs/ is git-ignored)")
    d.add_argument("--no-reference", action="store_true", help="skip the voxel rolling-ball reference volume (scipy)")
    c = sub.add_parser("compare", help="tube / classic approaches on the demo (volume checks)"); c.add_argument("--angle", type=float, default=45); c.add_argument("--r", type=float, default=6)
    c.add_argument("--exact", type=float, default=None, help="reference fillet volume mm3 (e.g. from a voxel closing)")
    p = sub.add_parser("pair", help="blend two STEP solids (A, B), fuse, check; writes OUT.step + OUT.json")
    p.add_argument("a", help="STEP, solid A (e.g. the arm)"); p.add_argument("b", help="STEP, solid B (e.g. the plate)")
    p.add_argument("--r", type=float, default=6, help="blend radius (mm)")
    p.add_argument("--base", default=None, help="STEP to fuse into (default A + B)"); p.add_argument("-o", "--out", default="blend")
    p.add_argument("--loops", default=None, help="comma list of crease loop indices (default all)")
    p.add_argument("--path", default=None, help="STEP with the crease curve(s) to blend along instead of the computed section")
    a = ap.parse_args(argv); t0 = time.time(); rep = {}
    if getattr(a, "out", None) and os.path.dirname(a.out): os.makedirs(os.path.dirname(a.out), exist_ok=True)
    if a.cmd == "demo":
        out = a.out or os.path.join("runs", "tilt%g_r%g" % (a.angle, a.r)); os.makedirs(os.path.dirname(out), exist_ok=True)
        A, B = tilt_demo(a.angle); res = blend(A, B, a.r)
        part, rep = fuse_blend(A + B, res, out + ".step")
        if not a.no_reference:
            try:
                rep["rolling_ball_reference_mm3"] = round(tilt_truth(a.angle, a.r), 1)
                rep["ratio_to_reference"] = round(rep["added_mm3"] / rep["rolling_ball_reference_mm3"], 4)
            except ImportError: pass
    elif a.cmd == "compare":
        A, B = tilt_demo(a.angle); rep = compare(A, B, a.r, a.angle, a.exact)
    else:
        A, B = one(import_step(a.a)), one(import_step(a.b))
        base = one(import_step(a.base)) if a.base else A + B
        paths = list(Wire.combine(import_step(a.path).edges(), tol=1e-3)) if a.path else None
        res = blend(A, B, a.r, paths=paths, loops=[int(x) for x in a.loops.split(",")] if a.loops else None)
        part, rep = fuse_blend(base, res, a.out + ".step"); out = a.out
    rep.update(seconds=round(time.time() - t0, 1), peak_rss_mb=round(peak_mb()))
    if a.cmd != "compare":
        rep["loops"] = res.loops; rep["notes"] = res.notes
        json.dump(rep, open(out + ".json", "w"), indent=1)
    print(json.dumps(rep, default=str))
    return 0 if rep.get("ok", True) else 1

def compare(A, B, r, angle, exact=None, log=print):
    """Run the alternatives on one case: tubes along the ball-centre curve, classic offset blend, section-loft blend.
    exact: reference fillet volume (default: tilt_truth voxel closing)."""
    rows = []
    res = blend(A, B, r, log=log)
    smp, _ = trace(crease_loops(A, B)[0], A, B, r, log=log)             # true ball centres for the tube tests
    P = [s["c"] for s in smp]; path = Wire([Edge.make_spline(P, periodic=True)])
    rows.append(dict(what="ball-centre curve", length=round(path.length, 1), min_turn_radius=round(centre_min_radius(smp, True), 2)))
    for meth, mode in (("pipe", "corrected"), ("pipe", "frenet"), ("pipe", "binormal"), ("capsules", None)):
        t1 = time.time()
        try: _, chk = ball_tube(path, r, meth, mode or "corrected")
        except Exception as ex: chk = dict(method=meth + ("/" + mode if mode else ""), error=str(ex)[:120], ok=False)
        chk["seconds"] = round(time.time() - t1, 1); chk["what"] = "tube"; rows.append(chk); log("  tube", chk)
    exact = exact or tilt_truth(angle, r)
    for tm, mode in (("pipe", "corrected"),):
        t1 = time.time()
        try:
            pcs, tubes = blend_classic(A, B, r, tm, mode); v = sum(p.volume for p in pcs)
            row = dict(what="classic offset blend", method=tm + "/" + mode, pieces=len(pcs), valid=all(p.is_valid for p in pcs),
                       volume_mm3=round(v, 1), expected_mm3=round(exact, 1), ratio=round(v / exact, 4), volume_check=volume_verdict(v, exact),
                       tubes=[t["volume_check"] for t in tubes])
        except Exception as ex: row = dict(what="classic offset blend", method=tm + "/" + mode, error=str(ex)[:120])
        row["seconds"] = round(time.time() - t1, 1); rows.append(row); log("  classic", row)
    t1 = time.time(); part, rep = fuse_blend(A + B, res)
    rows.append(dict(what="section-loft blend (this tool)", valid=rep["valid"], solids=rep["solids"], volume_mm3=rep["added_mm3"],
                     expected_mm3=round(exact, 1), ratio=round(rep["added_mm3"] / exact, 4), volume_check=volume_verdict(rep["added_mm3"], exact),
                     seconds=round(res.seconds + time.time() - t1, 1)))
    return dict(angle=angle, r=r, rows=rows)

if __name__ == "__main__":
    raise SystemExit(main())
