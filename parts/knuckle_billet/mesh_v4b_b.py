# Gmsh: v4b STEP -> 2nd-order tets (C3D10), refined by curvature at holes/fillets.
import os
MODELS_DIR = os.environ.get('MODELS_DIR', os.path.expanduser('~/models'))
KNUCKLE_V4B = os.path.join(MODELS_DIR, 'knuckle_1009', 'rev4b')
import gmsh, numpy as np, time, sys, json
SMAX = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
OUT = sys.argv[2] if len(sys.argv) > 2 else 'baseline/mesh_v4b.npz'
t = time.time(); gmsh.initialize(); gmsh.option.setNumber("General.Terminal", 1); gmsh.option.setNumber("General.Verbosity", 2)
for k,v in (("Geometry.OCCFixDegenerated",1),("Geometry.OCCFixSmallEdges",1),("Geometry.OCCFixSmallFaces",1),("Geometry.OCCSewFaces",0),("Geometry.Tolerance",1e-4)): gmsh.option.setNumber(k,v)
gmsh.model.occ.importShapes(os.path.join(KNUCKLE_V4B, 'knuckle.step')); gmsh.model.occ.synchronize()
print('healed vols', len(gmsh.model.getEntities(3)), 'surfs', len(gmsh.model.getEntities(2)), 'vol', sum(gmsh.model.occ.getMass(*v) for v in gmsh.model.getEntities(3)), flush=True)
gmsh.option.setNumber("Mesh.MeshSizeMax", SMAX); gmsh.option.setNumber("Mesh.MaxRetries", 50)
gmsh.option.setNumber("Mesh.MeshSizeMin", 0.5)
gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)   # elements per 2*pi of curvature -> refines holes/fillets
gmsh.option.setNumber("Mesh.Algorithm", 6); gmsh.option.setNumber("Mesh.Algorithm3D", 10)
gmsh.option.setNumber("Mesh.ElementOrder", 2); gmsh.option.setNumber("Mesh.HighOrderOptimize", 1)
gmsh.option.setNumber("Mesh.Optimize", 1); gmsh.option.setNumber("General.NumThreads", 8)
gmsh.model.mesh.generate(3)
nt, xyz, _ = gmsh.model.mesh.getNodes(); xyz = xyz.reshape(-1, 3)
et, etags, enodes = gmsh.model.mesh.getElements(3)
i = list(et).index(11); conn = np.array(enodes[i], dtype=np.int64).reshape(-1, 10)
np.savez_compressed(OUT, tags=nt, xyz=xyz, conn=conn)
print(json.dumps(dict(nodes=len(nt), tets=len(conn), smax=SMAX, seconds=round(time.time()-t))))
