"""Generic test geometry and measurements for tools/blend.py (no part models).

    straight_case()  wall on a plate: straight roots (crease split at the wall corners)
    curved_case()    round boss on a cylinder: a saddle-shaped root that curves and twists
    small_round_case() wall across a 4 mm step whose two edges have r1 rounds (smaller than the blend radius)
    surface_deviation(A, B, r, pieces) -> deviation of the blend surface from the true rolling-ball surface
"""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from build123d import Box, Solid, Plane, Align, Axis, Location, Vector

C, MIN, MAX = Align.CENTER, Align.MIN, Align.MAX

def straight_case():
    plate = Box(80, 60, 10, align=(C, C, MAX))
    wall = Box(50, 6, 20, align=(C, C, MIN)).moved(Location((0, 0, -3)))
    return wall, plate, 3.0

def curved_case():
    base = Solid.make_cylinder(14, 60, Plane(origin=(-30, 0, -14), z_dir=(1, 0, 0)))
    boss = Solid.make_cylinder(6, 31, Plane(origin=(0, 0, -6)))
    return boss, base, 4.0

def small_round_case(round_r=1.0):
    lo = Box(80, 60, 10, align=(C, C, MAX))
    hi = Box(40, 60, 4, align=(MIN, C, MIN))
    P = (lo + hi).solids()[0]
    es = [e for e in P.edges() if abs(e.center().X) < 1e-6 and abs(abs(e.tangent_at(0.5).Y) - 1) < 1e-6 and e.center().Z > -1e-6]
    P = P.fillet(round_r, es)
    wall = Box(50, 6, 20, align=(C, C, MIN)).moved(Location((0, 0, -3)))
    return wall, P, 2.0

CASES = {"straight": straight_case, "curved": curved_case, "small_round": small_round_case}

def truth_centres(A, B, r, ds=0.1):
    """Dense true rolling-ball samples (ball centre, tangent normals) along every crease loop."""
    import blend as bl
    dA, dB = bl.Dist(A), bl.Dist(B); out = []
    for lp in bl.crease_loops(A, B):
        n = max(64, int(lp.length / ds)); prev = None
        for i in range(n):
            s, _ = bl.ball_sample(lp, (i + 0.5) / n, A, B, r, dA, dB, prev)
            if s is not None: out.append(s); prev = s
    return out

def _arc_test(P, centres, nA, nB, r, tree, edge_deg=8.0):
    d, idx = tree.query(P, k=8)
    best = np.full(len(P), np.inf); bi = np.zeros(len(P), int)
    for k in range(idx.shape[1]):
        dd = np.linalg.norm(P - centres[idx[:, k]], axis=1)
        m = dd < best; best[m] = dd[m]; bi[m] = idx[m, k]
    v = (P - centres[bi]) / best[:, None]
    a = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", v, -nA[bi]), -1, 1)))
    b = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", v, -nB[bi]), -1, 1)))
    th = np.degrees(np.arccos(np.clip(np.einsum("ij,ij->i", nA[bi], nB[bi]), -1, 1)))
    on = (np.abs(a + b - th) < 2.0) & (a > edge_deg) & (b > edge_deg) & (np.abs(best - r) < 0.3 * r)
    return best - r, on

def surface_deviation(A, B, r, pieces, truth=None, n_arc=15, along_per_mm=8):
    """Signed deviation (mm) of the blend's arc surface from the true rolling-ball envelope (distance to the nearest
    true ball centre minus r; + = outside the ball surface). Arc faces are found automatically; points within 8 deg of
    the tangent lines (the trimmed run-out) are left out. Returns dict(max_abs, p99_abs, tooth, n_points, rows)
    where tooth = largest local peak-to-valley along the root after removing the slow trend (window ~3 mm)."""
    from scipy.spatial import cKDTree
    from scipy.ndimage import uniform_filter1d
    truth = truth or truth_centres(A, B, r)
    Cc = np.array([[s["c"].X, s["c"].Y, s["c"].Z] for s in truth])
    NA = np.array([[s["nA"].X, s["nA"].Y, s["nA"].Z] for s in truth]); NB = np.array([[s["nB"].X, s["nB"].Y, s["nB"].Z] for s in truth])
    tree = cKDTree(Cc); devs, teeth, rows = [], [], 0
    for pc in pieces:
        for f in pc.faces():
            g = np.array([[tuple(f.position_at(u, v)) for v in np.linspace(0.05, 0.95, 7)] for u in np.linspace(0.05, 0.95, 7)])
            d0, on = _arc_test(g.reshape(-1, 3), Cc, NA, NB, r, tree)
            if (on & (np.abs(d0) < 0.1)).mean() < 0.5: continue          # the arc face(s), not the closing / dip faces
            eu = np.linalg.norm(np.diff(g, axis=0), axis=2).sum(0).mean(); ev = np.linalg.norm(np.diff(g, axis=1), axis=2).sum(1).mean()
            along_len = max(eu, ev); na = int(min(6000, max(12, along_len * along_per_mm)))
            A_ = np.linspace(0.0, 1.0, na); R_ = np.linspace(0.02, 0.98, n_arc)
            if eu >= ev: grid = np.array([[tuple(f.position_at(a, b)) for a in A_] for b in R_])     # rows: arc fraction
            else: grid = np.array([[tuple(f.position_at(b, a)) for a in A_] for b in R_])
            for row in grid:
                d, on = _arc_test(row, Cc, NA, NB, r, tree)
                if on.sum() < 5: continue
                rows += 1; devs.append(d[on])
                dr = d.copy(); dr[~on] = np.nan
                # local peak-to-valley over ~3 mm windows after removing the slow trend
                good = np.where(on)[0]; seg = dr[good]
                w = max(5, int(3.0 * along_per_mm * len(seg) / max(1, na)))
                hp = seg - uniform_filter1d(seg, w, mode="nearest")
                teeth.append(float(hp.max() - hp.min()))
    if not devs: return dict(max_abs=None, p99_abs=None, tooth=None, n_points=0, rows=0)
    D = np.concatenate(devs)
    return dict(max_abs=float(np.abs(D).max()), p99_abs=float(np.percentile(np.abs(D), 99)), mean=float(D.mean()),
                tooth=float(max(teeth)), n_points=int(D.size), rows=rows)
