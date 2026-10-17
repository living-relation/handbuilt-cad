import gmsh, numpy as np, sys, json, time
step, out, smax = sys.argv[1], sys.argv[2], float(sys.argv[3])
t = time.time(); gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.occ.importShapes(step); gmsh.model.occ.synchronize()
for k, v in (("Mesh.MeshSizeMax", smax), ("Mesh.MeshSizeMin", 1.5), ("Mesh.MeshSizeFromCurvature", 10), ("Mesh.Algorithm", int(__import__("os").environ.get("ALG2D", 6))), ("Mesh.Algorithm3D", int(__import__("os").environ.get("ALG3D", 10))),
             ("Mesh.ElementOrder", 2), ("Mesh.HighOrderOptimize", 0), ("Mesh.SecondOrderLinear", 1), ("Mesh.Optimize", 1), ("General.NumThreads", 8)): gmsh.option.setNumber(k, v)
gmsh.model.mesh.generate(3)
nt, xyz, _ = gmsh.model.mesh.getNodes(); xyz = xyz.reshape(-1, 3)
et, _, en = gmsh.model.mesh.getElements(3); i = list(et).index(11); conn = np.array(en[i], dtype=np.int64).reshape(-1, 10)
used = np.unique(conn); m = np.isin(nt, used)
np.savez_compressed(out, tags=nt[m], xyz=xyz[m], conn=conn)
vol = sum(gmsh.model.occ.getMass(*v) for v in gmsh.model.getEntities(3))
print(json.dumps(dict(nodes=int(m.sum()), tets=len(conn), vol=vol, seconds=round(time.time() - t))))
