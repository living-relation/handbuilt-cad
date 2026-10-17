from common import *
import networkx as nx
s = load_scan(); P = s.vertices; N = s.vertex_normals
d = np.load("check_dist.npy")
plate = ((P[:,1] > -8.5) & (P[:,1] < 23.5)) | ((P[:,1] > -78) & (P[:,1] < -42.5))
cand = plate & (P[:,0] > 33.0) & (P[:,0] < 37.9) & (d > 0.5) & (P[:,2] > 20)
e = s.edges_unique; e = e[cand[e[:,0]] & cand[e[:,1]]]
g = nx.Graph(); g.add_nodes_from(np.where(cand)[0]); g.add_edges_from(e.tolist())
res = []
for c in nx.connected_components(g):
    c = np.array(list(c))
    if len(c) < 25: continue
    q = P[c]
    res.append((q[:,1].mean(), q[:,2].mean(), q[:,1].max()-q[:,1].min(), q[:,2].max()-q[:,2].min(), 38.3 - q[:,0].min(), len(c)))
res.sort(key=lambda r: (r[0] < -20, -r[1], r[0]))
for r in res: print("pocket y %6.1f z %5.1f  w %4.1f h %4.1f depth %4.1f  n %d" % r)
print(len(res))
