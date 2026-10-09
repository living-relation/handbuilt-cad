"""Rear knuckle - hand-built parametric solid (build123d).

Frame: Fairsolid run 'knuckle' frame, then frame_hb.json (rigid: Z = hub axis, Z=0 on the hub bottom face).
Exact primitives: hub (revolved), hub bore steps, the three eyes (tubes), every hole.
Cast webs/arms: clean prisms from smoothed silhouettes (knuckle_profiles.py), intersected per region.
"""
import math
from build123d import *
from knuckle_profiles import PROFILES
SECTIONS = {}   # (loft stations not used in v3)

# ------------------------------------------------------------------ parameters (mm, deg)
HUB_OD          = 88.0     # bearing housing outside
HUB_OD_BOTTOM   = 84.0     # at the bottom face (lead-in)
HUB_LEADIN_H    = 7.0      # height of the bottom lead-in taper
HUB_FLARE_Z     = (26.0, 33.0)   # OD grows from HUB_OD to HUB_OD_TOP here
HUB_OD_TOP      = 94.0
HUB_TOP_Z       = 66.0     # flat top face of the hub collar inside the flange

TOP_OPENING_D   = 67.0     # opening through the flange top (cast, not round - simplified)

BORE = [  # (z_from, z_to, diameter) - stepped hub bore, bottom to top
    (-1.0, 10.5, 75.0),    # bottom counterbore
    (10.5, 13.5, 78.0),    # circlip groove
    (13.5, 46.0, 74.0),    # bearing seat
    (46.0, 50.5, 67.0),    # bearing stop lip
    (50.5, 58.5, 75.0),
    (58.5, 66.0, 79.2),    # top counterbore
    (66.0, 85.0, TOP_OPENING_D),  # opening through the flange above the hub
]

FLANGE_HOLE_D   = 10.5     # 4 bolt holes through the flange (Z)
FLANGE_HOLES    = [(-55.8, 18.1), (-47.5, -34.8), (53.7, -25.1), (51.8, 28.9)]
FLANGE_HOLE_Z   = (38.0, 82.0)
EAR_HOLES       = [((-101.5, 29.0), 10.0, (40.0, 64.0)),   # left ear
                   ((-41.0, -97.0), 9.0, (39.0, 70.0))]    # lower-left ear

X_HOLES = [  # ((y, z), diameter, x_from, x_to) - holes along X
    ((0.9, 72.5), 17.0, 38.0, 72.0),       # side boss
    ((-147.5, 96.2), 14.3, -30.0, 25.0),   # lower arm, outer (v4b: re-fitted on scan, was y-145.5 z99.4 d14.5)
    ((-79.0, 93.7), 14.0, -30.0, 25.0),    # lower arm, inner (v4b: re-fitted on scan, was y-78.3 z95.8 d14.5)
]

EYES = {  # centre, axis direction, outside dia, bore dia, length
    "left_eye":  dict(c=(-79.15, 86.0, 83.0), axis=(1, 0, 0), od=46.0, bore=35.0, length=26.0),
    "right_eye": dict(c=(65.9, 73.9, 112.6), axis=(math.cos(math.radians(13.6)), 0, -math.sin(math.radians(13.6))), od=46.5, bore=35.5, length=26.0),
    "top_eye":   dict(c=(-6.6, 138.1, 129.0), axis=(-math.sin(math.radians(8.7)), 0, math.cos(math.radians(8.7))), od=52.0, bore=40.0, length=40.0),
}

SMOOTH_LOFTS    = ("body",)   # smooth loft; the arms use ruled bands (their sections change too fast)
JOIN_ORDER = ["plate_low", "back_web", "left_ear", "plate_high", "low_arm_end", "low_arm", "top_arm", "left_web", "right_web"]
FUZZY           = 0.02     # boolean fuzzy tolerance (mm), build robustness only
LOFT_CHUNK      = 8        # stations per ruled-loft chunk (build robustness only)

# ------------------------------------------------------------------ helpers
PAD = {"z": 1.3, "x": 1.7, "y": 2.1}   # each view's prism runs a little past the region box (different amounts),
                                      # so no two prisms share an end face and regions overlap their neighbours

def _plane(ax, lo, hi):
    e = PAD[ax]
    if ax == "z": return Plane(origin=(0, 0, lo[2] - e), x_dir=(1, 0, 0), z_dir=(0, 0, 1)), hi[2] - lo[2] + 2 * e
    if ax == "x": return Plane(origin=(lo[0] - e, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)), hi[0] - lo[0] + 2 * e
    return Plane(origin=(0, hi[1] + e, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)), hi[1] - lo[1] + 2 * e

def _wire(pl, pts):
    n = len(pts)
    P = [pl.from_local_coords(Vector(u, v, 0)) for u, v in pts]
    return Wire([Edge.make_spline(P, periodic=True, parameters=[i / n for i in range(n + 1)])])

