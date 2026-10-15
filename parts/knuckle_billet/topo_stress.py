import os
MODELS_DIR = os.environ.get('MODELS_DIR', os.path.expanduser('~/models'))
KB = os.path.join(MODELS_DIR, 'knuckle_billet_1009')  # moved part files: baseline/, iter-opt/
"""Stress-constrained voxel SIMP for the billet knuckle.
min  volume(design)   s.t.  PN_k(sigma_vM) / (c_k * S_ALLOW) <= 1  for all 5 load cases
qp-relaxed von Mises (sigma_e = xbar^q * sigma0_e, element-centre stress), p-norm aggregation per case with adaptive
normalisation c_k (PN -> max), adjoint sensitivities, density filter + Heaviside projection (beta continuation), MMA (nlopt).
Shares grid / non-design / supports / loads with topo_simp.py (exec of its setup section).
usage: python topo_stress.py validate <h>            -> voxel it11 vs CalculiX robust stress
       python topo_stress.py run <h> <evals_per_beta> <outstem>"""
import sys, numpy as np, json, time, math
MODE, H_ = sys.argv[1], sys.argv[2]
OUTS = sys.argv[4] if MODE == 'run' else 'topo/validate'
NEV = int(sys.argv[3]) if MODE == 'run' else 0
sys.argv = ['topo_simp.py', '2.0', H_, '1', OUTS]
src = open('topo_simp.py').read().split('# ---------------- SIMP loop')[0]
exec(src)
import pypardiso, scipy.sparse as sp, trimesh
S_ALLOW = float(__import__('os').environ.get('SALLOW', '230'));  # voxel corner-stress allowable (251 x ~0.92 calibration)
PS, Q, PN_P = 3.0, 0.5, 8.0
g0 = np.array(corners, float) * 2 - 1; dN0 = g0 / 8 * (2 / h); B0 = np.zeros((6, 24))
for i_ in range(8):
    B0[0,3*i_], B0[1,3*i_+1], B0[2,3*i_+2] = dN0[i_]; B0[3,3*i_], B0[3,3*i_+1] = dN0[i_,1], dN0[i_,0]
    B0[4,3*i_+1], B0[4,3*i_+2] = dN0[i_,2], dN0[i_,1]; B0[5,3*i_], B0[5,3*i_+2] = dN0[i_,2], dN0[i_,0]
Dm = E / ((1 + NU) * (1 - 2 * NU)) * np.array([[1-NU,NU,NU,0,0,0],[NU,1-NU,NU,0,0,0],[NU,NU,1-NU,0,0,0],[0,0,0,(1-2*NU)/2,0,0],[0,0,0,0,(1-2*NU)/2,0],[0,0,0,0,0,(1-2*NU)/2]])
DB = Dm @ B0
def Bat(a, b, c):
    xi = np.array(corners, float) * 2 - 1
    dN = np.array([[xi[i,0]*(1+b*xi[i,1])*(1+c*xi[i,2]), xi[i,1]*(1+a*xi[i,0])*(1+c*xi[i,2]), xi[i,2]*(1+a*xi[i,0])*(1+b*xi[i,1])] for i in range(8)]) / 8 * (2 / h)
    Bm = np.zeros((6, 24))
    for i in range(8):
        Bm[0,3*i], Bm[1,3*i+1], Bm[2,3*i+2] = dN[i]; Bm[3,3*i], Bm[3,3*i+1] = dN[i,1], dN[i,0]
        Bm[4,3*i+1], Bm[4,3*i+2] = dN[i,2], dN[i,1]; Bm[5,3*i], Bm[5,3*i+2] = dN[i,2], dN[i,0]
    return Bm
STRESS_PT = float(__import__('os').environ.get('SPT', '0'))   # 0 = centre; 1 = corners (nodal extrapolation), 0.577 = Gauss points
DBs = [Dm @ Bat(STRESS_PT * a, STRESS_PT * b, STRESS_PT * c) for a, b, c in (np.array(corners) * 2 - 1)] if STRESS_PT > 0 else [DB]
Vm = np.array([[1,-.5,-.5,0,0,0],[-.5,1,-.5,0,0,0],[-.5,-.5,1,0,0,0],[0,0,0,3,0,0],[0,0,0,0,3,0],[0,0,0,0,0,3]])
# stress-measure mask: exclude elements touching support / load node sets (+1 voxel), like the 3 mm singular zone in post
sup = np.zeros(nn, bool)
for k_, v_ in S.items(): sup[v_] = True
near = sup[en].any(1)
nb = np.zeros(nn, bool); nb[np.unique(en[near])] = True; smask = ~nb[en].any(1)
say(f'stress-measure elements {smask.sum()} of {ne}')
# junction stress-concentration factor: design elements within KT_R voxels of a non-design (interface) solid get stress x KT
KT = float(__import__('os').environ.get('KT', '1.0')); KT_R = int(__import__('os').environ.get('KT_R', '2'))
kt = np.ones(ne)
if KT > 1.0:
    import scipy.ndimage as ndi
    gnd = np.zeros(int(np.prod(n)), bool); gnd[ea[isnd]] = True
    gd = ndi.binary_dilation(gnd.reshape(tuple(n)), iterations=KT_R).reshape(-1)
    jn = gd[ea] & ~isnd; kt[jn] = KT; say(f'junction SCF {KT} on {jn.sum()} elements (r={KT_R} voxels)')
