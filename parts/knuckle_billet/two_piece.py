"""Two-piece knuckle: main (hub/flange/arms/eyes) + bolt-on strut tongue with a Z-bolted foot on the flange top.
Base geometry = full-arm (solid arms, no tilted arm pockets). Usage: two_piece.py <params.json> <outdir>"""
import sys, json, math
sys.argv = [sys.argv[0], sys.argv[1], '/tmp/tp_dummy'] + sys.argv[2:]
OUTDIR = sys.argv[3]
exec(open('knuckle_billet.py').read().split("if __name__ == '__main__':")[0])
full = build(); full = max(full.solids(), key=lambda s: s.volume)
ZJ = P['flange_z'][1]                       # joint plane = flange top z 82
FOOT = dict(x=34.0, y0=-69.0, y1=-38.0, t=16.0)
# tongue region: everything above the flange top in the tongue strip + everything beyond the flange disc edge in the strip
Treg = Pos(0, (FOOT['y1'] - 200) / 2, ZJ + 50) * Box(2 * FOOT['x'], 200 + FOOT['y1'], 100)
Treg += Pos(0, (FOOT['y0'] - 200) / 2, 66.0 + 50) * Box(32.0, 200 + FOOT['y0'], 100)   # tongue beyond the disc edge: x +/-16, z >= 66 (clears the ear-2 lug)
tongue = full & Treg
main = full - Treg
foot = Pos(0, (FOOT['y0'] + FOOT['y1']) / 2, ZJ + FOOT['t'] / 2) * Box(2 * FOOT['x'], FOOT['y1'] - FOOT['y0'], FOOT['t'])
try: foot = fillet(foot.edges().filter_by(Axis.Z), 6.0)
except Exception: pass
tongue = tongue + (foot - Pos(0, 0, 66.0) * Cylinder(P['keepout_r'], 200, align=(Align.CENTER, Align.CENTER, Align.MIN)))
# joint: 4x M12 12.9 through-bolts (d13), inner pair fitted, foot -> flange with nuts under the flange, 2x d8 dowels (H7), all along Z
BOLTS = [(-10.0, -57.1), (10.0, -57.1), (-28.0, -50.8), (28.0, -50.8)]   # on an r58 arc: >=2 mm to the r45 keep-out and the r71 flange edge, 20 mm pitch
DOWELS = []   # location by the inner pair as fitted shoulder bolts (d11 reamed) + foot shoulder on the main body at y -38
for (bx, by) in BOLTS:
    c = Pos(bx, by, ZJ - 20.0 - 1) * Cylinder(6.5, 20.0 + FOOT['t'] + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    tongue -= c; main -= c
for (bx, by) in DOWELS:
    c = Pos(bx, by, ZJ - 10.0) * Cylinder(4.0, 20.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    tongue -= c; main -= c
rep = {}
for name, s in (('main', main), ('tongue', tongue)):
    sol = s.solids(); big = max(sol, key=lambda q: q.volume)
    bb = big.bounding_box()
    rep[name] = dict(n_solids=len(sol), valid=bool(big.is_valid), mass_kg=round(big.volume * 2.81e-6, 3),
                     bbox_mm=[round(bb.max.X - bb.min.X, 1), round(bb.max.Y - bb.min.Y, 1), round(bb.max.Z - bb.min.Z, 1)],
                     zrange=[round(bb.min.Z, 1), round(bb.max.Z, 1)])
    export_step(big, f'{OUTDIR}/{name}.step'); export_stl(big, f'{OUTDIR}/{name}.stl', tolerance=0.05, angular_tolerance=0.2)
asm = Compound([max(main.solids(), key=lambda q: q.volume), max(tongue.solids(), key=lambda q: q.volume)])
export_stl(asm, f'{OUTDIR}/assembled.stl', tolerance=0.05, angular_tolerance=0.2); export_step(asm, f'{OUTDIR}/assembled.step')
exp = Compound([max(main.solids(), key=lambda q: q.volume), Pos(0, -40, 60) * max(tongue.solids(), key=lambda q: q.volume)])
export_stl(exp, f'{OUTDIR}/exploded.stl', tolerance=0.05, angular_tolerance=0.2)
fused = max((main + tongue).solids(), key=lambda q: q.volume); export_step(fused, f'{OUTDIR}/fused_for_fea.step')
rep['total_kg'] = round(rep['main']['mass_kg'] + rep['tongue']['mass_kg'], 3); rep['bolts'] = BOLTS; rep['dowels'] = DOWELS; rep['foot'] = FOOT
json.dump(rep, open(f'{OUTDIR}/build.json', 'w'), indent=1); print(json.dumps(rep))