def _prism(ax, contours, lo, hi):
    from shapely.geometry import Polygon
    pl, depth = _plane(ax, lo, hi)
    loops = [c for c in contours if "pts" in c]           # round holes are cut later as exact holes
    polys = [Polygon(c["pts"]) for c in loops]
    depth_of = [sum(1 for j, q in enumerate(polys) if j != i and q.contains(p)) for i, p in enumerate(polys)]
    solids = []
    for i, c in enumerate(loops):
        if depth_of[i] % 2: continue
        inner = [_wire(pl, loops[j]["pts"]) for j in range(len(loops)) if depth_of[j] == depth_of[i] + 1 and polys[i].contains(polys[j])]
        f = Face(_wire(pl, c["pts"]), inner)
        solids.append(extrude(f, amount=depth, dir=pl.z_dir))
    out = solids[0]
    for s_ in solids[1:]: out = out.fuse(s_)
    return out

def _one(x):
    """Boolean results may come back as a list of solids; keep them together."""
    if isinstance(x, (list, ShapeList)):
        x = [y for y in x if y.volume > 1e-3] if len(x) > 1 else list(x)
        return x[0] if len(x) == 1 else Compound(x)
    return x

PAD_SETS = [(1.3, 1.7, 2.1), (0.9, 2.3, 1.6), (2.6, 1.1, 1.9), (1.9, 2.7, 0.8)]   # (z, x, y) overrun variants

def hull_piece(name):
    """Three-view prism: plan (Z) outline ∩ side (X) outline ∩ front (Y) outline, inside the region box.
    The kernel occasionally fails on a particular overrun combination, so a few variants are tried."""
    p = PROFILES[name]; lo, hi = p["box"]
    best = None
    for pz, px, py in ([(0.0, 0.0, 0.0)] if name.startswith("plate") else PAD_SETS):   # flange halves: as v3 (no overrun)
        PAD.update(z=pz, x=px, y=py)
        P = {ax: _prism(ax, p[ax], lo, hi) for ax in "zxy"}
        for order in (("z", "x", "y"), ("z", "y", "x"), ("x", "y", "z")):
            s = P[order[0]]
            for ax in order[1:]:
                try:
                    s = s.intersect(P[ax])
                except Exception:
                    s = None
                if s is None: break
                s = _one(s)
            if s is not None and s.solids():
                if s.is_valid and len(s.solids()) == 1: return s
                best = best or s
    return best

def loft_piece(name):
    """Loft through smoothed scan stations along one axis, trimmed by the region's plan outline."""
    d = SECTIONS[name]; lo, hi = d["box"]; ax = d["axis"]
    if ax == "y":   to3 = lambda L, u, v: Vector(u, L, v)      # stations in X-Z
    else:           to3 = lambda L, u, v: Vector(L, u, v)      # stations in Y-Z
    wires = []
    for L, pts in d["stations"]:
        n = len(pts)
        wires.append(Wire([Edge.make_spline([to3(L, u, v) for u, v in pts], periodic=True, parameters=[i / n for i in range(n + 1)])]))
    if name in SMOOTH_LOFTS:
        body = Solid.make_loft(wires, ruled=False)
        return Solid(body.wrapped.Reversed()) if body.volume < 0 else body
    try:
        body = Solid.make_loft(wires, ruled=True)
        body = Solid(body.wrapped.Reversed()) if body.volume < 0 else body
        if body.is_valid: return body
    except Exception:
        pass
    # ruled bands between neighbouring stations, sewn into one closed shell with flat end caps
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
    from OCP.TopoDS import TopoDS
    sew = BRepBuilderAPI_Sewing(1e-3)
    for w0, w1 in zip(wires[:-1], wires[1:]):
        band = Solid.make_loft([w0, w1], ruled=True)
        for f in band.faces():
            if f.geom_type != GeomType.PLANE: sew.Add(f.wrapped)
    sew.Add(Face(wires[0]).wrapped); sew.Add(Face(wires[-1]).wrapped)
    sew.Perform()
    shell = TopoDS.Shell(sew.SewedShape())
    from OCP.ShapeFix import ShapeFix_Solid
    fx = ShapeFix_Solid(BRepBuilderAPI_MakeSolid(shell).Solid()); fx.Perform()
    body = Solid(TopoDS.Solid(fx.Solid()))
    if body.volume < 0: body = Solid(body.wrapped.Reversed())
    return body

def plan_prism(name):
    p = PROFILES[name]; lo, hi = p["box"]
    return _prism("z", p["z"], lo, hi)

def revolve_profile(rz):
    """rz: list of (r, z) points of a closed half-section in the XZ plane, revolved about Z."""
    w = Wire.make_polygon([Vector(r, 0, z) for r, z in rz], close=True)
    return revolve(Face(w), axis=Axis.Z, revolution_arc=360)

