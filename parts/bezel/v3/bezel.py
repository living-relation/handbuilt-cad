"""Gauge-cluster bezel, hand-built v3 (build123d). Frame: bezel/frame_hb.json (plate top face = z0, straight back edge along Y at x~25).
v3 vs v2: nose boss removed; front rim bead with rising ends + end walls; stepped front skirt (drop, ledge, outer lip);
back wall follows the scan's lower middle; hood posts; gauge collars + ribs under the plate; turn-signal housings + arrow windows;
snap tabs with rounded ends and hooks."""
import math
from build123d import *
from bezel_outline import OUTLINE, WINDOWS

# ---- parameters (mm) ----
PLATE_T      = 2.7
GAUGE_PITCH  = 101.95
GAUGE_Y      = 203.07
CENTRE_GAUGE = dict(x=79.0, d=103.4)
SIDE_GAUGE   = dict(x=73.1, d=89.6)
OPEN_FILLET  = 1.0
SMALL_HOLES  = [((120.6, 134.1), 9.0), ((119.9, 271.7), 9.0)]       # confirmed real by Daniel
WINDOW_R     = 2.5
# back wall + hood
WALL_X       = (24.5, 27.0)
WALL_Y       = (13.9, 392.0)
WALL_TOP     = 33.0
# wall top in the middle (y, z) - measured on the scan at x=25.75; full height outside y 64..344
WALL_PROFILE = [(64, 29.5), (66, 17.0), (132, 15.5), (150, 16.0), (158, 12.8), (172, 11.5), (180, 8.0), (186, 8.0), (192, 14.8),
                (204, 14.5), (216, 7.0), (234, 4.0), (246, 8.4), (264, 9.0), (276, 10.8), (294, 13.8), (312, 15.4), (336, 16.0), (344, 29.5)]
HOOD         = dict(x=(5.0, 27.0), y=(3.0, 402.0), z=(30.0, 33.0))
POSTS        = [dict(x=(20.5, 25.0), y=(130.0, 170.0)), dict(x=(20.5, 25.0), y=(225.0, 265.0))]   # hood supports behind the wall
# curved front edge
RIM_END_X    = [(0, 36.0), (32, 35.0), (40, 33.5), (48, 30.2), (56, 26.5), (64, 23.0), (72, 19.4), (80, 16.5), (88, 13.0), (96, 11.3), (104, 10.3), (112, 9.0), (120, 8.1), (200, 8.1)]  # end walls slope down with x
RIM_T        = 1.5            # bead on the plate edge
RIM_TOP      = [(0, 33.0), (14, 33.0), (20, 31.7), (40, 16.6), (60, 11.5), (80, 9.8), (100, 8.3), (120, 6.9), (140, 6.1), (160, 5.7),
                (200, 5.5), (240, 5.8), (280, 5.8), (320, 4.8), (340, 6.9), (360, 13.0), (380, 27.5), (392, 33.0), (410, 33.0)]
SKIRT_T      = 2.0            # drop from the plate down to the ledge
LEDGE        = dict(out=6.0, z=(-9.8, -8.0))      # ledge reaches this far outside the plate edge
LIP          = dict(t=1.8, z=(-10.0, -4.0))        # outer lip at the ledge edge
CLIPS        = [dict(y=102.5, w=14.0), dict(y=202.2, w=14.0), dict(y=302.6, w=14.0)]
CLIP_T       = 2.2
CLIP_Z       = (-25.5, -9.0)
CLIP_END_R   = 5.0            # rounded tab end
HOOK         = dict(h=3.0, out=1.5)   # wedge on the outside of each tab near the bottom
# under the plate
COLLAR       = dict(inset=2.0, out=1.0, z=-8.0)    # tube under each gauge opening: r from R-inset to R+out
RIBS         = [dict(x=40.5, y=(140.0, 166.0)), dict(x=105.0, y=(140.0, 166.0)), dict(x=40.5, y=(240.0, 266.0)), dict(x=105.0, y=(240.0, 266.0))]
RIB_T, RIB_Z = 1.5, -6.0
SIG_HOUSINGS = [dict(x=(113.0, 131.0), y=(144.0, 161.0), arrow=-1), dict(x=(112.0, 133.0), y=(262.0, 279.0), arrow=+1)]
SIG_WALL, SIG_Z = 1.2, -5.0
ARROW        = dict(head_w=10.0, head_l=5.5, stem_w=4.0, stem_l=5.0)   # turn-signal arrow windows, pointing +/-Y

