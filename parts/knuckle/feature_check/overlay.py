import sys, math
sys.path.insert(0, "/workspace/hbwork"); sys.path.insert(0, "/workspace/handbuilt/knuckle/v4b")
import numpy as np, trimesh
from hb_common import load_scan_hb, render
import knuckle as K
s = load_scan_hb("knuckle", "/workspace/hbwork/knuckle")
def cyl(c, a, d, L, ann=None):
    a = np.asarray(a, float); a /= np.linalg.norm(a)
    T = trimesh.geometry.align_vectors((0, 0, 1), a); T[:3, 3] = c
    m = trimesh.creation.annulus(r_min=ann, r_max=d / 2, height=L, sections=64) if ann else trimesh.creation.cylinder(radius=d / 2, height=L, sections=64)
    m.apply_transform(T); return m
RED = (0.85, 0.1, 0.1, 1.0); BLUE = (0.1, 0.35, 0.9, 0.55); ORG = (1.0, 0.55, 0.0, 0.45)
holes, bores, ods = [], [], []
for x, y in K.FLANGE_HOLES: holes.append(cyl((x, y, 60), (0, 0, 1), K.FLANGE_HOLE_D, 70))
for (x, y), d, (z0, z1) in K.EAR_HOLES: holes.append(cyl((x, y, (z0 + z1) / 2), (0, 0, 1), d, z1 - z0 + 20))
for (y, z), d, x0, x1 in K.X_HOLES: holes.append(cyl(((x0 + x1) / 2, y, z), (1, 0, 0), d, x1 - x0 + 16))
for e in K.EYES.values():
    holes.append(cyl(e["c"], e["axis"], e["bore"], e["length"] + 20))
    ods.append(cyl(e["c"], e["axis"], e["od"] + 0.6, e["length"], ann=e["od"] / 2 - 0.6))
for z0, z1, d in K.BORE[:6]:
    bores.append(cyl((0, 0, (max(z0, 0) + z1) / 2), (0, 0, 1), d, z1 - max(z0, 0), ann=d / 2 - 0.8))
ods.append(cyl((0, 0, 16), (0, 0, 1), K.HUB_OD + 0.6, 18, ann=K.HUB_OD / 2 - 0.6))
H = trimesh.util.concatenate(holes); B = trimesh.util.concatenate(bores); O = trimesh.util.concatenate(ods)
c = s.vertices.mean(0); r = np.linalg.norm(s.vertices - c, axis=1).max()
for v in ["top", "right", "iso", "bottom"]:
    render([(s, (0.78, 0.78, 0.78)), (H, RED), (B, BLUE), (O, ORG)], f"overlay_{v}.png", views=(v,), size=(1300, 1000), center=c, radius=r)
    print("wrote", v)
