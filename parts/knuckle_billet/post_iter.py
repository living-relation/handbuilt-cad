"""Parse CalculiX .frd (U, S per step), compute von Mises, safety factors, write results.json/.md and VTU files."""
import numpy as np, json, meshio, math
import sys; D = sys.argv[1]; STEM = sys.argv[2]; L = json.load(open('loads.json'))
M = np.load(f'{D}/{STEM}_mesh.npz'); X, conn, tags = M['xyz'], M['conn'], M['tags']
idx = {int(t): i for i, t in enumerate(tags)}
N = len(X)
def parse(fn):
    steps = []; cur = None; blk = None
    for line in open(fn, errors='replace'):
        if line.startswith(' -4'):
            name = line.split()[1]; blk = name; cur = {} ; steps.append((name, cur))
        elif line.startswith(' -1') and blk in ('DISP', 'STRESS'):
            nid = int(line[3:13]); vals = [float(line[13+12*k:25+12*k]) for k in range((len(line.rstrip())-13)//12)]
            cur[nid] = vals
        elif line.startswith(' -3'): blk = None
    return steps
steps = parse(f'{D}/{STEM}.frd')
U = [s for n, s in steps if n == 'DISP']; S = [s for n, s in steps if n == 'STRESS']
names = __import__('os').environ.get('CASES', ','.join(L['cases'])).split(',')
assert len(U) == len(names) and len(S) == len(names), (len(U), len(S))
MAT = {'6061-T6': dict(E=68.9, Sy=276, Su=310, rho=2.70, Se=96.5*0.85),
       '7075-T6': dict(E=71.7, Sy=503, Su=572, rho=2.81, Se=159*0.85)}
# exclude constraint/load-introduction singularities: nodes within 3 mm of a supported/loaded hole set
deck = open(f'{D}/{STEM}.inp').read()
def nset(name):
    part = deck.split(f'*NSET, NSET={name}\n')[1].split('*')[0]
    return np.array([int(l.rstrip(',')) - 1 for l in part.split()], int)
sing = np.zeros(N, bool)
from scipy.spatial import cKDTree
tree = cKDTree(X)
for s in ('STRUTO', 'STRUTI', 'EYEL', 'EYER', 'EYET', 'EAR1', 'EAR2', 'SEAT'):
    for lst in tree.query_ball_point(X[nset(s)], 3.0): sing[lst] = True
vol = 0.0
P = X[conn[:, :4].ravel() if False else [[idx[int(t)] for t in c[:4]] for c in conn]]
a, b, c_, d = P[:, 0], P[:, 1], P[:, 2], P[:, 3]
vol = np.abs(np.einsum('ij,ij->i', np.cross(b - a, c_ - a), d - a)).sum() / 6
res = dict(volume_mm3=vol, mass_kg={k: vol * m['rho'] / 1e6 for k, m in MAT.items()}, mesh=dict(nodes=N, tets=len(conn)), cases={})
cells = [('tetra10', np.array([[idx[int(t)] for t in c] for c in conn])[:, [0,1,2,3,4,5,6,7,9,8]])]
for k, name in enumerate(names):
    s = np.zeros((N, 6)); u = np.zeros((N, 3))
    for nid, v in S[k].items():
        if nid <= N: s[nid-1] = v[:6]
    for nid, v in U[k].items():
        if nid <= N: u[nid-1] = v[:3]
    sx, sy, sz, txy, tyz, tzx = s.T
    vm = np.sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2) + 3*(txy**2 + tyz**2 + tzx**2))
    i_raw = int(np.argmax(vm)); vm_ex = np.where(sing, 0, vm); i_ex = int(np.argmax(vm_ex))
    um = np.linalg.norm(u, axis=1)
    r = dict(vm_max_raw=float(vm[i_raw]), at_raw=X[i_raw].round(1).tolist(), vm_max=float(vm_ex[i_ex]), at=X[i_ex].round(1).tolist(),
             vm_p999=float(np.percentile(vm, 99.9)), umax_6061=float(um.max()), umax_7075=float(um.max()*68.9/71.7))
    for mk, m in MAT.items():
        if name == 'fatigue':
            sa = sm = r['vm_max'] / 2
            r[f'SF_fatigue_goodman_{mk}'] = 1 / (sa / m['Se'] + sm / m['Su'])
            r[f'SF_fatigue_reversed_{mk}'] = m['Se'] / r['vm_max']
        r[f'SF_yield_{mk}'] = m['Sy'] / r['vm_max']
    res['cases'][name] = r
    meshio.write(f'{D}/{STEM}_{name}.vtu', meshio.Mesh(X, cells, point_data={'vonMises_MPa': vm, 'U_mm': u, 'singular_zone': sing.astype(float)}))
json.dump(res, open(f'{D}/{STEM}_results.json', 'w'), indent=1)
pass
