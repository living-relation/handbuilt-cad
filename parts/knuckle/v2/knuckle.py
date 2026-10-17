"""Rear knuckle - hand-built parametric solid (build123d).

Frame: Fairsolid run 'knuckle' frame, then frame_hb.json (rigid: Z = hub axis, Z=0 on the hub bottom face).
Exact primitives: hub (revolved), hub bore steps, the three eyes (tubes), every hole.
Cast webs/arms: clean prisms from smoothed silhouettes (knuckle_profiles.py), intersected per region.
"""
import math
from build123d import *
from knuckle_profiles import PROFILES
from knuckle_sections import SECTIONS

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
    ((-145.5, 99.4), 14.5, -30.0, 25.0),   # lower arm, outer
    ((-78.3, 95.8), 14.5, -30.0, 25.0),    # lower arm, inner
]

EYES = {  # centre, axis direction, outside dia, bore dia, length
    "left_eye":  dict(c=(-79.15, 86.0, 83.0), axis=(1, 0, 0), od=46.0, bore=35.0, length=26.0),
    "right_eye": dict(c=(65.9, 73.9, 112.6), axis=(math.cos(math.radians(13.6)), 0, -math.sin(math.radians(13.6))), od=46.5, bore=35.5, length=26.0),
    "top_eye":   dict(c=(-6.6, 138.1, 129.0), axis=(-math.sin(math.radians(8.7)), 0, math.cos(math.radians(8.7))), od=52.0, bore=40.0, length=40.0),
}

SMOOTH_LOFTS    = ("body",)   # smooth loft; the arms use ruled bands (their sections change too fast)
LOFT_CHUNK      = 8        # stations per ruled-loft chunk (build robustness only)

# ------------------------------------------------------------------ helpers
def _plane(ax, lo, hi):
    if ax == "z": return Plane(origin=(0, 0, lo[2]), x_dir=(1, 0, 0), z_dir=(0, 0, 1)), hi[2] - lo[2]
    if ax == "x": return Plane(origin=(lo[0], 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)), hi[0] - lo[0]
    return Plane(origin=(0, hi[1], 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0)), hi[1] - lo[1]

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

def hull_piece(name):
    p = PROFILES[name]; lo, hi = p["box"]
    s = _prism("z", p["z"], lo, hi)
    s = _one(s.intersect(_prism("x", p["x"], lo, hi)))
    s = _one(s.intersect(_prism("y", p["y"], lo, hi)))
    return s

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

def build():
    r0, r1, r2 = HUB_OD_BOTTOM / 2, HUB_OD / 2, HUB_OD_TOP / 2
    part = revolve_profile([(0, 0), (r0, 0), (r1, HUB_LEADIN_H), (r1, HUB_FLARE_Z[0]), (r2, HUB_FLARE_Z[1]), (r2, HUB_TOP_Z), (0, HUB_TOP_Z)])
    for name in PROFILES:                      # flange layers, arms, webs, ear: three-view prisms per region
        part = _one(part.fuse(hull_piece(name))); _log("+" + name, part)
    for e in EYES.values():
        part = _one(part.fuse(tube(e["c"], e["axis"], e["od"], e["length"]))); _log("+eye", part)
    part = part.clean()
    # --- cuts
    pts = []
    for z0, z1, d in BORE:
        pts += [(d / 2, z0), (d / 2, z1)]
    bore = revolve_profile([(0, BORE[0][0])] + pts + [(0, BORE[-1][1])])
    part = _one(part.cut(bore)); _log("-bore", part)
    for e in EYES.values():
        part = _one(part.cut(tube(e["c"], e["axis"], e["bore"], e["length"] + 20)))
    for (x, y) in FLANGE_HOLES:
        part = _one(part.cut(Solid.make_cylinder(FLANGE_HOLE_D / 2, FLANGE_HOLE_Z[1] - FLANGE_HOLE_Z[0], Plane(origin=(x, y, FLANGE_HOLE_Z[0])))))
    for (x, y), d, (z0, z1) in EAR_HOLES:
        part = _one(part.cut(Solid.make_cylinder(d / 2, z1 - z0, Plane(origin=(x, y, z0)))))
    for (y, z), d, x0, x1 in X_HOLES:
        part = _one(part.cut(Solid.make_cylinder(d / 2, x1 - x0, Plane(origin=(x0, y, z), z_dir=(1, 0, 0)))))
    return part.clean()

if __name__ == "__main__":
    import sys, time
    VERBOSE = True; t = time.time(); part = build()
    print("valid", part.is_valid, "solids", len(part.solids()), "bbox", part.bounding_box(), "%.0fs" % (time.time() - t))
    out = sys.argv[1] if len(sys.argv) > 1 else "knuckle"
    export_step(part, out + ".step"); export_stl(part, out + ".stl", tolerance=0.02, angular_tolerance=0.1)
