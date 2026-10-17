"""STEP round-trip + per-file diff (orig vs fixed): solids, validity, volume, bbox, mass."""
import sys, os, json, glob
from build123d import *
RHO = {'Cu': 8.94, 'Al': 2.70, 'PA12': 1.01}
def mat(p):
    return 'Cu' if 'Cu' in p else ('PA12' if ('PA12' in p or 'Holder' in p or 'holder' in p) else 'Al')
res = {}
for f in sorted(glob.glob('out/**/*.step', recursive=True)):
    o = f.replace('out/', 'orig/', 1)
    a = import_step(f); s = a.solids()
    r = dict(n=len(s), valid=all(x.is_valid for x in s), vol=round(sum(x.volume for x in s), 2))
    bb = a.bounding_box(); r['bbox'] = [round(v, 2) for v in (*bb.min, *bb.max)]
    if os.path.exists(o):
        b = import_step(o); t = b.solids(); bo = b.bounding_box()
        r.update(n0=len(t), vol0=round(sum(x.volume for x in t), 2), bbox0=[round(v, 2) for v in (*bo.min, *bo.max)])
    if 'assembly' not in f:
        m = mat(f); r['material'] = m; r['mass_g'] = round(r['vol'] * RHO[m] / 1000, 1)
        if 'vol0' in r: r['mass0_g'] = round(r['vol0'] * RHO[m] / 1000, 1)
    res[f] = r; print(f, r)
json.dump(res, open('logs/roundtrip.json', 'w'), indent=1)
