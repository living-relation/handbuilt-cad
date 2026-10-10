"""Billet rear knuckle (ST185) - build123d. Interface copied from knuckle/v4b/knuckle.py (never moved).
Body: hub tube + bolt flange ring + solid strut-clamp tongue + H-section arms (pocketed from +/-Z, 3+2 machinable)
to the 3 eyes, a tongue-to-lateral-eye rib, ear and side bosses. Usage: python knuckle_billet.py <params.json> <outstem>"""
import math, json, sys
import numpy as np
from build123d import *

# ------------------------------------------------ INTERFACE (exactly v4b)
BORE = [(-1.0, 10.5, 75.0), (10.5, 13.5, 78.0), (13.5, 46.0, 74.0), (46.0, 50.5, 67.0), (50.5, 58.5, 75.0), (58.5, 66.0, 79.2), (66.0, 85.0, 67.0)]
FLANGE_HOLE_D = 10.5; FLANGE_HOLES = [(-55.8, 18.1), (-47.5, -34.8), (53.7, -25.1), (51.8, 28.9)]; FLANGE_HOLE_Z = (38.0, 82.0)
EAR_HOLES = [((-101.5, 29.0), 10.0, (40.0, 64.0)), ((-41.0, -97.0), 9.0, (39.0, 70.0))]
X_HOLES = [((0.9, 72.5), 17.0, 38.0, 72.0), ((-147.5, 96.2), 14.3, -30.0, 25.0), ((-79.0, 93.7), 14.0, -30.0, 25.0)]
c13, s13, c87, s87 = math.cos(math.radians(13.6)), math.sin(math.radians(13.6)), math.cos(math.radians(8.7)), math.sin(math.radians(8.7))
EYES = {"left_eye": dict(c=(-79.15, 86.0, 83.0), axis=(1, 0, 0), od=46.0, bore=35.0, length=26.0),
        "right_eye": dict(c=(65.9, 73.9, 112.6), axis=(c13, 0, -s13), od=46.5, bore=35.5, length=26.0),
        "top_eye": dict(c=(-6.6, 138.1, 129.0), axis=(-s87, 0, c87), od=52.0, bore=40.0, length=40.0)}
TONGUE_X = (-15.0, 15.0)   # strut-bracket clamp faces (v4b tongue measured -14.4..15.2 / -16.5..17.0)

P = dict(hub_od=92.0, flange_r=71.0, flange_z=(62.0, 82.0), tongue_y=(-166.0, -40.0), tongue_z=(72.0, 116.0),
         tongue_pocket_depth=12.0, arm_w=34.0, arm_h=42.0, wall=6.0, web=6.0, edge_r=4.0, pocket_r=6.0,
         ear_boss_d=26.0, side_boss_d=32.0, keepout_r=45.0, flange_pockets=True, flange_pocket_angles=(95, 189), junction_r=6.0, ear_lug_to_flange_top=False, left_arm_h=None,
         flange_style='disc', ring_r=56.0, bolt_boss_r=11.5, floor_r=0.0, tongue_bottom_pocket=0.0, tongue_junction_r=0.0,
         left_root=(-50, 40, 76), right_root=(45, 45, 82), top_root=(-5, 55, 78), arm_left=None, arm_right=None, arm_top=None, rib_r2=(24.0, 30.0), tongue_blend=0.0, tongue_blend_len=32.0, sector_y=-12.0, hybrid_pockets=(), tongue_root_patch=0.0, tongue_under_wedge=0.0, wedge_flare=0.0,
         layout='arms', ribs=True, frame_lt=(30.0, 36.0), frame_tr=(30.0, 36.0), strip_w=26.0, ear1_link_w=0.0, left_strut2=None, ties=(), rib_size=None, rib_end_clear=14.0, rib_inner_solid=False, ribs_left=False, left_gusset=None, blend_mode='chamfer', arm_pockets=True, rib_pockets=True, lug_pockets=True, wall_right=None, wall_top=None)
if len(sys.argv) > 1 and sys.argv[1].endswith('.json'): P.update(json.load(open(sys.argv[1])))
for k in ('arm_left', 'arm_right', 'arm_top'):
    if P[k] is None: P[k] = (P['arm_w'], P['left_arm_h'] or P['arm_h']) if k == 'arm_left' else (P['arm_w'], P['arm_h'])
OUT = sys.argv[2] if len(sys.argv) > 2 else 'knuckle_billet'
V = lambda *a: Vector(*a)

