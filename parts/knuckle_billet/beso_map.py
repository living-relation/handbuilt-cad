"""BESO step-0 map on a CalculiX result: element stress envelope over the 5 cases -> low-stress material by region.
Usage: beso_map.py <stem> [frac=0.15]   (reads iter/<stem>_<case>.vtu)"""
import sys, json, numpy as np, meshio, math
stem = sys.argv[1]; frac = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
ALLOW = 251.0; RHO = 2.81e-6
cases = ['bump', 'corner', 'brake', 'combined', 'fatigue']
env = None
for c in cases:
    m = meshio.read(f'iter/{stem}_{c}.vtu'); vm = m.point_data['vonMises_MPa']
    if c == 'fatigue': vm = vm * (251.0 / 167.0)      # fatigue case scaled to its own allowable (Goodman ~167 MPa amplitude-equiv, conservative)
    env = vm if env is None else np.maximum(env, vm)
X = m.points; tets = [cb.data for cb in m.cells if cb.type.startswith('tetra')][0]
sing = m.point_data['singular_zone'] > 0.5
p = X[tets[:, :4]]; vol = np.abs(np.einsum('ij,ij->i', p[:, 1] - p[:, 0], np.cross(p[:, 2] - p[:, 0], p[:, 3] - p[:, 0]))) / 6
se = env[tets].max(1); cen = p.mean(1)
x, y, z = cen.T; r = np.hypot(x, y)
sys.path.insert(0, '.')
EYES = {"left": ((-79.15, 86.0, 83.0), (1, 0, 0), 46.0), "right": ((65.9, 73.9, 112.6), (math.cos(math.radians(13.6)), 0, -math.sin(math.radians(13.6))), 46.5),
        "top": ((-6.6, 138.1, 129.0), (-math.sin(math.radians(8.7)), 0, math.cos(math.radians(8.7))), 52.0)}
keep = (r < 50) & (z < 70)                                   # hub tube + bearing seat
for c0, a, od in EYES.values():
    c0 = np.array(c0); a = np.array(a); d = cen - c0; t = d @ a; rr = np.linalg.norm(d - np.outer(t, a), axis=1)
    keep |= (rr < od / 2 + 6) & (np.abs(t) < 20 + 6)
for hx, hy in [(-55.8, 18.1), (-47.5, -34.8), (53.7, -25.1), (51.8, 28.9)]: keep |= np.hypot(x - hx, y - hy) < 14
for hx, hy in [(-101.5, 29.0), (-41.0, -97.0)]: keep |= np.hypot(x - hx, y - hy) < 13
keep |= (y < -60) & (np.abs(x) < 20)                         # strut clamp zone: bolts at y -147.5 and -79.0 (d14), lands to 12 mm past the lower bolt edge -> y -60
keep |= np.hypot(y - 0.9, z - 72.5) < 14                      # side boss
def region(i):
    if 62 <= z[i] <= 82.5 and r[i] <= 72: return 'flange/hybrid plate'
    if abs(x[i]) <= 16 and y[i] < -40: return 'tongue'
    if r[i] < 50: return 'hub/web'
    if x[i] < -85 or (y[i] < -60 and x[i] < -20): return 'ear lugs'
    if y[i] > 60 and abs(x[i]) < 30: return 'top arm'
    if x[i] < -30 and y[i] > 30: return 'left arm'
    if x[i] > 30 and y[i] > 30: return 'right arm'
    return 'ribs/other'
low = (se < frac * ALLOW) & ~keep
lab = np.array([region(i) for i in range(len(se))])
out = {}
for L in sorted(set(lab)):
    m_ = lab == L
    out[L] = dict(mass_kg=round(float(vol[m_].sum() * RHO), 3), low_kg=round(float(vol[m_ & low].sum() * RHO), 3),
                  low_frac=round(float(vol[m_ & low].sum() / max(vol[m_].sum(), 1e-9)), 2),
                  p50_MPa=round(float(np.median(se[m_])), 1),
                  low_centroid=np.round(np.average(cen[m_ & low], axis=0, weights=vol[m_ & low]), 1).tolist() if (m_ & low).any() else None)
tot = dict(total_kg=round(float(vol.sum() * RHO), 3), kept_interface_kg=round(float(vol[keep].sum() * RHO), 3), low_kg=round(float(vol[low].sum() * RHO), 3), frac=frac)
json.dump(dict(total=tot, regions=out), open(f'iter/{stem}_beso_map.json', 'w'), indent=1)
print(json.dumps(tot)); [print(k, v) for k, v in out.items()]
np.savez_compressed(f'iter/{stem}_beso_map.npz', cen=cen, se=se, vol=vol, keep=keep, low=low)
