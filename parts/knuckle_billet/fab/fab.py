"""Fabricated ST185 RH rear knuckle concepts (geometry only; no FEA yet - owner approves shapes first).
usage: python fab.py A|B|C <outstem>
A: all-welded 4130 box upright (turned housing/eyes/bosses + closed 3 mm sheet box arms + plate gussets)
B: tube + plate: turned housing with 8 mm plate wing, round 4130 tube arms/ties, plate tongue
C: hybrid: welded 4130 core (housing, wing, tongue, ear webs) + bolt-on machined 7075 lower eye carrier (3 eyes, one piece)
Interface constants copied verbatim from ../knuckle_billet.py (OEM v4b)."""
import math, json, sys
from build123d import *
src = open(__file__.rsplit('/', 2)[0] + '/knuckle_billet.py').read().split("P = dict(")[0]
ns = {}; exec(src.replace('from build123d import *', ''), ns)
BORE, FLANGE_HOLES, FLANGE_HOLE_D, FLANGE_HOLE_Z = ns['BORE'], ns['FLANGE_HOLES'], ns['FLANGE_HOLE_D'], ns['FLANGE_HOLE_Z']
EAR_HOLES, X_HOLES, EYES = ns['EAR_HOLES'], ns['X_HOLES'], ns['EYES']; TONGUE_X = ns['TONGUE_X_OEM']; ABS_X = ns['ABS_FACE_X']
CON = sys.argv[1]; OUT = sys.argv[2]
V = lambda *a: Vector(*a)
def zc(r, z0, z1, x=0, y=0): return Pos(x, y, z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
def cyl(c, axis, d, L): return Plane(origin=V(*c), z_dir=V(*axis).normalized()) * Cylinder(d/2, L, align=(Align.CENTER, Align.CENTER, Align.MIN))
def tube_c(c, axis, od, L): return Plane(origin=V(*c), z_dir=V(*axis).normalized()) * Cylinder(od/2, L)
def frame(A, B, hint=(0, 0, 1)):
    A, B = V(*A), V(*B); x = (B - A).normalized(); h = V(*hint); n = (h - x * h.dot(x)).normalized()
    return Plane(origin=(A + B) * 0.5, x_dir=x, z_dir=n), (B - A).length
def aim(R, eye, extra=0.0):
    """point on the eye axis to aim a member at, shifted toward the far end so the member lands inside the eye length"""
    e = EYES[eye]; a = V(*e['axis']).normalized(); c = V(*e['c']); d = (c - V(*R)).normalized(); ct = d.dot(a)
    st = max(math.sqrt(max(1 - ct * ct, 1e-6)), 0.3); s = (e['od'] / 2) * ct / st * 0.5 + extra * (1 if ct >= 0 else -1)
    s = max(-e['length'] / 2 + 6, min(e['length'] / 2 - 6, s)); return tuple(c + a * s)
def boxm(A, B, w, h, t, hint=(0, 0, 1), c0=12.0, c1=26.0, r=4.0):
    """closed welded box member: 4 sheet walls t, outer long edges radiused r (press-braked), void stops c0/c1 short of the ends"""
    pl, L = frame(A, B, hint); o = Box(L, w, h)
    try: o = fillet(o.edges().filter_by(Axis.X), r)
    except Exception: pass
    i = Pos((c0 - c1) / 2, 0, 0) * Box(L - c0 - c1, w - 2 * t, h - 2 * t)
    return pl * o - pl * i
def rtube(A, B, od, t, c0=12.0, c1=26.0):
    pl, L = frame(A, B); o = pl * Rot(0, 90, 0) * Cylinder(od / 2, L)
    i = pl * Pos((c0 - c1) / 2, 0, 0) * Rot(0, 90, 0) * Cylinder(od / 2 - t, L - c0 - c1)
    return o - i
def hbar(A, B, w, h, wall=6.0, web=8.0, hint=(0, 0, 1), endc=26.0, r=6.0):
    """machined 7075 H-section arm, pocketed from both faces"""
    pl, L = frame(A, B, hint); bar = Box(L, w, h)
    try: bar = fillet(bar.edges().filter_by(Axis.X), r)
    except Exception: pass
    bar = pl * bar; pd = (h - web) / 2; plen = L - 2 * endc
    if plen > 16:
        for s in (1, -1):
            pk = extrude(Plane(origin=(0, 0, s * h / 2), z_dir=(0, 0, -s)) * RectangleRounded(plen, w - 2 * wall, 5.0), amount=pd)
            bar = bar - pl * pk
    return bar
def plate_xy(pts, z0, z1, r=8.0):
    p = extrude(Pos(0, 0, z0) * make_face(Polyline(*pts, close=True)), amount=z1 - z0)
    try: p = fillet(p.edges().filter_by(Axis.Z), r)
    except Exception: pass
    return p
def radial_web(ang_xy, pts_rz, t, r=5.0):
    """vertical plate in the radial plane at angle ang (deg), profile given as (r, z) points"""
    a = math.radians(ang_xy); pl = Plane(origin=(0, 0, 0), x_dir=(math.cos(a), math.sin(a), 0), z_dir=(math.sin(a), -math.cos(a), 0))
    p = pl * extrude(make_face(Polyline(*pts_rz, close=True)), amount=t / 2, both=True)
    try: p = fillet(p.edges().filter_by(lambda e: abs(V(*e.tangent_at(0.5)).dot(pl.z_dir)) > 0.99), r)
    except Exception: pass
    return p
def yz_plate(x0, x1, pts_yz, r=6.0):
    pl = Plane(origin=(x0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))
    p = pl * extrude(make_face(Polyline(*pts_yz, close=True)), amount=x1 - x0)
    try: p = fillet(p.edges().filter_by(Axis.X), r)
    except Exception: pass
    return p

parts = {}   # label -> (shape, material, process)
def add(label, shp, mat='4130', proc=''): parts[label] = (shp, mat, proc)

# ---------------- common welded steel core
add('housing', zc(44, 0, 66) + zc(56, 66, 82) + sum([zc(11.5, 66, 82, x, y) for x, y in FLANGE_HOLES], Part()), proc='turned 4130 bar, OD88 tube + r56 flange ring w/ 4 bolt bosses (16 thk); bore finish-machined AFTER welding')
for (x, y), d, (z0, z1) in EAR_HOLES:
    i = 1 if x < -90 else 2
    add(f'ear{i}_boss', zc(12, z0, z1, x, y), proc='turned 4130 boss OD24, reamed after welding')
    rb = math.hypot(x, y) - 11; ang = math.degrees(math.atan2(y, x))
    add(f'ear{i}_web', radial_web(ang, [(40, z0), (rb + 10, z0), (rb + 10, z1), (rb - 18, z1), (rb - 44, 80), (40, 80)], 8.0), proc='8 mm 4130 plate web, housing -> ear boss, top edge tapers into the wing')
(y, z), d, x0, x1 = X_HOLES[0]
add('abs_boss', cyl((x0, y, z), (1, 0, 0), 32.0, ABS_X - x0), proc='turned 4130 slug d32 (OEM ABS boss), face x=72 and 17 mm bore machined after welding')
# strut tongue: two 7 mm cheeks at the OEM clamp faces x=+/-15, 4 mm top/bottom plates, end plate, 2 crush sleeves
ty0, ty1, tz0, tz1 = -166.0, -40.0, 72.0, 116.0
xa, xb = TONGUE_X; ym, yl = (ty0 + ty1) / 2, ty1 - ty0; zm, zl = (tz0 + tz1) / 2, tz1 - tz0
tg = (Pos(xb - 3.5, ym, zm) * Box(7, yl, zl) + Pos(xa + 3.5, ym, zm) * Box(7, yl, zl) + Pos(0.5, ym, zm) * Box(4, yl, zl)
      + Pos((xa + xb) / 2, ym, tz0 + 2) * Box(xb - xa, yl, 4) + Pos((xa + xb) / 2, ym, tz1 - 2) * Box(xb - xa, yl, 4) + Pos((xa + xb) / 2, ty0 + 2.5, zm) * Box(xb - xa, 5, zl))
try: tg = fillet(tg.edges().filter_by(Axis.Y).filter_by(lambda e: abs(abs(e.center().X - 0.55) - 14.35) < 0.1 and abs(e.center().Z - 94) > 20), 3.0)
except Exception as ex: print('tongue fillet failed', ex)
for (yy, zz), dd, _, _ in X_HOLES[1:]: tg += cyl((xa, yy, zz), (1, 0, 0), dd + 10, xb - xa)
add('tongue', tg, proc='7 mm cheeks (OEM clamp faces x=-13.8/+14.9, faced after welding), 4 mm centre web, 4 mm caps, 5 mm end plate, 2 crush sleeves (d+10 OD)')
# tongue root: flares to |x|<=34 only where y > -60 (clamp bracket ends at y -67), plus a centre keel gusset under the tongue
add('tongue_root', plate_xy([(-13.8, -42), (-13.8, -58), (14.9, -58), (14.9, -42), (34, -40), (34, -30), (-34, -30), (-34, -40)], 72, 112, r=10.0)
    & Pos(0, 0, 92) * Box(80, 200, 40) - (Pos(0, -95, 116) * Rot(0, 90, 0) * Cylinder(60, 100)),   # sloped top: falls from the tongue cap to the flange
    proc='two 6 mm side gussets + cap, tongue root -> flange ring')
add('keel', yz_plate(-4, 4, [(-42, 6), (-42, 74), (-128, 74), (-112, 60)], r=8.0), proc='8 mm 4130 keel gusset under the tongue, housing OD -> tongue bottom cap')
WING = [(-92, 50), (-92, 14), (-68, -26), (-36, -52), (-14, -58), (14, -58), (40, -46), (54, -18), (54, 14), (82, 26), (82, 54), (46, 74), (-30, 72), (-60, 54)]
wz = (74.0, 82.0)
if CON == 'A': pass
else: add('wing', plate_xy(WING, *wz, r=10.0), proc='8 mm 4130 plate wing, laser cut, flush with the flange top (z 82)')

E = EYES; L_root, R_root, T_root = (-50, 38, 80), (46, 44, 84), (-5, 58, 80)
mat_arm = '4130'
if CON == 'A':
    add('wing', plate_xy(WING, 76, 82, r=10.0), proc='6 mm 4130 bottom closing plate of the box upright')
    add('arm_L', boxm(L_root, aim(L_root, 'left_eye'), 30, 52, 3.0), proc='closed box 30x52x3 4130 sheet (2 press-braked channels seam-welded)')
    add('arm_R', boxm(R_root, aim(R_root, 'right_eye'), 30, 48, 3.0), proc='closed box 30x48x3')
    add('arm_T', boxm(T_root, aim(T_root, 'top_eye', 4), 34, 48, 3.0, hint=(1, 0, 0)), proc='closed box 34x48x3 (trailing-arm leg)')
    add('tie_LT', boxm(aim(E['left_eye']['c'], 'top_eye', 2), aim(E['top_eye']['c'], 'left_eye'), 24, 36, 2.5, c0=26, c1=26), proc='closed box 24x36x2.5 tie, L eye -> trailing eye')
    add('tie_TR', boxm(aim(E['right_eye']['c'], 'top_eye', 2), aim(E['top_eye']['c'], 'right_eye'), 24, 36, 2.5, c0=26, c1=26), proc='closed box 24x36x2.5 tie, trailing eye -> R eye')
    add('gusset_LR', radial_web(90, [(56, 70), (100, 70), (118, 118), (60, 92)], 4.0), proc='4 mm centre shear web under the hub (driveshaft side clear)')
elif CON == 'B':
    add('arm_L', rtube(L_root, aim(L_root, 'left_eye'), 38.1, 3.05), proc='tube 1.50 x 0.120 4130 (38.1 x 3.05)')
    add('arm_R', rtube(R_root, aim(R_root, 'right_eye'), 38.1, 3.05), proc='tube 1.50 x 0.120')
    add('arm_T', rtube(T_root, aim(T_root, 'top_eye', 4), 38.1, 3.05), proc='tube 1.50 x 0.120 (trailing leg)')
    add('tie_LT', rtube(aim(E['left_eye']['c'], 'top_eye', 2), aim(E['top_eye']['c'], 'left_eye'), 25.4, 2.4, c0=26, c1=26), proc='tube 1.00 x 0.095 tie')
    add('tie_TR', rtube(aim(E['right_eye']['c'], 'top_eye', 2), aim(E['top_eye']['c'], 'right_eye'), 25.4, 2.4, c0=26, c1=26), proc='tube 1.00 x 0.095 tie')
    add('brace_L', rtube((-80, 20, 80), aim((-80, 20, 80), 'left_eye'), 25.4, 2.4, c0=10), proc='tube 1.00 x 0.095 brace from wing tip')
    add('brace_R', rtube((70, 20, 82), aim((70, 20, 82), 'right_eye'), 25.4, 2.4, c0=10), proc='tube 1.00 x 0.095 brace from wing tip')
elif CON == 'C':
    # bolt-on 7075 lower carrier: base pad on the wing top (z 82-96) + 3 H arms + ties + the 3 eyes, one machined piece
    pad = plate_xy([(-70, 30), (-30, 30), (-10, 46), (10, 46), (30, 30), (64, 30), (64, 62), (30, 74), (-30, 74), (-70, 62)], 82, 96, r=10.0)
    car = pad + hbar((-50, 50, 89), aim((-50, 50, 89), 'left_eye'), 30, 46) + hbar((45, 50, 89), aim((45, 50, 89), 'right_eye'), 30, 42) \
        + hbar((-5, 60, 89), aim((-5, 60, 89), 'top_eye', 4), 34, 42, hint=(1, 0, 0)) \
        + hbar(aim(E['left_eye']['c'], 'top_eye', 2), aim(E['top_eye']['c'], 'left_eye'), 22, 32, wall=5.0, endc=30) + hbar(aim(E['right_eye']['c'], 'top_eye', 2), aim(E['top_eye']['c'], 'right_eye'), 22, 32, wall=5.0, endc=30)
    for k, v in E.items(): car += tube_c(v['c'], v['axis'], v['od'], v['length'])
    BOLTS_C = [(-60, 40), (-44, 56), (-20, 64), (20, 64), (54, 40), (30, 56)]
    for x, y in BOLTS_C: car -= zc(5.25, 60, 100, x, y) + zc(9, 96 - 0.01, 110, x, y) - zc(9, 70, 95.99, x, y)
    add('carrier_7075', car, mat='7075', proc='one-piece 7075-T651 lower eye carrier, 3-axis from 2.25" plate + angle-block for the two tilted eyes; 6x M10 12.9 into the wing (M10 weld nuts / tapped 8 mm wing + backing bar)')
    add('wing_pads', sum([zc(10, 64, 74, x, y) for x, y in BOLTS_C], Part()), proc='6 weld nuts / bosses under the wing for the carrier bolts')
if CON != 'C':
    for k, v in E.items(): add(k, tube_c(v['c'], v['axis'], v['od'], v['length']), proc=f"turned 4130 eye OD{v['od']} (bushing bore {v['bore']} finish-bored after welding)")

def cuts(p, eye_trim=True):
    p -= zc(45, 66, 266)
    for z0, z1, d in BORE: p -= zc(d / 2, z0, z1)
    for x, y in FLANGE_HOLES: p -= zc(FLANGE_HOLE_D / 2, FLANGE_HOLE_Z[0], FLANGE_HOLE_Z[1], x, y)
    for (x, y), d, (z0, z1) in EAR_HOLES: p -= zc(d / 2, z0 - 1, z1 + 1, x, y)
    for (y, z), d, x0, x1 in X_HOLES: p -= cyl((x0, y, z), (1, 0, 0), d, x1 - x0)
    for k, v in EYES.items():
        a = V(*v['axis']).normalized(); c = V(*v['c']) - a * (v['length'] / 2 + 30); p -= cyl(tuple(c), tuple(a), v['bore'], v['length'] + 60)
        if eye_trim:
            for s in (1, -1):
                o = V(*v['c']) + a * s * (v['length'] / 2); p -= Plane(origin=o, z_dir=a * s) * Cylinder(v['od'] / 2 + 6, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for s, xf in ((1, TONGUE_X[1]), (-1, TONGUE_X[0])): p -= Pos(xf + s * 30, -117.5, 95) * Box(60, 95, 60)
    p -= cyl((ABS_X, 0.9, 72.5), (1, 0, 0), 36.0, 30.0)   # OEM ABS face x=67 + spot-face clearance
    return p

import time; t0 = time.time()
steel = [s for s, m, _ in parts.values() if m == '4130']; al = [s for s, m, _ in parts.values() if m == '7075']
st = cuts(sum(steel[1:], steel[0]))
rep = dict(concept=CON, parts={k: dict(material=m, process=pr) for k, (s, m, pr) in parts.items()})
def bigsol(p):
    ss = p.solids(); return max(ss, key=lambda s: s.volume), len(ss), [(round(s.volume), [round(c) for c in s.center()]) for s in ss]
bs, n, vols = bigsol(st)
if not bs.is_valid:
    try:
        fx = bs.fix(); bs = fx if fx.is_valid else bs
    except Exception as ex: print('fix failed', ex)
rep["steel"] = dict(n_solids=n, solid_vols=vols, valid=bool(bs.is_valid), vol=bs.volume, mass_kg=bs.volume * 7.85e-6)
out = [bs]
if al:
    ac = cuts(sum(al[1:], al[0]))
    ba, na, va = bigsol(ac); rep['al'] = dict(n_solids=na, solid_vols=va, valid=bool(ba.is_valid), vol=ba.volume, mass_kg=ba.volume * 2.81e-6)
    out.append(ba); export_step(bs, OUT + '_steel.step'); export_step(ba, OUT + '_7075.step')
    export_stl(bs, OUT + '_steel.stl', tolerance=0.05, angular_tolerance=0.2); export_stl(ba, OUT + '_7075.stl', tolerance=0.05, angular_tolerance=0.2)
    asm = Compound(out); export_step(asm, OUT + '.step'); export_stl(bs.fuse(ba), OUT + '.stl', tolerance=0.05, angular_tolerance=0.2)
else:
    export_step(bs, OUT + '.step'); export_stl(bs, OUT + '.stl', tolerance=0.05, angular_tolerance=0.2)
# per-part weld lengths (rough): perimeter of intersection between each pair of steel parts
wl = {}
names = [k for k, (s, m, _) in parts.items() if m == '4130']
for i, a_ in enumerate(names):
    for b_ in names[i + 1:]:
        try:
            ints = parts[a_][0] & parts[b_][0]
            if ints.volume > 1.0:
                bb = ints.bounding_box(); wl[f'{a_}+{b_}'] = round(ints.area / 4)   # contact patch ~ area/4 heuristic not used; store intersect area
        except Exception: pass
rep['steel_joints_intersect_area_mm2'] = wl
rep['total_mass_kg'] = rep['steel']['mass_kg'] + rep.get('al', {}).get('mass_kg', 0); rep['seconds'] = round(time.time() - t0)
json.dump(rep, open(OUT + '_build.json', 'w'), indent=1); print(json.dumps({k: rep[k] for k in ('steel', 'total_mass_kg', 'seconds')}), rep.get('al'))
