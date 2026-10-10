"""Voxel SIMP topology optimisation of the billet knuckle (multi-load compliance, volume constraint).
Hex8 voxels, density filter, OC update, pypardiso solves. Supports/loads mirror fea_v4b.py (CalculiX deck).
usage: python topo_simp.py <target_mass_kg> <h_mm> <iters> <outstem>"""
import numpy as np, json, math, sys, time, trimesh, scipy.sparse as sp, pypardiso
from scipy.spatial import cKDTree
t0 = time.time()
MT, h, NIT, OUT = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]; LOCK = True; SW = 2.0  # stress-weight exponent
RHO_AL = 2.81e-6; E, NU = 71700.0, 0.33; PEN = 3.0; RMIN = 2.0 * h
log = open(OUT + '.log', 'w')
def say(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); log.write(s + '\n'); log.flush()
L = json.load(open('loads.json')); Rt = L['vehicle']['R_loaded'] * 1000
# ---------------- grid
lo = np.array([-120.0, -170.0, -2.0]); hi = np.array([90.0, 170.0, 156.0])
n = np.ceil((hi - lo) / h).astype(int); nx, ny, nz = n
ix, iy, iz = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing='ij')
C = lo + (np.stack([ix, iy, iz], -1).reshape(-1, 3) + 0.5) * h          # element centres
def vox_in(stl):
    m = trimesh.load(stl); v = m.voxelized(pitch=h / 2).fill(); P = v.points
    g = np.floor((P - lo) / h).astype(int); ok = np.all((g >= 0) & (g < n), 1); g = g[ok]
    occ = np.zeros(tuple(n), bool); occ[g[:, 0], g[:, 1], g[:, 2]] = True; return occ.reshape(-1)
inside = vox_in('iter/it11.stl') | vox_in('baseline/v4b_fixed.stl')
from scipy.ndimage import binary_dilation, binary_closing
env = binary_dilation(binary_closing(inside.reshape(tuple(n)), iterations=2), iterations=1).reshape(-1)
x, y, z = C.T; r = np.hypot(x, y)
def in_cyl(c, a, rad, z0, z1):
    a = np.array(a, float); a /= np.linalg.norm(a); d = C - np.array(c, float); s = d @ a
    return (np.linalg.norm(d - np.outer(s, a), axis=1) < rad) & (s >= z0) & (s <= z1)
exec(open('knuckle_billet.py').read().split("TONGUE_X")[0].replace('from build123d import *', ''))   # BORE, holes, EYES
# keep-outs: drive shaft column, bore, clamp-bracket zone (strut bolts down to 12 mm below the lower bolt: y <= -67, |x| > 15)
void = ((r < 45.0) & (z > 66.0)) | ((r < 39.6) & (z <= 66.5)) | (z < 0) | ((np.abs(x) > 15.0) & (y < -67.0) & (z > 60) & (z < 130))
for z0, z1, d in BORE: void |= (r < d / 2) & (z >= z0) & (z <= z1)
for (hx, hy) in FLANGE_HOLES: void |= in_cyl((hx, hy, 0), (0, 0, 1), FLANGE_HOLE_D / 2, 38, 82)
for (hx, hy), d, (z0, z1) in EAR_HOLES: void |= in_cyl((hx, hy, 0), (0, 0, 1), d / 2, z0 - 1, z1 + 1)
for (hy, hz), d, x0, x1 in X_HOLES: void |= in_cyl((0, hy, hz), (1, 0, 0), d / 2, x0, x1)
for k, v in EYES.items():
    void |= in_cyl(v['c'], v['axis'], v['bore'] / 2, -v['length'] / 2 - 30, v['length'] / 2 + 30)
    # eye end faces stay at v4b positions: nothing within the eye OD+6 beyond the end faces
    a = np.array(v['axis'], float); a /= np.linalg.norm(a); s = (C - np.array(v['c'])) @ a
    rad = np.linalg.norm((C - np.array(v['c'])) - np.outer(s, a), axis=1)
    void |= (rad < v['od'] / 2 + 6) & (np.abs(s) > v['length'] / 2) & (np.abs(s) < v['length'] / 2 + 30)