LOG = []
def log(*a):
    print(*a, flush=True); LOG.append(" ".join(str(x) for x in a))

def poly_face(pts, z=0):
    return make_face(Polyline(*[(x, y, z) for x, y in pts], close=True))

def outline_face(off=0.0):
    w = Wire([Spline(*[(x, y, 0) for x, y in OUTLINE] + [(OUTLINE[0][0], OUTLINE[0][1], 0)])])
    f = make_face(w)
    if off == 0: return f
    r = offset(f, amount=off)
    return r.faces()[0]

def yz_prism(pts, x0, x1):
    """Polygon in the YZ plane, extruded along +X from x0 to x1."""
    f = make_face(Polyline(*[(x0, y, z) for y, z in pts], close=True))
    return extrude(f, amount=x1 - x0, dir=(1, 0, 0))

def front_only(f, x_min=40.0):
    return f - Box(x_min + 50, 1000, 10, align=(Align.MAX, Align.CENTER, Align.CENTER)).translate((x_min, 200, 0))

def _one(x):
    if isinstance(x, ShapeList):
        x = list(x)
        return x[0] if len(x) == 1 else Compound(x)
    return x

def join(part, tool, name):
    tool = _one(tool)
    r = part.fuse(tool).clean()
    ok = r.is_valid and len(r.solids()) == 1 and r.volume > part.volume - 1
    log(f"  +{name:14s} vol {tool.volume:8.0f}  -> solids {len(r.solids())} valid {r.is_valid} {'OK' if ok else 'SKIPPED'}")
    return r if ok else part

def cut(part, tool, name):
    tool = _one(tool)
    r = part.cut(tool).clean()
    ok = r.is_valid and len(r.solids()) == 1 and r.volume < part.volume + 1
    log(f"  -{name:14s} -> solids {len(r.solids())} valid {r.is_valid} {'OK' if ok else 'SKIPPED'}")
    return r if ok else part

def arrow_pts(cx, cy, sgn):
    a = ARROW; tip = cy + sgn * (a["head_l"] + a["stem_l"]) / 2; base = tip - sgn * a["head_l"]; tail = base - sgn * a["stem_l"]
    return [(cx, tip), (cx + a["head_w"] / 2, base), (cx + a["stem_w"] / 2, base), (cx + a["stem_w"] / 2, tail),
            (cx - a["stem_w"] / 2, tail), (cx - a["stem_w"] / 2, base), (cx - a["head_w"] / 2, base)]

