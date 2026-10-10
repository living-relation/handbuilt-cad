"""PCV breather tube (Audi OE 06H103223A, EA888 2.0T) - variant with one stock O-ring end and one
angled -10 AN male flare end.  Parametric: build(angle_deg).  All mm.

Stock end: identical to pcv_adapter/pcv_adapter.py v3 (two O-ring grooves, 21.8 land, 20.4 ball flare,
16.4 neck) from its face (z=0) up to NECK_START_Z.  Z = stock-end axis, part grows toward +Z.
Then a 16.4 OD tube bends toward +X by ANGLE about a centreline radius BEND_R, and a straight leg carries
a 1" hex, thread relief, 7/8-14 UNF thread (cosmetic: major-diameter cylinder) and 37 deg flare cone.

-10 AN male end (SAE AS4395 / MS33656 / AND10056 size 10, SAE J514 37-deg flare):
  thread 7/8-14 UNJF-3A (0.8750 in major, 14 TPI)          -> THREAD_D 22.225
  bore A .500 in (12.7)  - we keep 13.0 bore (nose wall 1.64 mm >= 1.5)
  nose / small cone dia D .641 in (16.28), cone max dia C .727 in (18.47), gauge dia B .686 in
  thread relief dia F .773 in (19.63), thread length J .625 in (15.9) nose -> relief
  hex 1 in A/F (Hoke Gyrolok 10AAN10 -10 AN adapter table)
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
THREAD_D    = 0.875 * IN            # 22.225, 7/8-14 UNF major dia (cosmetic thread)
THREAD_CH   = 1.0                   # 45 deg lead chamfer at the front of the thread
NOSE_D      = 0.641 * IN            # 16.28, flare nose dia (AS4395 D)
CONE_MAX_D  = 0.727 * IN            # 18.47, top of 37 deg flare cone (AS4395 C)
FLARE_ANG   = 37.0                  # deg from axis (74 included)
THREAD_LEN  = 0.625 * IN            # 15.9, nose face -> start of thread relief (AS4395 J)
RELIEF_D    = 0.773 * IN            # 19.63 (AS4395 F)
RELIEF_W    = 1.8                   # ~1 pitch
HEX_AF      = 1.0 * IN              # 25.4 across flats
HEX_LEN     = 7.0
HEX_CH      = 30.0                  # deg, standard nut-style chamfer on both hex faces
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

def leg_local():
    """AN leg in local coords: s=0 at bend exit, s=leg_len at the flare nose face."""
    rT, rR, rN, rC = THREAD_D / 2, RELIEF_D / 2, NOSE_D / 2, CONE_MAX_D / 2
    cone_ax = (rC - rN) / math.tan(math.radians(FLARE_ANG))
    L = HEX_LEN + RELIEF_W + THREAD_LEN
    s_rel = HEX_LEN
    s_thr = HEX_LEN + RELIEF_W
    s_cone = L - cone_ax
    # thread front chamfer from full major down to the cone top dia
    s_ch = s_cone - (rT - rC)          # 45 deg chamfer start
    pts = [(0, 0), (rR, 0), (rR, s_thr - 0.4), (rR + 0.4, s_thr), (rT, s_thr + (rT - rR - 0.4)),
           (rT, s_ch), (rC, s_cone), (rN, L), (0, L)]
    # (relief->thread uses a 45 deg ramp so the first thread is not a knife edge)
    face = Plane.XZ * Polygon(*[(r, s) for r, s in pts], align=None)
    body = revolve(face, axis=Axis.Z)
    # hex with 30 deg chamfered corners (intersection with double cone)
    hexp = extrude(RegularPolygon(HEX_AF / 2, 6, major_radius=False), amount=HEX_LEN)
    rc = HEX_AF / 2 / math.cos(math.radians(30))
    t = math.tan(math.radians(HEX_CH))
    d = (rc - HEX_AF / 2 * 0.98) * t  # chamfer reaches ~ the flats
    chp = Plane.XZ * Polygon((0, 0), (HEX_AF / 2 * 0.98, 0), (rc + 0.01, d), (rc + 0.01, HEX_LEN - d),
                             (HEX_AF / 2 * 0.98, HEX_LEN), (0, HEX_LEN), align=None)
    hexs = hexp & revolve(chp, axis=Axis.Z)
    # short tube under the hex start so the bend blends in
    return body + hexs, L

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
