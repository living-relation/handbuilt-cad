from common import *
import trimesh.grouping as G, networkx as nx
s = load_scan()
# boundary edges
e = s.edges_sorted; u, inv, cnt = np.unique(e, axis=0, return_inverse=True, return_counts=True)
b = u[cnt == 1]; print("boundary edges", len(b))
g = nx.Graph(); g.add_edges_from(b.tolist())
comps = sorted(nx.connected_components(g), key=len, reverse=True)
for c in comps[:5]:
    p = s.vertices[list(c)]; ctr = p.mean(0); w, V = np.linalg.eigh(np.cov((p-ctr).T)); n = V[:,0]
    d = (p-ctr) @ n
    print("loop n", len(c), "ctr", ctr.round(2), "normal", n.round(3), "plane rms %.2f max %.2f" % (np.sqrt((d**2).mean()), np.abs(d).max()), "bbox", p.min(0).round(1), p.max(0).round(1))
