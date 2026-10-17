import gmsh, numpy as np, json, time
t=time.time(); gmsh.initialize(); gmsh.option.setNumber("General.Terminal",1); gmsh.option.setNumber("General.Verbosity",2)
gmsh.merge('baseline/v4b_remesh.stl')
s=gmsh.model.getEntities(2); l=gmsh.model.geo.addSurfaceLoop([e[1] for e in s]); gmsh.model.geo.addVolume([l]); gmsh.model.geo.synchronize()
gmsh.option.setNumber("Mesh.MeshSizeMax", 4.0); gmsh.option.setNumber("Mesh.Algorithm3D", 10); gmsh.option.setNumber("General.NumThreads", 8)
gmsh.model.mesh.generate(3); gmsh.model.mesh.optimize("Netgen"); gmsh.model.mesh.optimize("Relocate3D"); gmsh.model.mesh.setOrder(2)
nt,xyz,_=gmsh.model.mesh.getNodes(); xyz=xyz.reshape(-1,3)
et,etags,enodes=gmsh.model.mesh.getElements(3); i=list(et).index(11); conn=np.array(enodes[i],dtype=np.int64).reshape(-1,10)
np.savez_compressed('baseline/mesh_remesh.npz', tags=nt, xyz=xyz, conn=conn); print(json.dumps(dict(nodes=len(nt),tets=len(conn),seconds=round(time.time()-t))))
