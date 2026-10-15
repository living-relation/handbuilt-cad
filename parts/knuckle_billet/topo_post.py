"""Density result -> iso-surface STL (rho=0.5) + region read-out vs it11.  usage: topo_post.py <stem>"""
import os
MODELS_DIR = os.environ.get('MODELS_DIR', os.path.expanduser('~/models'))
KB = os.path.join(MODELS_DIR, 'knuckle_billet_1009')  # moved part files: baseline/, iter-opt/
import numpy as np, json, sys, trimesh
from skimage.measure import marching_cubes
from scipy.ndimage import gaussian_filter
stem = sys.argv[1]; D = np.load(stem + '.npz'); n = D['n']; lo = D['lo']; h = float(D['h']); ea = D['ea']; rho = D['rho']; isnd = D['isnd']
G = np.zeros(int(np.prod(n))); G[ea] = rho; G = G.reshape(tuple(n))
Gp = np.pad(gaussian_filter(G, 0.6), 1)
v, f, _, _ = marching_cubes(Gp, 0.5); v = (v - 1 + 0.5) * h + lo
m = trimesh.Trimesh(v, f); trimesh.smoothing.filter_taubin(m, iterations=10); m.export(stem + '_iso.stl')
mass_thr = (rho > 0.5).sum() * h**3 * 2.81e-6
# region read-out: it11 voxels vs topo material
C = lo + (np.stack(np.unravel_index(ea, tuple(n)), 1) + 0.5) * h
vv = trimesh.load(os.path.join(KB, 'iter-opt', 'it11.stl')).voxelized(pitch=h / 2).fill().points
g = np.floor((vv - lo) / h).astype(int); ok = np.all((g >= 0) & (g < n), 1); g = g[ok]
occ = np.zeros(tuple(n), bool); occ[g[:, 0], g[:, 1], g[:, 2]] = True; in11 = occ.reshape(-1)[ea]
solid = rho > 0.5; x, y, z = C.T; r = np.hypot(x, y)
regions = {
 'tongue root / below clamp (y -67..-40)': (y > -67) & (y < -40) & (np.abs(x) < 40),
 'flange ring, tongue side (y<-12)': (z >= 60) & (z <= 84) & (r < 75) & (y < -12) & ~((np.abs(x) < 16) & (y < -40)),
 'flange plate, arm side (y>-12)': (z >= 60) & (z <= 84) & (r < 75) & (y >= -12),
 'hub tube outer z<60': (z < 60) & (r < 52),
 'ear-1 lug zone': (np.hypot(x + 70, y - 20) < 30) & (z < 70),
 'ear-2 lug zone': (np.hypot(x + 28, y + 70) < 30) & (z < 72),
 'left-eye arm zone': (x < -40) & (y > 20) & (y < 70) & (z > 60),
 'right-eye arm zone': (x > 30) & (y > 20) & (y < 60) & (z > 70),
 'top-eye arm zone': (np.abs(x) < 35) & (y > 45) & (y < 115) & (z > 75),
 'rib tongue->right eye (x>15, y -60..20, z>84)': (x > 15) & (y > -60) & (y < 20) & (z > 84),
 'rib tongue->left eye (x<-15, y -60..20, z>84)': (x < -15) & (y > -60) & (y < 20) & (z > 84),
}
out = {}
for k, msk in regions.items():
    a = msk & ~isnd
    out[k] = dict(topo_kg=round(float((solid & a).sum() * h**3 * 2.81e-6), 3), it11_kg=round(float((in11 & a).sum() * h**3 * 2.81e-6), 3),
                  it11_kept_frac=round(float((solid & in11 & a).sum() / max((in11 & a).sum(), 1)), 2),
                  topo_outside_it11_kg=round(float((solid & ~in11 & a).sum() * h**3 * 2.81e-6), 3))
res = dict(stem=stem, mass_rho_gt_0p5_kg=round(mass_thr, 3), iso_volume_kg=round(m.volume * 2.81e-6, 3) if m.is_volume else None, grey_frac=round(float(((rho > 0.1) & (rho < 0.9) & ~isnd).sum() / (~isnd).sum()), 3), regions=out)
json.dump(res, open(stem + '_readout.json', 'w'), indent=1); print(json.dumps(res, indent=1))
