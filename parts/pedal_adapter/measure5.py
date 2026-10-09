from common import *
import trimesh.intersections as TI
s = load_scan()
a = np.radians(25); u = np.array([-np.sin(a), np.cos(a)]); v = np.array([np.cos(a), np.sin(a)])
for z in [19, 22, 28, 31, 34, 40, 48]:
    segs = TI.mesh_plane(s, plane_normal=[0,0,1], plane_origin=[0,0,z]).reshape(-1, 3)
    segs = segs[segs[:,1] > 10]
    row = []
    for x in range(-38, 40, 4):
        k = np.abs(segs[:,0]-x) < 0.4
        # exclude connector box region
        U = segs[:, :2] @ u; V = segs[:, :2] @ v
        k &= ~((U > 35) & (V > -17) & (V < 12))
        row.append(f"{segs[k,1].max():.1f}" if k.any() else "  -  ")
    print("z", z, " ".join(f"{r:>5}" for r in row))
print("x  ", " ".join(f"{x:>5}" for x in range(-38, 40, 4)))
