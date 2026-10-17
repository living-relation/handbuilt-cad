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
    e = m.contains(empty_pts) if len(empty_pts) else np.zeros(0, bool); s = m.contains(solid_pts)
    ok = (not e.any()) and s.mean() >= min_solid_frac
    checks.append(dict(feature=name, ok=bool(ok), empty_violations=int(e.sum()), solid_frac=round(float(s.mean()), 2)))
for z0, z1, d in ns['BORE'][:6]:
    zm = (max(z0, 0) + z1) / 2
    chk(f'bore d{d} z{z0}-{z1}', ring((0, 0, zm), (0, 0, 1), d/2 - 0.3, [0]), ring((0, 0, zm), (0, 0, 1), d/2 + 1.5, [0]))
for x, y in ns['FLANGE_HOLES']:
    chk(f'flange hole ({x},{y})', ring((x, y, 74), (0, 0, 1), 5.25 - 0.3, [-6, 0, 6]), ring((x, y, 74), (0, 0, 1), 5.25 + 1.5, [-4, 0, 4]))
for (x, y), d, (z0, z1) in ns['EAR_HOLES']:
    dp = min(d, float(__import__('os').environ.get('TAP_PILOT_EAR', d)))   # threaded ear holes may be modelled as tap-drill pilots (e.g. 8.8 for M10x1.25)
    zm = (z0 + z1) / 2; chk(f'ear hole ({x},{y}) d{d} (open >= d{dp})', ring((x, y, zm), (0, 0, 1), dp/2 - 0.3, [-8, 0, 8]), ring((x, y, zm), (0, 0, 1), d/2 + 1.5, [-8, 0, 8]))
for (y, z), d, x0, x1 in ns['X_HOLES']:
    xs = [0] if d == 17.0 else [-12, 0, 12]; xc = 60 if d == 17.0 else 0
    chk(f'X hole (y{y},z{z}) d{d}', ring((xc, y, z), (1, 0, 0), d/2 - 0.3, xs), ring((xc, y, z), (1, 0, 0), d/2 + 1.5, xs))
for k, v in ns['EYES'].items():
    L = v['length']; chk(f'{k} bore d{v["bore"]}', ring(v['c'], v['axis'], v['bore']/2 - 0.3, [-L/3, 0, L/3]), ring(v['c'], v['axis'], (v['bore'] + v['od'])/4, [-L/3, 0, L/3]), 0.95)
    chk(f'{k} OD {v["od"]} + end faces at +/-{L/2}', np.vstack([ring(v['c'], v['axis'], (v['bore'] + v['od'])/4, [L/2 + 0.4, -L/2 - 0.4])]),
        ring(v['c'], v['axis'], (v['bore'] + v['od'])/4, [L/2 - 0.6, -L/2 + 0.6]), 0.95)
# (chunk 18: the old x=+/-15 clamp-face check is superseded by the OEM-face check below)
# chunk 18 (Daniel's hard rules): OEM tongue faces, ABS mount face, strut-tube keep-out + clamp bracket envelope
TXo = (-13.8, 14.9)
for yy in (-159.0, -135.0, -91.0):
    chk(f'OEM tongue faces x={TXo} at y{yy}', np.array([[TXo[1] + 0.4, yy, z] for z in (88, 100)] + [[TXo[0] - 0.4, yy, z] for z in (88, 100)]),
        np.array([[TXo[1] - 1.4, yy, z] for z in (88, 100)] + [[TXo[0] + 1.4, yy, z] for z in (88, 100)]), 0.75)
chk('ABS face x=67.0 normal +X, boss r>=15', ring((67.4, 0.9, 72.5), (1, 0, 0), 12.0, [0]), np.vstack([ring((66.0, 0.9, 72.5), (1, 0, 0), r, [0]) for r in (10.0, 14.5)]), 0.9)
ko = []
for yy in np.arange(-250, -39, 6.0):
    for r in (5.0, 18.0, 30.0):
        for t in np.linspace(0, 2 * math.pi, 16, endpoint=False): ko.append([0.5 + r * math.cos(t), yy, 116 + 31 + r * math.sin(t)])
chk('strut tube keep-out (OD52 est +5, inboard of tongue, y -250..-40)', np.array(ko), np.array([[0.5, -100, 100]]), 1.0)
env = [[x, y, z] for x in (TXo[1] + 1, TXo[1] + 6, TXo[1] + 11, TXo[0] - 1, TXo[0] - 6, TXo[0] - 11) for y in (-170, -140, -110, -80, -66, -60) for z in (86, 100, 114)]
chk('strut clamp bracket envelope (ears beside the faces, y -171..-60, z 84-116)', np.array(env), np.array([[0.5, -100, 100]]), 1.0)
# baseline_al (Daniel): minimum-material rules around critical features (constraints for any future optimisation; no break-through)
MINWALL = dict(bearing_bore=6.0, eye_boss=5.0, strut_clamp=8.0, caliper_ear=6.0, abs_boss=6.0, abs_screw=4.0, flange_bolt=4.0)
def minwall(name, c, a, r_hole, t, s_list, frac=0.95):
    chk(f'MINWALL {name} >= {t} mm', np.zeros((0, 3)), ring(c, a, r_hole + t - 0.3, s_list, n=24), frac)
minwall('bearing bore (seat d74)', (0, 0, 0), (0, 0, 1), 37.0, MINWALL['bearing_bore'], [16, 30, 44])
for k, v in ns['EYES'].items():
    L = v['length']; minwall(f'{k} boss', v['c'], v['axis'], v['bore'] / 2, MINWALL['eye_boss'], [-L/3, 0, L/3])
for (y, z), d, x0, x1 in ns['X_HOLES'][1:]:
    minwall(f'strut clamp bolt y{y}', (0, y, z), (1, 0, 0), d / 2, MINWALL['strut_clamp'], [-8, 0, 8], 0.9)
for (x, y), d, (z0, z1) in ns['EAR_HOLES']:
    minwall(f'caliper ear ({x},{y}) (M10 major)', (x, y, (z0 + z1) / 2), (0, 0, 1), 5.0, MINWALL['caliper_ear'], [-5, 0, 5], 0.9)
minwall('ABS boss (d17)', (60, 0.9, 72.5), (1, 0, 0), 8.5, MINWALL['abs_boss'], [-3, 0, 3], 0.9)
minwall('ABS screw (M6)', (60, -39.4, 63.7), (1, 0, 0), 3.0, MINWALL['abs_screw'], [-3, 0, 3], 0.9)
for x, y in ns['FLANGE_HOLES']:
    minwall(f'flange bolt ({x},{y})', (x, y, 74), (0, 0, 1), 5.25, MINWALL['flange_bolt'], [-4, 0, 4], 0.9)
ok = all(c['ok'] for c in checks)
json.dump(dict(all_ok=ok, checks=checks), open(stl.replace('.stl', '_interface.json'), 'w'), indent=1)
for c in checks:
    if not c['ok']: print('FAIL', c)
print('INTERFACE ALL OK' if ok else 'INTERFACE FAILURES', sum(c['ok'] for c in checks), '/', len(checks))
