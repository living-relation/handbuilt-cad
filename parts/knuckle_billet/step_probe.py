import gmsh, time
t=time.time(); gmsh.initialize(); gmsh.option.setNumber("General.Terminal",0)
gmsh.model.occ.importShapes('/workspace/handbuilt/knuckle/v4b/knuckle.step'); gmsh.model.occ.synchronize()
vols=gmsh.model.getEntities(3); surfs=gmsh.model.getEntities(2)
print('load s', round(time.time()-t), 'vols', len(vols), 'surfs', len(surfs), flush=True)
for v in vols: print('mass', gmsh.model.occ.getMass(*v))
