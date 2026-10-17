"""PCV breather tube (Audi OE 06H103223A, EA888 2.0T) - variant with one stock O-ring end and one
angled -10 AN male flare end.  Parametric: build(angle_deg).  All mm.

Stock end: identical to pcv_adapter/pcv_adapter.py v3 (two O-ring grooves, 21.8 land, 20.4 ball flare,
16.4 neck) from its face (z=0) up to NECK_START_Z.  Z = stock-end axis, part grows toward +Z.
Then a 16.4 OD tube bends toward +X by ANGLE about a centreline radius BEND_R, and a straight leg carries
a plain 30-deg step to the thread relief land, a REAL helical 7/8-14 UNF-2A thread (v2, 2026-10-10;
v1 had a 1" hex and a cosmetic thread) and the 37 deg flare cone. No hex.

-10 AN male end (SAE AS4395 / MS33656 / AND10056 size 10, SAE J514 37-deg flare):
  thread 7/8-14 UNJF-3A (0.8750 in major, 14 TPI)          (2A form used below)
  bore A .500 in (12.7)  - we keep 13.0 bore (nose wall 1.64 mm >= 1.5)
  nose / small cone dia D .641 in (16.28), cone max dia C .727 in (18.47), gauge dia B .686 in
  thread relief dia F .773 in (19.63), thread length J .625 in (15.9) nose -> relief
  thread form: ASME B1.1 UNF-2A 7/8-14: major .8647-.8731, pitch dia .8216-.8267, UNR minor max .7874 in
Constraint: max Z of the whole part (measured along the stock-end axis from its face) <= 53.0.
"""
import math, os, sys
from build123d import *

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pcv_adapter"))
import pcv_adapter as stock  # v3 stock end geometry

IN = 25.4
# ---------------- parameters ----------------
BORE_D      = stock.BORE_D          # 13.0, constant through the whole part
TUBE_D      = stock.NECK_D          # 16.4, tube OD through the bend
BEND_START  = stock.NECK_START_Z    # 18.9, bend starts where the ball flare meets the neck
BEND_R      = 14.0                  # bend centreline radius (inside radius 5.8)
NOSE_D      = 0.641 * IN            # 16.28, flare nose dia (AS4395 D)
CONE_MAX_D  = 0.727 * IN            # 18.47, top of 37 deg flare cone (AS4395 C)
FLARE_ANG   = 37.0                  # deg from axis (74 included)
THREAD_LEN  = 0.625 * IN            # 15.9, nose face -> end of thread at the relief (AS4395 J)
RELIEF_D    = 0.773 * IN            # 19.63 (AS4395 F)
RELIEF_W    = 1.8                   # ~1 pitch
LEAD_TUBE   = 0.5                   # plain 16.4 tube after the bend before the relief ramp
# 7/8-14 UNF-2A external thread (ASME B1.1), real helical geometry
PITCH       = IN / 14               # 1.8143
MAJOR_D     = 0.8731 * IN           # 22.177, 2A major max (0.8647-0.8731 in)
PITCH_D     = 0.8267 * IN           # 20.998, 2A pitch dia max (0.8216-0.8267 in), reference
MINOR_D     = 0.7874 * IN           # 20.000, 2A UNR minor max (root)
THREAD_DEPTH = (MAJOR_D - MINOR_D) / 2   # 1.088
CREST_W     = PITCH / 8             # 0.227 flat crest (basic 60 deg form)
NOSE_BORE_CH = 0.3
MAX_AXIAL   = 53.0
# ---------------------------------------------

def stock_end():
    """Solid of revolution (no bore) of the stock O-ring end, z = 0 .. BEND_START."""
    P = lambda r, z: (r, 0, z)
    e = stock.end_edges(False)
    rL0 = stock.LEAD_LAND_D / 2 - stock.END_CHAMFER_RAD
    loop = [Line(P(0, 0), P(rL0, 0))] + e + [Line(P(stock.NECK_D / 2, BEND_START), P(0, BEND_START)),
                                              Line(P(0, BEND_START), P(0, 0))]
    return revolve(Face(Wire(loop)), axis=Axis.Z)

def bend(diam, ang, extra=0.0):
    c = Plane.XY.offset(BEND_START) * Circle(diam / 2)
    return revolve(c, axis=Axis((BEND_R, 0, BEND_START), (0, 1, 0)), revolution_arc=ang)

def thread_ridge(z0, length):
    """Real helical 7/8-14 UNF-2A ridge (60 deg form, flat crest P/8) swept along a helix, local Z axis."""
    h = THREAD_DEPTH; rr = MINOR_D / 2 - 0.1           # 0.1 overlap into the core
    w_root = CREST_W + 2 * (h + 0.1) * math.tan(math.radians(30))
    pr = Plane.XZ * Polygon((rr, -w_root / 2), (MAJOR_D / 2, -CREST_W / 2), (MAJOR_D / 2, CREST_W / 2),
                            (rr, w_root / 2), align=None)
    hx = Helix(PITCH, length, MINOR_D / 2 - 0.1, center=(0, 0, 0))
    hx = Wire([hx]) if not isinstance(hx, Wire) else hx
    # profile at helix start, in the plane containing the axis
    sp = hx.position_at(0)
    ang = math.degrees(math.atan2(sp.Y, sp.X))
    prof = Rot(0, 0, ang) * pr
    r = sweep(prof, path=hx, is_frenet=True)
    return Pos(0, 0, z0) * r