def cyl(c, axis, d, length):
    """cylinder starting at c and running +length along axis"""
    a = V(*axis).normalized(); return Plane(origin=V(*c), z_dir=a) * Cylinder(d/2, length, align=(Align.CENTER, Align.CENTER, Align.MIN))
def tube(c, axis, od, length):
    """cylinder centred on c"""
    a = V(*axis).normalized(); return Plane(origin=V(*c), z_dir=a) * Cylinder(od/2, length)
def frame(A, B, hint=(0, 0, 1)):
    A, B = V(*A), V(*B); x = (B - A).normalized(); h = V(*hint)
    n = (h - x * h.dot(x)).normalized(); return Plane(origin=(A + B) * 0.5, x_dir=x, z_dir=n), (B - A).length
def hbar(A, B, w, h, end_clear=18.0, hint=(0, 0, 1), pockets=True, wall=None):
    """H-section arm: solid bar with long edges filleted, pocketed from both local +/-z faces (3+2 machinable)."""
    pl, L = frame(A, B, hint)
    bar = Box(L, w, h)
    try: bar = fillet(bar.edges().filter_by(Axis.X), P['edge_r'])
    except Exception: pass
    bar = pl * bar
    pl_len = L - 2 * end_clear; pw = w - 2 * (wall or P['wall']); pd = (h - P['web']) / 2
    if P['arm_pockets'] and pockets and pl_len > 2 * P['pocket_r'] + 2 and pw > 2 * P['pocket_r'] + 1 and pd > 0.5:
        for s in (1, -1):
            sk = Plane(origin=(0, 0, s * h / 2), z_dir=(0, 0, -s)) * RectangleRounded(pl_len, pw, P['pocket_r'])
            pk = extrude(sk, amount=pd)
            if P['floor_r'] > 0:
                try: pk = fillet(pk.edges().filter_by(lambda e, s=s, h=h, pd=pd: abs(e.center().Z - s * (h / 2 - pd)) < 0.01), P['floor_r'])
                except Exception: pass
            bar = bar - pl * pk
    return bar

def junction_fillets(part):
    zf0, zf1 = P['flange_z']; done = []
    for zf in (zf1, zf0):
        cand = [e for e in part.edges() if all(abs(v.Z - zf) < 0.05 for v in e.vertices()) and len(e.vertices()) > 0
                and 46.0 < math.hypot(e.center().X, e.center().Y) < P['flange_r'] - 1.0]
        for r in (P['junction_r'], P['junction_r'] - 2.0, 4.0):
            try:
                part = fillet(cand, r); done.append((zf, len(cand), r)); break
            except Exception:
                ok = 0
                for e in cand:                       # one by one, skipping the ones OCC can't do
                    try:
                        ee = [x for x in part.edges() if (x.center() - e.center()).length < 0.05]
                        if ee: part = fillet(ee, r); ok += 1
                    except Exception: pass
                if ok: done.append((zf, ok, r, 'partial')); break
    if P['tongue_junction_r'] > 0:   # tongue side faces (x = +/-15) meeting the flange top: the it4 hot spot (15,-42,82)
        te = [e for e in part.edges() if all(abs(v.Z - zf1) < 0.05 for v in e.vertices()) and any(abs(abs(v.X) - 15.0) < 0.05 for v in e.vertices())
              and -80 < e.center().Y < -30]
        for r in (P['tongue_junction_r'], 6.0):
            try: part = fillet(te, r); done.append(('tongue', len(te), r)); break
            except Exception: pass
    print('junction fillets', done, flush=True)
    return part