def build():
    of = outline_face()
    part = extrude(of, amount=PLATE_T, dir=(0, 0, -1)); log("plate", round(part.volume))
    # back wall, lowered in the middle to the scan's profile, posts + hood on top
    wall = Box(WALL_X[1] - WALL_X[0], WALL_Y[1] - WALL_Y[0], WALL_TOP + PLATE_T, align=Align.MIN).translate((WALL_X[0], WALL_Y[0], -PLATE_T))
    wall = wall.cut(yz_prism(WALL_PROFILE + [(344, 40), (64, 40)], WALL_X[0] - 1, WALL_X[1] + 1)).clean()
    part = join(part, wall, "back wall")
    for i, p in enumerate(POSTS):
        top = min(z for y, z in WALL_PROFILE if p["y"][0] - 10 <= y <= p["y"][1] + 10)
        post = Box(p["x"][1] - p["x"][0], p["y"][1] - p["y"][0], HOOD["z"][0] + 0.5 - (top - 1), align=Align.MIN).translate((p["x"][0], p["y"][0], top - 1))
        part = join(part, post, f"hood post {i+1}")
    hood = Box(HOOD["x"][1] - HOOD["x"][0], HOOD["y"][1] - HOOD["y"][0], HOOD["z"][1] - HOOD["z"][0], align=Align.MIN).translate((HOOD["x"][0], HOOD["y"][0], HOOD["z"][0]))
    part = join(part, hood, "hood")
    # front rim bead on the plate edge, rising at both ends into the end walls
    band = front_only(of - outline_face(-RIM_T), x_min=26.0)
    rim = extrude(band, amount=40).translate((0, 0, -PLATE_T + 0.5))
    rim = _one(rim.intersect(yz_prism([(y, z) for y, z in RIM_TOP] + [(410, -5), (0, -5)], 0, 200)))
    xz = make_face(Polyline(*[(x, -10, z) for x, z in RIM_END_X] + [(200, -10, -5), (0, -10, -5)], close=True))
    rim = _one(rim.intersect(extrude(xz, amount=430, dir=(0, 1, 0))))
    part = join(part, rim, "front rim")
    # stepped skirt: drop inside the edge, ledge outward, outer lip
    drop = extrude(front_only(of - outline_face(-SKIRT_T)), amount=9.5 + 0.5).translate((0, 0, -9.5))
    part = join(part, drop, "skirt drop")
    outer = outline_face(LEDGE["out"])
    ledge = extrude(front_only(outer - outline_face(-SKIRT_T + 0.5)), amount=LEDGE["z"][1] - LEDGE["z"][0]).translate((0, 0, LEDGE["z"][0]))
    ledge = ledge.intersect(Box(400, WALL_Y[1] - WALL_Y[0] - 40, 50, align=(Align.MIN, Align.MIN, Align.CENTER)).translate((0, WALL_Y[0] + 20, 0)))
    part = join(part, ledge, "skirt ledge")
    lip = extrude(front_only(outer - outline_face(LEDGE["out"] - LIP["t"])), amount=LIP["z"][1] - LIP["z"][0]).translate((0, 0, LIP["z"][0]))
    lip = lip.intersect(Box(400, WALL_Y[1] - WALL_Y[0] - 40, 50, align=(Align.MIN, Align.MIN, Align.CENTER)).translate((0, WALL_Y[0] + 20, 0)))
    part = join(part, lip, "skirt lip")
    # snap tabs hanging from the lip, rounded ends, small hook outward
    lip_mid = outline_face(LEDGE["out"] - LIP["t"] / 2).outer_wire()
    for i, c in enumerate(CLIPS):
        # point on the lip centre-line at this y, on the curved side, and its tangent
        best = None
        for k in range(400):
            t = k / 400; p = lip_mid.position_at(t)
            if p.X > 80 and (best is None or abs(p.Y - c["y"]) < abs(best[1].Y - c["y"])): best = (t, p)
        t, p = best; tg = lip_mid.tangent_at(t); ang = math.degrees(math.atan2(tg.Y, tg.X))
        prof = Rectangle(c["w"], CLIP_Z[1] - CLIP_Z[0])      # in XY, then stood up
        tab = extrude(prof, amount=CLIP_T / 2, both=True)
        try:
            ed = tab.edges().filter_by(Axis.Z).sort_by(Axis.Y)[:2]
            tab = tab.fillet(CLIP_END_R, ed)
        except Exception as ex: log("   tab end fillet skipped", ex)
        hook = extrude(make_face(Polyline((-c["w"] / 2 + 1, 0, 0), (c["w"] / 2 - 1, 0, 0), (c["w"] / 2 - 1, HOOK["h"], 0), (-c["w"] / 2 + 1, HOOK["h"], 0), close=True)), amount=HOOK["out"])
        hook = hook.translate((0, -(CLIP_Z[1] - CLIP_Z[0]) / 2 + 3.0, CLIP_T / 2 - 0.3))
        tab = tab.fuse(hook).clean()
        # local: X along the lip, Y = down/up, Z = outward normal  ->  world
        tab = tab.rotate(Axis.X, 90)                       # Y(up) -> Z, Z(outward) -> -Y
        tab = tab.rotate(Axis.Z, ang).translate((p.X, p.Y, (CLIP_Z[0] + CLIP_Z[1]) / 2))
        # make sure the hook points away from the part centre
        part = join(part, tab, f"clip {i+1}")
    # gauge collars + ribs under the plate
    gauges = [(CENTRE_GAUGE["x"], GAUGE_Y, CENTRE_GAUGE["d"])] + [(SIDE_GAUGE["x"], GAUGE_Y + k * GAUGE_PITCH, SIDE_GAUGE["d"]) for k in (-1, 1)]
    for i, (x, y, d) in enumerate(gauges):
        h = -COLLAR["z"] - PLATE_T + 0.5
        col = Pos(x, y, COLLAR["z"]) * (Cylinder(d / 2 + COLLAR["out"], h, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Cylinder(d / 2 - COLLAR["inset"], h, align=(Align.CENTER, Align.CENTER, Align.MIN)))
        part = join(part, col, f"collar {i+1}")
    for i, r in enumerate(RIBS):
        rib = Box(RIB_T, r["y"][1] - r["y"][0], -RIB_Z - PLATE_T + 0.5, align=(Align.CENTER, Align.MIN, Align.MIN)).translate((r["x"], r["y"][0], RIB_Z))
        part = join(part, rib, f"rib {i+1}")
    for i, h in enumerate(SIG_HOUSINGS):
        bx = Box(h["x"][1] - h["x"][0], h["y"][1] - h["y"][0], -SIG_Z - PLATE_T + 0.5, align=Align.MIN).translate((h["x"][0], h["y"][0], SIG_Z))
        inner = Box(h["x"][1] - h["x"][0] - 2 * SIG_WALL, h["y"][1] - h["y"][0] - 2 * SIG_WALL, 20, align=(Align.MIN, Align.MIN, Align.MAX)).translate((h["x"][0] + SIG_WALL, h["y"][0] + SIG_WALL, -PLATE_T))
        part = join(part, bx - inner, f"signal housing {i+1}")
    # ---- cuts ----
    for i, (x, y, d) in enumerate(gauges):
        part = cut(part, Pos(x, y, -30) * Cylinder(d / 2 - COLLAR["inset"], 60, align=(Align.CENTER, Align.CENTER, Align.MIN)), f"gauge {i+1} bore")
        part = cut(part, Pos(x, y, -PLATE_T - 0.01) * Cylinder(d / 2, 20, align=(Align.CENTER, Align.CENTER, Align.MIN)), f"gauge {i+1} open")
    for y0, y1 in []: pass
    for (x, y), d in SMALL_HOLES:
        part = cut(part, Pos(x, y, -20) * Cylinder(d / 2, 40, align=(Align.CENTER, Align.CENTER, Align.MIN)), f"hole d{d}")
    for i, w in enumerate(WINDOWS):
        f = poly_face(w)
        try: f = fillet(f.vertices(), WINDOW_R)
        except Exception: pass
        part = cut(part, extrude(f.translate((0, 0, -20)), amount=40), f"end window {i+1}")
    for i, h in enumerate(SIG_HOUSINGS):
        cx, cy = (h["x"][0] + h["x"][1]) / 2, (h["y"][0] + h["y"][1]) / 2
        part = cut(part, extrude(poly_face(arrow_pts(cx, cy, h["arrow"]), z=-10), amount=20), f"arrow {i+1}")
    try:
        es = [e for e in part.edges() if e.geom_type == GeomType.CIRCLE and abs(e.center().Z) < 0.01 and e.radius > 40]
        p2 = part.fillet(OPEN_FILLET, es)
        if p2.is_valid and len(p2.solids()) == 1: part = p2; log("  gauge top-edge fillet OK")
    except Exception as ex: log("  gauge fillet skipped:", ex)
    return part

if __name__ == "__main__":
    import sys, time
    t = time.time(); p = build()
    log("RESULT valid", p.is_valid, "solids", len(p.solids()), "vol %.0f" % p.volume, "bbox", p.bounding_box(), "%.0fs" % (time.time() - t))
    out = sys.argv[1] if len(sys.argv) > 1 else "bezel"
    export_step(p, out + ".step"); export_stl(p, out + ".stl", tolerance=0.02, angular_tolerance=0.1)
    open(out + "_build.log", "w").write("\n".join(LOG) + "\n")