def leg_local():
    """AN leg in local coords: s=0 at bend exit, s=L at the flare nose face. No hex."""
    rTube, rR, rN, rC = TUBE_D / 2, RELIEF_D / 2, NOSE_D / 2, CONE_MAX_D / 2
    rMin, rMaj = MINOR_D / 2, MAJOR_D / 2
    cone_ax = (rC - rN) / math.tan(math.radians(FLARE_ANG))
    ramp = (rR - rTube) / math.tan(math.radians(30))   # 30 deg step up from tube to relief land
    s_rel = LEAD_TUBE + ramp
    s_thr = s_rel + RELIEF_W
    L = s_thr + THREAD_LEN
    s_cone = L - cone_ax
    s_fc = s_cone - (rMin - rC)                          # front 45 deg chamfer meets the minor dia
    pts = [(0, 0), (rTube, 0), (rTube, LEAD_TUBE), (rR, s_rel), (rR, s_thr), (rMin, s_thr),
           (rMin, s_fc), (rC, s_cone), (rN, L), (0, L)]
    base = revolve(Plane.XZ * Polygon(*pts, align=None), axis=Axis.Z)
    # envelope that trims the ridge: 45 deg runout at the relief end, 45 deg start chamfer at the front
    big = rMaj + 0.3
    env = [(0, s_thr), (rMin, s_thr), (big, s_thr + (big - rMin)), (big, s_cone - (big - rC)),
           (rC, s_cone), (0, s_cone)]
    envs = revolve(Plane.XZ * Polygon(*env, align=None), axis=Axis.Z)
    ridge = thread_ridge(s_thr - PITCH, (s_cone - s_thr) + 2 * PITCH) & envs
    return base + ridge, L

def build(angle_deg):
    a = math.radians(angle_deg)
    p1 = Vector(BEND_R * (1 - math.cos(a)), 0, BEND_START + BEND_R * math.sin(a))
    d = Vector(math.sin(a), 0, math.cos(a))
    leg_plane = Plane(origin=p1, x_dir=(math.cos(a), 0, -math.sin(a)), z_dir=d)
    leg, L = leg_local()
    outer = stock_end() + bend(TUBE_D, angle_deg) + leg_plane * leg
    # bore: straight + swept + leg, constant BORE_D
    bore = (Pos(0, 0, -1) * Cylinder(BORE_D / 2, BEND_START + 1, align=(Align.CENTER, Align.CENTER, Align.MIN))
            + bend(BORE_D, angle_deg)
            + leg_plane * Cylinder(BORE_D / 2, L + 1, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    part = outer - bore
    # stock-end bore chamfer (same as v3) and a light chamfer at the flare nose bore
    try:
        e0 = [e for e in part.edges().filter_by(GeomType.CIRCLE)
              if abs(e.position_at(0).Z) < 1e-4 and abs(e.radius - BORE_D / 2) < 1e-3]
        part = chamfer(e0, length=stock.BORE_CHAMFER)
    except Exception as ex:
        print("stock bore chamfer skipped:", ex)
    try:
        nose_c = p1 + d * L
        en = [e for e in part.edges().filter_by(GeomType.CIRCLE)
              if (e.arc_center - nose_c).length < 1e-3 and abs(e.radius - BORE_D / 2) < 1e-3]
        part = chamfer(en, length=NOSE_BORE_CH)
    except Exception as ex:
        print("nose bore chamfer skipped:", ex)
    # soft blend where the stock ball flare meets the tube (v3 had a 1.5 neck fillet)
    try:
        ring = [e for e in part.edges().filter_by(GeomType.CIRCLE)
                if abs(e.position_at(0).Z - BEND_START) < 1e-3 and abs(e.radius - TUBE_D / 2) < 1e-3]
        part = fillet(ring, radius=stock.NECK_FILLET)
    except Exception as ex:
        print("neck fillet skipped:", ex)
    if isinstance(part, Compound) or not hasattr(part, "volume"):
        pass
    return part, dict(leg_len=L, p1=p1, d=d, nose=p1 + d * L)

def report(angle_deg, part, info):
    bb = part.bounding_box(optimal=True)
    sol = part.solids()
    return dict(angle=angle_deg, valid=part.is_valid, n_solids=len(sol), volume=round(part.volume, 1),
                axial_len=round(bb.max.Z - bb.min.Z, 3), zmin=round(bb.min.Z, 3), zmax=round(bb.max.Z, 3),
                xspan=round(bb.max.X - bb.min.X, 2), leg_len=round(info["leg_len"], 2),
                nose_center=tuple(round(v, 2) for v in info["nose"]),
                mass_g_pa12=round(part.volume * 1.01e-3, 1), mass_g_6061=round(part.volume * 2.70e-3, 1))

if __name__ == "__main__":
    import json
    angs = [float(x) for x in sys.argv[1:]] or [45.0, 35.0]
    out = []
    for ang in angs:
        p, info = build(ang)
        r = report(ang, p, info)
        print(json.dumps(r))
        assert r["n_solids"] == 1 and r["valid"], "not one valid solid"
        assert r["zmax"] <= MAX_AXIAL + 1e-6, "too long"
        n = f"pcv_an10_{int(ang)}"
        export_step(p, os.path.join(HERE, n + ".step"))
        export_stl(p, os.path.join(HERE, n + ".stl"), tolerance=0.01, angular_tolerance=0.1)
        out.append(r)
    json.dump(out, open(os.path.join(HERE, "pcv_an10_report.json"), "w"), indent=1)
