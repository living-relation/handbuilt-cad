import trimesh, numpy as np, pymeshfix, fast_simplification as fs
m=trimesh.load('/workspace/handbuilt/knuckle/v4b/knuckle.stl', process=True); m.merge_vertices(digits_vertex=4)
def fix(v,f):
    v,f=pymeshfix.clean_from_arrays(np.ascontiguousarray(v,dtype=np.float64), np.ascontiguousarray(f,dtype=np.int32))
    return trimesh.Trimesh(v,f)
mm=fix(m.vertices,m.faces); print('fixed', mm.is_watertight, mm.volume, len(mm.faces))
v2,f2=fs.simplify(mm.vertices.astype(np.float32), mm.faces.astype(np.int32), target_reduction=0.6)
d=fix(v2,f2); print('decimated', d.is_watertight, d.volume, len(d.faces))
d.export('v4b_dec.stl')