def build():
    zf0, zf1 = P['flange_z']
    part = Cylinder(P['hub_od']/2, 66.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if P['flange_style'] == 'disc':
        part += Pos(0, 0, zf0) * Cylinder(P['flange_r'], zf1 - zf0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    else:   # spoked ring: collar ring + a boss around each bolt + radial spoke from the hub to each boss
        part += Pos(0, 0, zf0) * Cylinder(P['ring_r'], zf1 - zf0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        for x, y in FLANGE_HOLES:
            part += Pos(x, y, zf0) * Cylinder(P['bolt_boss_r'], zf1 - zf0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        if P['flange_style'] == 'hybrid':   # full-radius plate on the arm side (y > sector_y) to tie the 3 arm roots together
            plate = Pos(0, 0, zf0) * Cylinder(P['flange_r'], zf1 - zf0, align=(Align.CENTER, Align.CENTER, Align.MIN))
            plate = plate & Pos(0, P['sector_y'] + 100, (zf0 + zf1) / 2) * Box(200, 200, zf1 - zf0 + 2)
            part += plate
            for ang in P['hybrid_pockets']:
                a = math.radians(ang); r = (P['ring_r'] + P['flange_r']) / 2 + 1
                part -= Pos(r*math.cos(a), r*math.sin(a), zf1 - 10) * Rot(0, 0, ang + 90) * extrude(RectangleRounded(20, 10, 4.5), amount=11)
    # ear bosses + lugs to the hub
    for (x, y), d, (z0, z1) in EAR_HOLES:
        part += Pos(x, y, z0) * Cylinder(P['ear_boss_d']/2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        r = math.hypot(x, y); ux, uy = x / r, y / r
        ei = 0 if x < -90 else 1
        lw = P['ear1_link_w'] if (ei == 0 and P['ear1_link_w']) else P['ear_boss_d']
        part += hbar((ux*35, uy*35, (z0+z1)/2), (x, y, (z0+z1)/2), lw, z1 - z0, end_clear=40.0, pockets=P['lug_pockets'])
        if P['ear_lug_to_flange_top'] and not (ei == 0 and P['ear1_link_w']):   # deep lug tying the ear into the full flange depth, stopping short of the bolt seat
            zt = P['flange_z'][1]; zm = (z0 + zt) / 2
            part += hbar((ux*35, uy*35, zm), (x - ux*(P['ear_boss_d']/2 + 4), y - uy*(P['ear_boss_d']/2 + 4), zm), P['ear_boss_d'], zt - z0, end_clear=60.0, pockets=P['lug_pockets'])
    # side boss (ABS?) along X
    (y, z), d, x0, x1 = X_HOLES[0]
    part += cyl((x0, y, z), (1, 0, 0), P['side_boss_d'], x1 - x0)
    # strut clamp tongue (solid between the clamp faces, pocketed from +Z between the bolts)
    ty0, ty1 = P['tongue_y']; tz0, tz1 = P['tongue_z']
    tg = Pos((TONGUE_X[0]+TONGUE_X[1])/2, (ty0+ty1)/2, (tz0+tz1)/2) * Box(TONGUE_X[1]-TONGUE_X[0], ty1-ty0, tz1-tz0)
    try: tg = fillet(tg.edges().filter_by(Axis.Y), P['edge_r'])
    except Exception: pass
    part += tg
    if P['tongue_pocket_depth'] > 0:
        pkt = Pos(0, -113.25, tz1 - P['tongue_pocket_depth']) * extrude(RectangleRounded(TONGUE_X[1]-TONGUE_X[0]-2*P['wall'], 30.0, P['pocket_r']), amount=P['tongue_pocket_depth'] + 1)
        part -= pkt
    if P['tongue_bottom_pocket'] > 0:
        pkb = Pos(0, -113.25, tz0 - 1) * extrude(RectangleRounded(TONGUE_X[1]-TONGUE_X[0]-2*P['wall'], 30.0, P['pocket_r']), amount=P['tongue_bottom_pocket'] + 1)
        if P['floor_r'] > 0:
            try: pkb = fillet(pkb.edges().filter_by(lambda e: abs(e.center().Z - (tz0 + P['tongue_bottom_pocket'])) < 0.01), P['floor_r'])
            except Exception: pass
        part -= pkb
    # tongue-root blend: 45-degree fill prisms along both tongue side faces where they meet the flange top (it4 hot spot (15,-42,82))
    if P['tongue_blend'] > 0:
        Lb = P['tongue_blend']; zt = P['flange_z'][1]
        pl = Plane(origin=(0, -36.0, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))
        for sx in (1, -1):
            x0 = TONGUE_X[1] if sx > 0 else TONGUE_X[0]
            if P['blend_mode'] == 'fillet':   # true concave radius Lb tangent to the tongue side face and the flange top (no 45-deg facet)
                rect = Polygon((x0 - sx * 2, zt - 2), (x0 + sx * Lb, zt - 2), (x0 + sx * Lb, zt + Lb), (x0 - sx * 2, zt + Lb), align=None)
                prof = pl * extrude(rect, amount=P['tongue_blend_len'])
                cut = Plane(origin=(x0 + sx * Lb, -36.0, zt + Lb), x_dir=(1, 0, 0), z_dir=(0, -1, 0)) * Cylinder(Lb, P['tongue_blend_len'] + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
                part += prof - Pos(0, 1, 0) * cut
            else:
                tri = Polygon((x0 - sx * 2, zt - 2), (x0 + sx * Lb, zt - 2), (x0 + sx * Lb, zt), (x0 - sx * 2, zt + Lb), align=None)
                part += pl * extrude(tri, amount=P['tongue_blend_len'])
    # chunk 4 options for the braking peak at the tongue lower side edge (-14.9,-69.1,75)
    if P['tongue_root_patch'] > 0:   # A: keep the full-radius disc under the tongue root (|x| <= patch half-width, y < 0)
        zf0, zf1 = P['flange_z']; hw = P['tongue_root_patch']
        patch = Pos(0, 0, zf0) * Cylinder(P['flange_r'], zf1 - zf0, align=(Align.CENTER, Align.CENTER, Align.MIN))
        patch = patch & Pos(0, -50, (zf0 + zf1) / 2) * Box(2 * hw, 100, zf1 - zf0 + 2)
        part += patch
    if P['tongue_under_wedge'] > 0:  # B: ramp under the tongue from the ring bottom out along the tongue bottom face
        Lw = P['tongue_under_wedge']; zf0 = P['flange_z'][0]; tz0 = P['tongue_z'][0]; y0 = -(P['ring_r'] - 6.0)
        plw = Plane(origin=(TONGUE_X[0] - P['wedge_flare'], 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))   # local x = global Y, local y = global Z
        tri = Polygon((y0, zf0), (y0, tz0 + 2), (y0 - Lw, tz0 + 2), (y0 - Lw, tz0), align=None)
        part += plw * extrude(tri, amount=TONGUE_X[1] - TONGUE_X[0] + 2 * P['wedge_flare'])
    # tongue root gusset down into the flange ring
    part += hbar((0, -45, 80), (0, -95, tz0 + 8), 30.0, 26.0, end_clear=60.0, hint=(1, 0, 0))
    # arms to the eyes (H-section), start on the flange ring outside the drive-shaft keep-out
    e = EYES
    if P['layout'] == 'frame':   # it13+: struts to the lateral eyes + closed I-beam lower frame L-eye -> strut-rod eye -> R-eye
        part += hbar(P['left_root'], e['left_eye']['c'], *P['arm_left'])
        part += hbar(P['right_root'], e['right_eye']['c'], *P['arm_right'])
        part += hbar(e['left_eye']['c'], e['top_eye']['c'], *P['frame_lt'], end_clear=26.0)
        if P['left_gusset']:   # merged left gusset plate: tongue root -> ear-1 lug corner -> left strut root -> left eye (replaces ribs L1/L2)
            g = P['left_gusset']; pts = [tuple(p_) for p_ in g['pts']]
            face = make_face(Polyline(*pts, close=True))
            plate = extrude(Pos(0, 0, g['z0']) * face, amount=g['z1'] - g['z0'])
            try: plate = fillet(plate.edges().filter_by(Axis.Z), 6.0)
            except Exception: pass
            if g.get('pocket', 0) > 0:
                try:
                    inner = offset(face, -g.get('wall', 6.0))
                    pk = extrude(Pos(0, 0, g['z1'] - g['pocket']) * inner, amount=g['pocket'] + 1)
                    try: pk = fillet(pk.edges().filter_by(Axis.Z), 5.0)
                    except Exception: pass
                    plate = plate - pk
                except Exception as ex: print('gusset pocket failed', ex)
            part += plate
        for A_, B_, w_, h_ in P['ties']:   # solid cross-ties / gusset webs (no pockets) closing strut-frame triangles
            part += hbar(tuple(A_), tuple(B_), w_, h_, end_clear=1e3)
        if P['left_strut2']:   # second left strut: flange/ear-1 lug corner -> left eye (old rib L2 path)
            part += hbar((-62, 10, 80), e['left_eye']['c'], *P['left_strut2'], end_clear=14.0)
        part += hbar(e['top_eye']['c'], e['right_eye']['c'], *P['frame_tr'], end_clear=26.0)
        for root in (P['left_root'], P['right_root']):   # strips under the strut roots, radial, flange depth
            rr = math.hypot(root[0], root[1]); ux, uy = root[0] / rr, root[1] / rr; zf0, zf1 = P['flange_z']
            part += hbar((ux * 44, uy * 44, (zf0 + zf1) / 2), (root[0] + ux * 6, root[1] + uy * 6, (zf0 + zf1) / 2), P['strip_w'], zf1 - zf0, end_clear=40.0, pockets=P['lug_pockets'])
    else:
        part += hbar(P['left_root'], e['left_eye']['c'], *P['arm_left'])
        part += hbar(P['right_root'], e['right_eye']['c'], *P['arm_right'], wall=P['wall_right'])
        part += hbar(P['top_root'], e['top_eye']['c'], *P['arm_top'], hint=(1, 0, 0), wall=P['wall_top'])
    # rib: strut-clamp tongue -> right lateral eye (around the drive shaft), and tongue -> left eye via the flange
    if P['ribs'] or P['ribs_left']:
        rs = P['rib_size']; r2 = P['rib_r2'] if rs is None else rs; rs = (24.0, 30.0) if rs is None else rs
        ri = (24.0, 30.0) if P['rib_inner_solid'] else rs     # inner segments skirt the drive-shaft keep-out: keep them solid
        if P['ribs']:
            part += hbar((4, -62, 96), (60, 0, 100), *ri, end_clear=P['rib_end_clear'], pockets=P['rib_pockets'])
            part += hbar((60, 0, 100), e['right_eye']['c'], *r2, end_clear=P['rib_end_clear'], pockets=P['rib_pockets'])
        part += hbar((-4, -60, 92), (-62, 10, 80), *ri, end_clear=P['rib_end_clear'], pockets=P['rib_pockets'])
        part += hbar((-62, 10, 80), e['left_eye']['c'], *rs, end_clear=P['rib_end_clear'], pockets=P['rib_pockets'])
    # eyes (exact OD/length)
    for k, v in e.items(): part += tube(v['c'], v['axis'], v['od'], v['length'])
    # flange-ring lightening pockets between the bolt holes, from +Z
    if P['flange_pockets'] and P['flange_style'] == 'disc':
        for ang in P['flange_pocket_angles']:
            a = math.radians(ang); r = (P['hub_od']/2 + P['flange_r']) / 2 + 2
            pk = Pos(r*math.cos(a), r*math.sin(a), zf1 - 10) * Rot(0, 0, ang + 90) * extrude(RectangleRounded(26, 13, 6.0), amount=11)
            part -= pk
    # junction fillets: concave edges where arms/lugs/tongue meet the flange-ring faces (old braking spike zone included)
    part = junction_fillets(part)
    # ---------------- interface cuts (exact v4b)
    part -= Pos(0, 0, 66.0) * Cylinder(P['keepout_r'], 200, align=(Align.CENTER, Align.CENTER, Align.MIN))  # drive-shaft keep-out above the hub
    for z0, z1, d in BORE: part -= Pos(0, 0, z0) * Cylinder(d/2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for x, y in FLANGE_HOLES: part -= Pos(x, y, FLANGE_HOLE_Z[0]) * Cylinder(FLANGE_HOLE_D/2, FLANGE_HOLE_Z[1]-FLANGE_HOLE_Z[0], align=(Align.CENTER, Align.CENTER, Align.MIN))
    for (x, y), d, (z0, z1) in EAR_HOLES: part -= Pos(x, y, z0 - 1) * Cylinder(d/2, z1 - z0 + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for (y, z), d, x0, x1 in X_HOLES: part -= cyl((x0, y, z), (1, 0, 0), d, x1 - x0)
    for k, v in e.items():
        a = V(*v['axis']).normalized(); c = V(*v['c']) - a * (v['length']/2 + 30)
        part -= cyl(tuple(c), tuple(a), v['bore'], v['length'] + 60)
        # keep the eye end faces at the v4b positions: trim anything that sticks past them inside the eye OD + 6
        for s in (1, -1):
            o = V(*v['c']) + a * s * (v['length']/2)
            part -= Plane(origin=o, z_dir=a * s) * Cylinder(v['od']/2 + 6, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
    # tongue clamp faces: nothing proud of x = TONGUE_X along the clamp length
    for s, xf in ((1, TONGUE_X[1]), (-1, TONGUE_X[0])):
        part -= Pos(xf + s * 30, -117.5, 95) * Box(60, 95, 60)
    return part

def solid_of(p):
    s = p.solids(); return s, len(s)

if __name__ == '__main__':
    import time; t = time.time()
    part = build()
    sol, n = solid_of(part)
    big = max(sol, key=lambda s: s.volume)
    rep = dict(n_solids=n, valid=bool(big.is_valid), volume_mm3=big.volume, mass_7075_kg=big.volume * 2.81e-6, mass_6061_kg=big.volume * 2.70e-6, bbox=str(big.bounding_box()), seconds=round(time.time() - t))
    export_step(big, OUT + '.step'); export_stl(big, OUT + '.stl', tolerance=0.05, angular_tolerance=0.2)
    json.dump(dict(P=P, report=rep), open(OUT + '_build.json', 'w'), indent=1); print(json.dumps(rep))
