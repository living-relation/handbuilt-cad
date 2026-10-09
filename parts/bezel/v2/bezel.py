"""Gauge-cluster bezel, hand-built v2 (build123d). Frame: bezel/frame_hb.json (plate top face = z0, straight edge along Y at x~25)."""
from build123d import *
from bezel_outline import OUTLINE, WINDOWS

# ---- parameters (mm) ----
PLATE_T      = 2.7            # face plate, z -PLATE_T..0
GAUGE_PITCH  = 101.95         # centre-to-centre of the 3 gauge openings (along Y)
GAUGE_Y      = 203.07         # centre gauge Y
CENTRE_GAUGE = dict(x=79.0, d=103.4)
SIDE_GAUGE   = dict(x=73.1, d=89.6)
OPEN_FILLET  = 1.0            # top-edge round on the gauge openings
SMALL_HOLES  = [((120.6, 134.1), 9.0), ((119.9, 271.7), 9.0)]
WINDOW_R     = 2.5            # corner radius of the two triangular end windows
WALL_X       = (24.5, 27.0)   # straight back wall (x), full height
WALL_Y       = (13.9, 392.0)
WALL_TOP     = 33.0
HOOD         = dict(x=(5.0, 27.0), y=(3.0, 402.0), z=(30.0, 33.0))   # visor lip on top of the wall
SKIRT_T      = 2.0            # curved outer skirt thickness
SKIRT_Z      = (-10.0, 3.0)
WALL_WINDOWS = [(62.0, 128.0), (172.0, 223.0), (267.0, 328.0)]   # Y spans of the 3 openings in the back wall
WALL_WIN_Z   = (17.0, 30.0)
CLIPS        = [dict(y=102.5, x_out=137.2, w=14.0), dict(y=202.2, x_out=150.4, w=23.4), dict(y=302.6, x_out=138.4, w=21.6)]  # snap tabs under the curved edge
CLIP_T       = 2.5
CLIP_Z       = (-26.0, -7.5)
NOSE         = dict(y=203.3, z=0.7, d=27.2, x=(1.7, 26.0))   # round boss through the back wall (function unknown)

def poly_face(pts):
    return make_face(Polyline(*[(x, y, 0) for x, y in pts], close=True))

def outline_face():
    try:
        w = Wire([Spline(*[(x, y, 0) for x, y in OUTLINE] + [(OUTLINE[0][0], OUTLINE[0][1], 0)], periodic=False)])
        return make_face(w)
    except Exception:
        return poly_face(OUTLINE)

def build():
    of = outline_face()
    plate = extrude(of, amount=PLATE_T, dir=(0, 0, -1))
    # curved skirt: band just inside the outline, away from the straight wall
    inner = offset(of, amount=-SKIRT_T)
    band = (of - inner)
    band = band - Pos(0, 0, 0) * Box(40, 1000, 1, align=(Align.MIN, Align.CENTER, Align.CENTER)).translate((-10, 200, 0))
    skirt = extrude(band, amount=SKIRT_Z[1] - SKIRT_Z[0]).translate((0, 0, SKIRT_Z[0]))
    wall = Box(WALL_X[1] - WALL_X[0], WALL_Y[1] - WALL_Y[0], WALL_TOP + PLATE_T, align=Align.MIN).translate((WALL_X[0], WALL_Y[0], -PLATE_T))
    hood = Box(HOOD["x"][1] - HOOD["x"][0], HOOD["y"][1] - HOOD["y"][0], HOOD["z"][1] - HOOD["z"][0], align=Align.MIN).translate((HOOD["x"][0], HOOD["y"][0], HOOD["z"][0]))
    import math
    tools = [skirt, wall, hood]
    for c in CLIPS:
        # tangent of the outline near this y
        pts = sorted([q for q in OUTLINE if q[0] > 80], key=lambda q: abs(q[1] - c["y"]))[:2]
        ang = math.degrees(math.atan2(pts[1][1] - pts[0][1], pts[1][0] - pts[0][0]))
        if ang < 0: ang += 180
        x_line = sum(q[0] for q in pts) / 2
        # ledge from inside the skirt out to the tab (the scan's tabs stand outboard of the plate edge), then the tab itself
        tab = Pos(c["x_out"] - CLIP_T / 2, c["y"], CLIP_Z[0]) * Box(CLIP_T, c["w"], -CLIP_Z[0] + SKIRT_Z[0] + 2.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
        L = c["x_out"] - x_line + SKIRT_T + 1.0
        ledge = Pos(c["x_out"] - L / 2, c["y"], SKIRT_Z[0]) * Box(L, c["w"], 2.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
        tools.append(tab.fuse(ledge).clean())
    nose = Pos(NOSE["x"][0], NOSE["y"], NOSE["z"]) * Cylinder(NOSE["d"] / 2, NOSE["x"][1] - NOSE["x"][0], rotation=(0, 90, 0), align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        nf = [f for f in nose.faces() if f.geom_type == GeomType.PLANE and f.center().X < NOSE["x"][0] + 0.1]
        nose = nose.fillet(NOSE["d"] / 2 - 2.0, nf[0].edges())
    except Exception as ex: print("nose fillet skipped:", ex)
    tools.append(nose)
    part = plate
    for t in tools:
        r = part.fuse(t).clean()
        if r.is_valid and len(r.solids()) == 1 and r.volume > part.volume: part = r
        else: print("join skipped", round(t.volume), "valid", r.is_valid, "solids", len(r.solids()))
    cuts = [Pos(CENTRE_GAUGE["x"], GAUGE_Y, -20) * Cylinder(CENTRE_GAUGE["d"] / 2, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))]
    for k in (-1, 1):
        cuts.append(Pos(SIDE_GAUGE["x"], GAUGE_Y + k * GAUGE_PITCH, -20) * Cylinder(SIDE_GAUGE["d"] / 2, 40, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    for y0, y1 in WALL_WINDOWS:
        cuts.append(Box(10, y1 - y0, WALL_WIN_Z[1] - WALL_WIN_Z[0], align=Align.MIN).translate((WALL_X[0] - 3, y0, WALL_WIN_Z[0])))
    for (x, y), d in SMALL_HOLES:
        cuts.append(Pos(x, y, -20) * Cylinder(d / 2, 40, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    for w in WINDOWS:
        f = poly_face(w)
        try: f = fillet(f.vertices(), WINDOW_R)
        except Exception: pass
        cuts.append(extrude(f.translate((0, 0, -20)), amount=40))
    part = part.cut(*cuts).clean()
    # round the top edges of the gauge openings
    try:
        es = [e for e in part.edges() if e.geom_type == GeomType.CIRCLE and abs(e.center().Z) < 0.01 and e.radius > 40]
        p2 = part.fillet(OPEN_FILLET, es)
        if p2.is_valid: part = p2
    except Exception as ex: print("opening fillet skipped:", ex)
    return part

if __name__ == "__main__":
    import sys, time
    t = time.time(); p = build()
    sol = p.solids(); print("valid", p.is_valid, "solids", len(sol), "vol %.0f" % p.volume, "bbox", p.bounding_box(), "%.0fs" % (time.time() - t))
    out = sys.argv[1] if len(sys.argv) > 1 else "bezel"
    export_step(p, out + ".step"); export_stl(p, out + ".stl", tolerance=0.02, angular_tolerance=0.1)
