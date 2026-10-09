from common import *
s = load_scan(); P = s.vertices; N = s.vertex_normals
a = np.radians(25); u = np.array([-np.sin(a), np.cos(a)]); v = np.array([np.cos(a), np.sin(a)])
m = (P[:,1] > 28) & (P[:,0] < -5) & (P[:,0] > -45)
q = P[m]; U = q[:,:2] @ u; V = q[:,:2] @ v
print("U range", U.min().round(2), U.max().round(2))
for uu in np.arange(30, 56, 2):
    k = np.abs(U-uu) < 0.5
    if k.sum() > 10: print("u", uu, "n", k.sum(), "v", np.round([V[k].min(), V[k].max()],2), "z", np.round([q[k,2].min(), q[k,2].max()],2))
# end face
k = U > U.max()-1.0; print("end u %.2f" % np.median(U[k]), "z", np.round([q[k,2].min(), q[k,2].max()],2), "v", np.round([V[k].min(), V[k].max()],2))
# side faces of connector via normals
Nn = N[m]; nu = Nn[:,:2] @ u; nv = Nn[:,:2] @ v
for name, sel in [("+v", nv > 0.95), ("-v", nv < -0.95), ("+z", Nn[:,2] > 0.95), ("-z", Nn[:,2] < -0.95), ("+u", nu > 0.95)]:
    k = sel & (U > 42)
    if k.sum(): print(name, k.sum(), "v med %.2f" % np.median(V[k]), "z med %.2f" % np.median(q[k,2]), "u med %.2f" % np.median(U[k]))
