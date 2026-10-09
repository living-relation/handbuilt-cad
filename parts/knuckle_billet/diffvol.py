import gmsh, trimesh, numpy as np
m=trimesh.load('baseline/v4b_fixed.stl'); lo,hi=m.bounds
rng=np.random.default_rng(1); P=rng.uniform(lo,hi,(60000,3))
inF=m.contains(P)
gmsh.initialize(); gmsh.option.setNumber("General.Terminal",0)
gmsh.model.occ.importShapes('/workspace/handbuilt/knuckle/v4b/knuckle.step'); gmsh.model.occ.synchronize()
Q=P[inF]; inS=np.array(gmsh.model.isInside(3,1,Q.ravel().tolist(),parametric=False) if False else [gmsh.model.isInside(3,1,list(q)) for q in Q])>0
extra=Q[~inS]; boxvol=np.prod(hi-lo)
print('fixed-only pts', len(extra), 'of', inF.sum(), 'est extra vol', len(extra)/len(P)*boxvol)
if len(extra):
    from collections import Counter
    print('x', np.percentile(extra[:,0],[5,50,95]).round(1), 'y', np.percentile(extra[:,1],[5,50,95]).round(1), 'z', np.percentile(extra[:,2],[5,50,95]).round(1))
    r=np.hypot(extra[:,0],extra[:,1]); print('r from hub axis pct', np.percentile(r,[5,50,95]).round(1))