# non-design solid shells around every interface
nd = (r < 46.0) & (z >= 0) & (z <= 66.0)                                  # hub tube (seat wall >= 6.4 mm)
for (hx, hy) in FLANGE_HOLES: nd |= in_cyl((hx, hy, 0), (0, 0, 1), 11.5, 62, 82)
for (hx, hy), d, (z0, z1) in EAR_HOLES: nd |= in_cyl((hx, hy, 0), (0, 0, 1), 12.0, z0, z1)
nd |= in_cyl((0, 0.9, 72.5), (1, 0, 0), 15.0, 38, 72)                     # side boss
nd |= (np.abs(x) <= 15.0) & (y <= -67.0) & (y >= -166.0) & (z >= 72) & (z <= 116)   # strut clamp lands (solid)
for k, v in EYES.items(): nd |= in_cyl(v['c'], v['axis'], v['od'] / 2, -v['length'] / 2, v['length'] / 2)
def seg_box(A, B, w, hgt):
    A = np.array(A, float); B = np.array(B, float); u = (B - A) / np.linalg.norm(B - A); L = np.linalg.norm(B - A)
    zz = np.array([0, 0, 1.0]); nrm = zz - u * u.dot(zz); nrm /= np.linalg.norm(nrm); side = np.cross(u, nrm)
    d = C - A; s_ = d @ u
    return (s_ >= 0) & (s_ <= L) & (np.abs(d @ side) <= w / 2) & (np.abs(d @ nrm) <= hgt / 2)
if LOCK:
    for A_, B_ in (((4, -62, 96), (60, 0, 100)), ((60, 0, 100), EYES['right_eye']['c']), ((-4, -60, 92), (-62, 10, 80)), ((-62, 10, 80), EYES['left_eye']['c'])):
        nd |= seg_box(A_, B_, 24.0, 30.0) & env
    ex1, ey1 = -101.5, 29.0; rr1 = math.hypot(ex1, ey1); u1 = (ex1 / rr1, ey1 / rr1)
    nd |= seg_box((u1[0]*35, u1[1]*35, 61), (ex1 - u1[0]*16, ey1 - u1[1]*16, 61), 24.0, 42.0) & env
    env |= nd
act = env & ~void; nd &= act | (nd & ~void)
act |= nd & ~void; nd &= act
des = act & ~nd
ea = np.where(act)[0]; ne = len(ea); isnd = nd[ea]
say(f'grid {nx}x{ny}x{nz} h={h}: active {ne}, non-design {isnd.sum()}, design {(~isnd).sum()}  ({time.time()-t0:.0f}s)')
Vnd = isnd.sum() * h**3; Vd = (~isnd).sum() * h**3
vf = (MT / RHO_AL - Vnd) / Vd; say(f'target {MT} kg -> design volfrac {vf:.3f} (non-design {Vnd*RHO_AL:.3f} kg, full envelope {(Vnd+Vd)*RHO_AL:.3f} kg)')
assert 0.02 < vf < 1
# ---------------- FE
ex, ey, ez = np.unravel_index(ea, tuple(n))
def nid(i, j, k): return (i * (ny + 1) + j) * (nz + 1) + k
corners = [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]
en = np.stack([nid(ex+a, ey+b, ez+c) for a, b, c in corners], 1)
un, inv = np.unique(en, return_inverse=True); en = inv.reshape(-1, 8); nn = len(un)
ui, uj, uk = np.unravel_index(un, (nx + 1, ny + 1, nz + 1)); XN = lo + np.stack([ui, uj, uk], 1) * h
def hex_ke():
    D = E / ((1 + NU) * (1 - 2 * NU)) * np.array([[1-NU,NU,NU,0,0,0],[NU,1-NU,NU,0,0,0],[NU,NU,1-NU,0,0,0],[0,0,0,(1-2*NU)/2,0,0],[0,0,0,0,(1-2*NU)/2,0],[0,0,0,0,0,(1-2*NU)/2]])
    xi = np.array(corners, float) * 2 - 1; K = np.zeros((24, 24)); g = 1 / math.sqrt(3)
    for a in (-g, g):
        for b in (-g, g):
            for c in (-g, g):
                dN = np.array([[xi[i,0]*(1+b*xi[i,1])*(1+c*xi[i,2]), xi[i,1]*(1+a*xi[i,0])*(1+c*xi[i,2]), xi[i,2]*(1+a*xi[i,0])*(1+b*xi[i,1])] for i in range(8)]) / 8
                dX = dN * (2 / h); B = np.zeros((6, 24))
                for i in range(8):
                    B[0,3*i], B[1,3*i+1], B[2,3*i+2] = dX[i]
                    B[3,3*i], B[3,3*i+1] = dX[i,1], dX[i,0]; B[4,3*i+1], B[4,3*i+2] = dX[i,2], dX[i,1]; B[5,3*i], B[5,3*i+2] = dX[i,2], dX[i,0]
                K += B.T @ D @ B * (h / 2) ** 3
    return K
