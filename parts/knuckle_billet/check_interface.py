"""Automatic interface check: every critical v4b feature must be open where it should be and surrounded by material."""
import sys, math, json, numpy as np, trimesh
sys.argv_ = sys.argv; stl = sys.argv[1]
import importlib.util
spec = importlib.util.spec_from_file_location('kb', 'knuckle_billet.py'); src = open('knuckle_billet.py').read().split("P = dict(")[0]
ns = {}; exec(src.replace('from build123d import *', ''), ns)
m = trimesh.load(stl)
def ring(c, a, r, s_list, n=12):
    c = np.array(c, float); a = np.array(a, float); a /= np.linalg.norm(a)
    u = np.cross(a, [0, 0, 1.0] if abs(a[2]) < 0.9 else [1.0, 0, 0]); u /= np.linalg.norm(u); w = np.cross(a, u)
    return np.array([c + a*s + r*(math.cos(t)*u + math.sin(t)*w) for s in s_list for t in np.linspace(0, 2*math.pi, n, endpoint=False)])
checks = []
def chk(name, empty_pts, solid_pts, min_solid_frac=0.75):
    e = m.contains(empty_pts); s = m.contains(solid_pts)
    ok = (not e.any()) and s.mean() >= min_solid_frac
    checks.append(dict(feature=name, ok=bool(ok), empty_violations=int(e.sum()), solid_frac=round(float(s.mean()), 2)))
for z0, z1, d in ns['BORE'][:6]:
    zm = (max(z0, 0) + z1) / 2
    chk(f'bore d{d} z{z0}-{z1}', ring((0, 0, zm), (0, 0, 1), d/2 - 0.3, [0]), ring((0, 0, zm), (0, 0, 1), d/2 + 1.5, [0]))
for x, y in ns['FLANGE_HOLES']:
    chk(f'flange hole ({x},{y})', ring((x, y, 74), (0, 0, 1), 5.25 - 0.3, [-6, 0, 6]), ring((x, y, 74), (0, 0, 1), 5.25 + 1.5, [-4, 0, 4]))
for (x, y), d, (z0, z1) in ns['EAR_HOLES']:
    zm = (z0 + z1) / 2; chk(f'ear hole ({x},{y}) d{d}', ring((x, y, zm), (0, 0, 1), d/2 - 0.3, [-8, 0, 8]), ring((x, y, zm), (0, 0, 1), d/2 + 1.5, [-8, 0, 8]))
for (y, z), d, x0, x1 in ns['X_HOLES']:
    xs = [0] if d == 17.0 else [-12, 0, 12]; xc = 60 if d == 17.0 else 0
    chk(f'X hole (y{y},z{z}) d{d}', ring((xc, y, z), (1, 0, 0), d/2 - 0.3, xs), ring((xc, y, z), (1, 0, 0), d/2 + 1.5, xs))
for k, v in ns['EYES'].items():
    L = v['length']; chk(f'{k} bore d{v["bore"]}', ring(v['c'], v['axis'], v['bore']/2 - 0.3, [-L/3, 0, L/3]), ring(v['c'], v['axis'], (v['bore'] + v['od'])/4, [-L/3, 0, L/3]), 0.95)
    chk(f'{k} OD {v["od"]} + end faces at +/-{L/2}', np.vstack([ring(v['c'], v['axis'], (v['bore'] + v['od'])/4, [L/2 + 0.4, -L/2 - 0.4])]),
        ring(v['c'], v['axis'], (v['bore'] + v['od'])/4, [L/2 - 0.6, -L/2 + 0.6]), 0.95)
for yy in (-159.0, -135.0, -91.0):
    chk(f'strut clamp faces x=+/-15 at y{yy}', np.array([[15.4, yy, 95], [-15.4, yy, 95], [15.4, yy, 85], [-15.4, yy, 85]]),
        np.array([[14.0, yy, 95], [-14.0, yy, 95], [14.0, yy, 85], [-14.0, yy, 85]]), 0.75)
ok = all(c['ok'] for c in checks)
json.dump(dict(all_ok=ok, checks=checks), open(stl.replace('.stl', '_interface.json'), 'w'), indent=1)
for c in checks:
    if not c['ok']: print('FAIL', c)
print('INTERFACE ALL OK' if ok else 'INTERFACE FAILURES', sum(c['ok'] for c in checks), '/', len(checks))