def tube(c, axis, d, length):
    a = Vector(*axis).normalized(); base = Vector(*c) - a * (length / 2)
    return Solid.make_cylinder(d / 2, length, Plane(origin=base, z_dir=a))

# ------------------------------------------------------------------ build
def _log(tag, x):
    if VERBOSE: print("  %-28s solids=%d valid=%s" % (tag, len(x.solids()), x.is_valid), flush=True)

VERBOSE = False

def _fix(x):
    from OCP.ShapeFix import ShapeFix_Shape
    from build123d.topology.shape_core import Shape
    f = ShapeFix_Shape(x.wrapped); f.Perform(); return _one(Shape.cast(f.Shape()))

def _join(part, piece, name):
    """Fuse with a validity check; retry with a fuzzy fuse, then a shape fix; skip the piece if all fail."""
    for how in ("plain", "fuzzy", "fix"):
        try:
            if how == "plain": r = part.fuse(piece)
            elif how == "fuzzy": r = part.fuse(piece, tol=FUZZY)
            else: r = _fix(_one(part.fuse(piece, tol=FUZZY)))
            r = _one(r)
            va, vb, vr = part.volume, piece.volume, (r.volume if r is not None else 0)
            if r is not None and r.is_valid and len(r.solids()) <= len(part.solids()) and vr >= max(va, vb) - 1 and vr <= va + vb + 1:
                if VERBOSE: print("  +%-14s %-6s solids=%d valid=True" % (name, how, len(r.solids())), flush=True)
                return r
        except Exception as ex:
            pass
    if VERBOSE: print("  !%-14s skipped (no valid join)" % name, flush=True)
    return part

def _touches(a, b):
    return a.bounding_box().to_align_offset if False else True

def build():
    r0, r1, r2 = HUB_OD_BOTTOM / 2, HUB_OD / 2, HUB_OD_TOP / 2
    hub = revolve_profile([(0, 0), (r0, 0), (r1, HUB_LEADIN_H), (r1, HUB_FLARE_Z[0]), (r2, HUB_FLARE_Z[1]), (r2, HUB_TOP_Z), (0, HUB_TOP_Z)])
    part = hub.solids()[0]
    pieces = []
    for name in JOIN_ORDER:                      # three-view prisms per region (overlapping regions)
        piece = hull_piece(name)
        if piece is None or not piece.solids():
            if VERBOSE: print("  (empty region skipped)", name)
            continue
        if not piece.is_valid: piece = _fix(piece)
        pieces += [(name, s_) for s_ in piece.solids() if s_.volume > 5 and s_.is_valid]
    for n, e in EYES.items():
        pieces.append((n, tube(e["c"], e["axis"], e["od"], e["length"])))
    pending = pieces                           # join one at a time; a join must stay ONE valid solid.
    for _pass in range(3):                     # pieces that don't touch yet are retried after the others
        left = []
        for name, s_ in pending:
            r = _join(part, s_, name)
            if r is part: left.append((name, s_))
            part = r
        pending = left
        if not pending: break
    if VERBOSE and pending: print("  NOT JOINED:", [n for n, _ in pending])
    # --- cuts (all at once)
    cuts = []
    pts = []
    for z0, z1, d in BORE:
        pts += [(d / 2, z0), (d / 2, z1)]
    cuts.append(revolve_profile([(0, BORE[0][0])] + pts + [(0, BORE[-1][1])]))
    for e in EYES.values():
        cuts.append(tube(e["c"], e["axis"], e["bore"], e["length"] + 20))
    for (x, y) in FLANGE_HOLES:
        cuts.append(Solid.make_cylinder(FLANGE_HOLE_D / 2, FLANGE_HOLE_Z[1] - FLANGE_HOLE_Z[0], Plane(origin=(x, y, FLANGE_HOLE_Z[0]))))
    for (x, y), d, (z0, z1) in EAR_HOLES:
        cuts.append(Solid.make_cylinder(d / 2, z1 - z0, Plane(origin=(x, y, z0))))
    for (y, z), d, x0, x1 in X_HOLES:
        cuts.append(Solid.make_cylinder(d / 2, x1 - x0, Plane(origin=(x0, y, z), z_dir=(1, 0, 0))))
    part = _one(part.cut(*cuts)); _log("cut %d features" % len(cuts), part)
    return part

if __name__ == "__main__":
    import sys, time
    VERBOSE = True; t = time.time(); part = build()
    print("valid", part.is_valid, "solids", len(part.solids()), "bbox", part.bounding_box(), "%.0fs" % (time.time() - t))
    out = sys.argv[1] if len(sys.argv) > 1 else "knuckle"
    export_step(part, out + ".step"); export_stl(part, out + ".stl", tolerance=0.02, angular_tolerance=0.1)