KE = hex_ke()
edof = (3 * en[:, :, None] + np.arange(3)).reshape(ne, 24)
I = np.repeat(edof, 24, 1).ravel(); J = np.tile(edof, (1, 24)).ravel()
# ---------------- supports and loads (mirror fea_v4b.py)
solid_nodes = np.zeros(nn, bool); solid_nodes[np.unique(en)] = True
def ring_nodes(c, a, rad, half):
    a = np.array(a, float); a /= np.linalg.norm(a); d = XN - np.array(c, float); s = d @ a
    rr = np.linalg.norm(d - np.outer(s, a), axis=1)
    return np.where((rr >= rad - 0.01) & (rr <= rad + 1.01 * h) & (np.abs(s) <= half + 0.01))[0]
def eye_ax(v): return v['axis']
S = {'SEAT': ring_nodes((0, 0, 29.75), (0, 0, 1), 37.0, 16.25), 'STRUTO': ring_nodes((-2.5, -147.5, 96.2), (1, 0, 0), 7.15, 15.0),
     'STRUTI': ring_nodes((-2.5, -79.0, 93.7), (1, 0, 0), 7.0, 15.0), 'EYEL': ring_nodes(EYES['left_eye']['c'], EYES['left_eye']['axis'], 17.5, 13),
     'EYER': ring_nodes(EYES['right_eye']['c'], EYES['right_eye']['axis'], 17.75, 13), 'EYET': ring_nodes(EYES['top_eye']['c'], EYES['top_eye']['axis'], 20.0, 20),
     'EAR1': ring_nodes((-101.5, 29.0, 52.0), (0, 0, 1), 5.0, 12.0), 'EAR2': ring_nodes((-41.0, -97.0, 54.5), (0, 0, 1), 4.5, 15.5)}
say('node sets', {k: len(v) for k, v in S.items()}); assert all(len(v) > 8 for v in S.values())
fixed = np.concatenate([3*S['STRUTO'], 3*S['STRUTO']+1, 3*S['STRUTO']+2, 3*S['STRUTI'], 3*S['STRUTI']+1, 3*S['STRUTI']+2, 3*S['EYEL']+2, 3*S['EYER']+2, 3*S['EYET']])
free = np.setdiff1d(np.arange(3 * nn), fixed)
zc, zp = 29.75, 20.0; cases = list(L['cases']); Fm = np.zeros((3 * nn, len(cases)))
sn = S['SEAT']; dd = XN[sn] - XN[sn].mean(0); Jm = sum(np.dot(d, d) * np.eye(3) - np.outer(d, d) for d in dd)
for k, name in enumerate(cases):
    c = L['cases'][name]; F = np.array([-c['Fx'], -c['Fz'], c['Fy']]); rv = np.array([0.0, Rt, zp - zc]); Mo = np.cross(rv, F)
    Mz = Mo[2]; Mo[2] = 0.0; Mo = Mo - np.cross(XN[sn].mean(0) - np.array([0, 0, zc]), F)   # move moment to the seat-node centroid
    w = np.linalg.solve(Jm, Mo); f = F / len(sn) + np.cross(w, dd)
    for i, node in enumerate(sn): Fm[3*node:3*node+3, k] += f[i]
    if c['brake']:
        for s_, ctr in (('EAR1', (-101.5, 29.0)), ('EAR2', (-41.0, -97.0))):
            p = np.array(ctr); rr = np.linalg.norm(p); t = np.array([-p[1], p[0]]) / rr; Fi = (Mz / 2 / rr) * t / len(S[s_])
            for node in S[s_]: Fm[3*node, k] += Fi[0]; Fm[3*node+1, k] += Fi[1]