smaskf = smask * kt
def solve(xp):
    Ee = 1e-6 + xp ** PS * (1 - 1e-6)
    K = sp.coo_matrix(((KE.ravel()[None, :] * Ee[:, None]).ravel(), (I, J)), shape=(3 * nn, 3 * nn)).tocsr()
    Kf = K[free][:, free]; U = np.zeros((3 * nn, len(cases))); U[free] = pypardiso.spsolve(Kf, Fm[free]); return Kf, U, Ee
def vm0(U, k, want_db=False):
    bs = bv = None; bi = None
    for j_, DBi in enumerate(DBs):
        s_ = U[edof, k] @ DBi.T; v_ = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', s_, Vm, s_), 1e-12))
        if bv is None: bs, bv, bi = s_, v_, np.zeros(len(v_), int)
        else:
            m = v_ > bv; bs[m] = s_[m]; bv[m] = v_[m]; bi[m] = j_
    return (bs, bv, bi) if want_db else (bs, bv)
if MODE == 'validate':
    vv = trimesh.load(os.path.join(KB, 'iter-opt', 'it11.stl')).voxelized(pitch=h / 2).fill().points
    g = np.floor((vv - lo) / h).astype(int); ok = np.all((g >= 0) & (g < n), 1); g = g[ok]
    occ = np.zeros(tuple(n), bool); occ[g[:, 0], g[:, 1], g[:, 2]] = True; in11 = occ.reshape(-1)[ea] | isnd
    xp = np.where(in11, 1.0, 0.0); Kf, U, Ee = solve(xp)
    ref = json.load(open('iter/it11_summary.json')); out = {}
    for k, c in enumerate(cases):
        _, v = vm0(U, k); vs = v[in11 & smask]
        out[c] = dict(voxel_p9999=round(float(np.percentile(vs, 99.99)), 1), voxel_p999=round(float(np.percentile(vs, 99.9)), 1),
                      voxel_max=round(float(vs.max()), 1), ccx_robust=round(ref[c]['robust'], 1),
                      ratio_p9999=round(float(np.percentile(vs, 99.99)) / ref[c]['robust'], 3), ratio_p999=round(float(np.percentile(vs, 99.9)) / ref[c]['robust'], 3))
        say(c, out[c])
    json.dump(dict(h=h, mass_voxel=float(in11.sum() * h**3 * RHO_AL), cases=out), open(f'topo/validate_h{int(h)}.json', 'w'), indent=1)
    say('VALIDATE DONE'); sys.exit()
# ---------------- optimisation
import nlopt
dmask = ~isnd; nd_idx = np.where(dmask)[0]; nvar = len(nd_idx)
def project(xt, beta, eta=0.5):
    return (np.tanh(beta * eta) + np.tanh(beta * (xt - eta))) / (np.tanh(beta * eta) + np.tanh(beta * (1 - eta)))
def dproject(xt, beta, eta=0.5):
    return beta * (1 - np.tanh(beta * (xt - eta)) ** 2) / (np.tanh(beta * eta) + np.tanh(beta * (1 - eta)))
state = dict(beta=1.0, ck=np.ones(len(cases)), last=None, nev=0, hist=[])
def physical(xv):
    x = np.ones(ne); x[nd_idx] = xv
    xt = np.asarray(H @ x).ravel() / Hs; xt[isnd] = 1.0
    xp = project(xt, state['beta']); xp[isnd] = 1.0; return x, xt, xp
