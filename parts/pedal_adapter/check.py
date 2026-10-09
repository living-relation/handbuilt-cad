"""Distance check: scan points -> model surface, plus renders."""
import sys, json, numpy as np, trimesh
from common import load_scan, render
from scipy.spatial import cKDTree
s = load_scan(); m = trimesh.load("pedal_adapter.stl")
print("model", m.bounds.round(2).tolist(), "watertight", m.is_watertight)
P = np.asarray(s.vertices)
# area-weight each scan vertex by its share of face area so dense patches don't dominate
w = np.zeros(len(P)); np.add.at(w, s.faces.ravel(), np.repeat(s.area_faces / 3, 3))
_, d, _ = trimesh.proximity.closest_point(m, P)
d = np.abs(d)
def wpct(x, q):
    o = np.argsort(x); c = np.cumsum(w[o]); c /= c[-1]; return float(np.interp(q / 100, c, x[o]))
stats = {"median_mm": wpct(d, 50), "p95_mm": wpct(d, 95), "max_mm": float(d.max()),
         "within_0.2_pct": float(w[d <= 0.2].sum() / w.sum() * 100), "within_0.5_pct": float(w[d <= 0.5].sum() / w.sum() * 100),
         "within_1.0_pct": float(w[d <= 1.0].sum() / w.sum() * 100), "n_points": int(len(P)), "weighting": "scan surface area"}
print(json.dumps(stats, indent=1)); json.dump(stats, open("check_stats.json", "w"), indent=1)
np.save("check_dist.npy", d)
# far-off clusters (> 1 mm)
far = d > 1.0
if far.any():
    import networkx as nx
    e = s.edges_unique; e = e[far[e[:, 0]] & far[e[:, 1]]]
    g = nx.Graph(); g.add_nodes_from(np.where(far)[0]); g.add_edges_from(e.tolist())
    comps = sorted(nx.connected_components(g), key=lambda c: -w[list(c)].sum())
    for c in comps[:15]:
        c = list(c); q = P[c]
        print("far area %6.1f mm2  ctr %s  max %.2f  bbox %s..%s" % (w[c].sum(), q.mean(0).round(1), d[c].max(), q.min(0).round(1), q.max(0).round(1)))
out = r"C:\Users\danie\agent-tools\pedal-parametric\work_"
tag = sys.argv[1] if len(sys.argv) > 1 else "chk"
render([(s, None)], out + tag + "_dist.png", views=("iso", "iso2", "isob", "isob2"), size=(650, 600), scalar=np.minimum(d, 2.0), cmap_range=(0, 2.0), bar_title="mm")
render([(s, None)], out + tag + "_dist2.png", views=("top", "bottom", "right", "left"), size=(650, 600), scalar=np.minimum(d, 2.0), cmap_range=(0, 2.0), bar_title="mm")
render([(m, (0.62, 0.7, 0.82))], out + tag + "_model.png", views=("iso", "iso2", "isob", "isob2"), size=(650, 600))