# ---------------- filter
tree = cKDTree(C[ea]); pairs = tree.query_pairs(RMIN, output_type='ndarray')
dist = np.linalg.norm(C[ea][pairs[:, 0]] - C[ea][pairs[:, 1]], axis=1); wgt = RMIN - dist
H = sp.coo_matrix((np.r_[wgt, wgt, np.full(ne, RMIN)], (np.r_[pairs[:, 0], pairs[:, 1], np.arange(ne)], np.r_[pairs[:, 1], pairs[:, 0], np.arange(ne)])), shape=(ne, ne)).tocsr()
Hs = np.asarray(H.sum(1)).ravel()
say(f'setup done {time.time()-t0:.0f}s, dofs {len(free)}')
# ---------------- SIMP loop
xd = np.where(isnd, 1.0, vf); xp = xd.copy(); c0 = None; hist = []
for it in range(NIT):
    Ee = 1e-6 + xp ** PEN * (1 - 1e-6)
    K = sp.coo_matrix(((KE.ravel()[None, :] * Ee[:, None]).ravel(), (I, J)), shape=(3 * nn, 3 * nn)).tocsr()
    Kf = K[free][:, free]; U = np.zeros((3 * nn, len(cases)))
    U[free] = pypardiso.spsolve(Kf, Fm[free])
    ce = np.stack([np.einsum('ij,jk,ik->i', U[edof, k], KE, U[edof, k]) for k in range(len(cases))], 1)
    comp = (Ee[:, None] * ce).sum(0)
    if c0 is None: c0 = comp.copy()
    # centre-point stresses (B at xi=0) for each case -> p-norm von Mises (relaxed: rho^0.5 * sigma_solid)
    if it == 0:
        g0 = np.array(corners, float) * 2 - 1; dN0 = g0 / 8 * (2 / h); B0 = np.zeros((6, 24))
        for i_ in range(8):
            B0[0,3*i_], B0[1,3*i_+1], B0[2,3*i_+2] = dN0[i_]; B0[3,3*i_], B0[3,3*i_+1] = dN0[i_,1], dN0[i_,0]
            B0[4,3*i_+1], B0[4,3*i_+2] = dN0[i_,2], dN0[i_,1]; B0[5,3*i_], B0[5,3*i_+2] = dN0[i_,2], dN0[i_,0]
        Dm = E / ((1 + NU) * (1 - 2 * NU)) * np.array([[1-NU,NU,NU,0,0,0],[NU,1-NU,NU,0,0,0],[NU,NU,1-NU,0,0,0],[0,0,0,(1-2*NU)/2,0,0],[0,0,0,0,(1-2*NU)/2,0],[0,0,0,0,0,(1-2*NU)/2]])
        DB = Dm @ B0
    vmk = []
    for k in range(len(cases)):
        sg = U[edof, k] @ DB.T
        vm = np.sqrt(0.5 * ((sg[:,0]-sg[:,1])**2 + (sg[:,1]-sg[:,2])**2 + (sg[:,2]-sg[:,0])**2) + 3 * (sg[:,3]**2 + sg[:,4]**2 + sg[:,5]**2))
        vmk.append(vm * np.sqrt(xp))
    vmk = np.array(vmk).T; pn = (np.mean(vmk[xp > 0.5] ** 8, 0)) ** (1 / 8) if (xp > 0.5).any() else vmk.max(0)
    wk = (1 / c0) * (pn / pn.mean()) ** SW; wk *= len(cases) / (wk * c0).sum() * 1.0
    cobj = float((comp * wk).sum())
    dc = -(PEN * xp ** (PEN - 1) * (1 - 1e-6))[:, None] * ce @ wk
    smax = vmk.max(1); dc *= (1 + (smax / 251.0) ** 2)      # stress-aware: favour material where the relaxed vM exceeds the SF-2 allowable
    dc = np.asarray(H @ (dc / Hs)).ravel() if False else np.asarray(H @ (xd * dc)).ravel() / Hs / np.maximum(xd, 1e-3)
    dv = np.ones(ne); dc[isnd] = 0
    l1, l2, mv = 1e-9, 1e9, 0.15; xold = xd.copy()
    while (l2 - l1) / (l1 + l2) > 1e-4:
        lm = 0.5 * (l1 + l2)
        xn = np.clip(xd * np.sqrt(np.maximum(-dc, 1e-30) / lm), np.maximum(1e-3, xd - mv), np.minimum(1.0, xd + mv)); xn[isnd] = 1.0
        xpn = np.asarray(H @ xn).ravel() / Hs; xpn[isnd] = 1.0
        if xpn[~isnd].mean() > vf: l1 = lm
        else: l2 = lm
    xd = xn; xp = xpn; ch = np.abs(xd - xold).max()
    m_solid = ((xp > 0.5).sum()) * h**3 * RHO_AL
    hist.append(dict(it=it, obj=cobj, change=float(ch), mass_thr=m_solid, comp=(comp / c0).round(3).tolist()))
    say(f'pnorm vM {np.round(pn,0).tolist()} ', end='') if False else None
    say(f'it {it:3d} pn {np.round(pn).astype(int).tolist()} obj {cobj:.4f} ch {ch:.3f} mass(rho>0.5) {m_solid:.3f} kg  c/c0 {np.round(comp/c0,3).tolist()}  {time.time()-t0:.0f}s')
    np.savez_compressed(OUT + '.npz', n=n, lo=lo, h=h, ea=ea, rho=xp, isnd=isnd)
    if it > 15 and ch < 0.01: break
json.dump(dict(target=MT, vf=vf, h=h, rmin=RMIN, pen=PEN, hist=hist, cases=cases), open(OUT + '.json', 'w'))
say('DONE', f'{time.time()-t0:.0f}s')