def evaluate(xv):
    if state['last'] is not None and np.array_equal(state['last'][0], xv): return state['last'][1]
    x, xt, xp = physical(xv); Kf, U, Ee = solve(xp)
    G = np.zeros((3 * nn, len(cases))); PN = np.zeros(len(cases)); dPNe = np.zeros((ne, len(cases))); smax = np.zeros(len(cases))
    for k in range(len(cases)):
        s, v, ix = vm0(U, k, True); se = (xp ** Q) * v * smaskf; smax[k] = se.max()
        pn = (np.sum(se ** PN_P)) ** (1 / PN_P); PN[k] = pn
        dpn_dse = pn ** (1 - PN_P) * se ** (PN_P - 1)                         # d PN / d sigma_e
        # adjoint load: d sigma_e / d u_e = xp^q * (V s)^T DB / v
        sv = s @ Vm; w = np.zeros((ne, 24))
        for j_, DBi in enumerate(DBs):
            m_ = ix == j_
            if m_.any(): w[m_] = sv[m_] @ DBi                                  # d vM / d u_e at the governing corner
        w *= (dpn_dse * xp ** Q * kt / v)[:, None]
        np.add.at(G[:, k], edof.ravel(), w.ravel())
        dPNe[:, k] = dpn_dse * Q * np.maximum(xp, 1e-6) ** (Q - 1) * v * smaskf           # explicit part
    Lm = np.zeros((3 * nn, len(cases))); Lm[free] = pypardiso.spsolve(Kf, G[free])
    for k in range(len(cases)):
        dPNe[:, k] -= PS * xp ** (PS - 1) * (1 - 1e-6) * np.einsum('ij,jk,ik->i', Lm[edof, k], KE, U[edof, k])
    # chain: xp <- xt (projection) <- x (filter)
    dxp = dproject(xt, state['beta']); dxp[isnd] = 0
    dPNx = np.asarray(H.T @ ((dPNe * dxp[:, None]) / Hs[:, None]))
    vol = xp[dmask].mean(); dvol = np.asarray(H.T @ (dxp / Hs)).ravel() / dmask.sum()
    res = dict(PN=PN, smax=smax, dPN=dPNx[nd_idx], vol=vol, dvol=dvol[nd_idx], xp=xp)
    state['last'] = (xv.copy(), res); return res
def f_obj(xv, grad):
    r = evaluate(xv)
    if grad.size: grad[:] = r['dvol']
    state['nev'] += 1
    mass = (xp_mass := (r['xp'] > 0.5).sum() * h**3 * RHO_AL)
    rat = r['smax'] / S_ALLOW; state['hist'].append(dict(ev=state['nev'], beta=state['beta'], vol=float(r['vol']), mass_thr=float(mass), smax=r['smax'].round(1).tolist(), PN=r['PN'].round(1).tolist()))
    say(f"ev {state['nev']:3d} b{state['beta']:.0f} vol {r['vol']:.4f} mass(>0.5) {mass:.3f} kg  smax/251 {np.round(rat, 2).tolist()}  {time.time()-t0:.0f}s")
    if state['nev'] % 3 == 0 and np.all(np.isfinite(r['xp'])): np.savez_compressed(OUTS + '.npz', n=n, lo=lo, h=h, ea=ea, rho=r['xp'], isnd=isnd)
    return float(r['vol'])
def make_con(k):
    def con(xv, grad):
        r = evaluate(xv); c = state['ck'][k]
        if grad.size: grad[:] = r['dPN'][:, k] * c / S_ALLOW
        return float(r['PN'][k] * c / S_ALLOW - 1.0)
    return con
xv = np.full(nvar, float(__import__('os').environ.get('X0', '0.7')))
for beta in tuple(float(b) for b in __import__("os").environ.get("BETAS", "1,2,4,8").split(",")):
    state['beta'] = beta; state['last'] = None
    SUBN = int(__import__('os').environ.get('SUBN', '10'))
    for sub in range(max(1, NEV // SUBN)):                                         # re-normalise c_k every SUBN evals (PN -> max)
        r = evaluate(xv); state['ck'] = np.where(r['PN'] > 0, r['smax'] / r['PN'], 1.0) * 0.5 + state['ck'] * 0.5 if sub or beta > 1 else r['smax'] / r['PN']
        opt = nlopt.opt(nlopt.LD_MMA, nvar); opt.set_lower_bounds(0.0); opt.set_upper_bounds(1.0)
        opt.set_min_objective(f_obj)
        for k in range(len(cases)): opt.add_inequality_constraint(make_con(k), 1e-3)
        opt.set_maxeval(SUBN); opt.set_param('inner_maxeval', 5) if hasattr(opt, 'set_param') else None
        xprev = xv.copy()
        try: xv = opt.optimize(xv)
        except Exception as ex: say('nlopt stop', type(ex).__name__, ex); xv = state['last'][0] if state['last'] else xv
        if not np.all(np.isfinite(xv)) or not np.all(np.isfinite(evaluate(xv)['smax'])):   # NaN guard (sc3 blew up at beta 16)
            say('non-finite step -> revert and end this beta stage'); xv = xprev; break
        np.savez_compressed(OUTS + f'_b{int(beta)}.npz', n=n, lo=lo, h=h, ea=ea, rho=physical(xv)[2], isnd=isnd)   # per-stage snapshot
        say(f'beta {beta} sub {sub} ck {np.round(state["ck"], 3).tolist()}')
r = evaluate(xv); np.savez_compressed(OUTS + '.npz', n=n, lo=lo, h=h, ea=ea, rho=r['xp'], isnd=isnd)
json.dump(dict(h=h, S_ALLOW=S_ALLOW, q=Q, p=PN_P, hist=state['hist']), open(OUTS + '.json', 'w'))
say('DONE', f'{time.time()-t0:.0f}s')
