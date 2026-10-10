"""Connectivity check of a density result: rho>0.5 voxels, 26-connected components; every interface (non-design group) must sit in the main one."""
import numpy as np, sys, json
from scipy.ndimage import label
D = np.load(sys.argv[1]); n = D['n']; ea = D['ea']; rho = D['rho']; isnd = D['isnd']; h = float(D['h'])
G = np.zeros(int(np.prod(n)), bool); G[ea[rho > 0.5]] = True; G = G.reshape(tuple(n))
lab, nc = label(G, structure=np.ones((3, 3, 3)))
sizes = np.bincount(lab.ravel())[1:]; main = int(np.argmax(sizes)) + 1
lab_e = lab.reshape(-1)[ea]
ndl = lab_e[isnd & (rho > 0.5)]
frac_nd_main = float((ndl == main).mean())
res = dict(components=int(nc), main_frac=float(sizes.max() / sizes.sum()), nondesign_in_main=frac_nd_main,
           mass_main_kg=float(sizes.max() * h**3 * 2.81e-6), mass_all_kg=float(sizes.sum() * h**3 * 2.81e-6))
print(json.dumps(res)); json.dump(res, open(sys.argv[1].replace('.npz', '_connect.json'), 'w'))
