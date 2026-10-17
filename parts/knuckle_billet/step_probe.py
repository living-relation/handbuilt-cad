import os
MODELS_DIR = os.environ.get('MODELS_DIR', os.path.expanduser('~/models'))
KNUCKLE_V4B = os.path.join(MODELS_DIR, 'knuckle_1009', 'rev4b')
import gmsh, time
t=time.time(); gmsh.initialize(); gmsh.option.setNumber("General.Terminal",0)
gmsh.model.occ.importShapes(os.path.join(KNUCKLE_V4B, 'knuckle.step')); gmsh.model.occ.synchronize()
vols=gmsh.model.getEntities(3); surfs=gmsh.model.getEntities(2)
print('load s', round(time.time()-t), 'vols', len(vols), 'surfs', len(surfs), flush=True)
for v in vols: print('mass', gmsh.model.occ.getMass(*v))
