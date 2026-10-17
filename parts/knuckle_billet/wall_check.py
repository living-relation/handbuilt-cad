"""Minimum wall thickness by inward ray casting from surface samples (trimesh). Usage: wall_check.py part.stl [n]"""
import sys, json, numpy as np, trimesh
m = trimesh.load(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 60000
pts, fi = trimesh.sample.sample_surface_even(m, n); nr = m.face_normals[fi]
o = pts - nr * 0.02
loc, ir, it = m.ray.intersects_location(o, -nr, multiple_hits=False)
d = np.full(len(pts), np.inf); d[ir] = np.linalg.norm(loc - o[ir], axis=1)
# a 'wall' is where the opposite face is roughly anti-parallel (excludes ray grazing into fillets / corners)
cosang = np.full(len(pts), 0.0); cosang[ir] = -np.einsum('ij,ij->i', m.face_normals[it], nr[ir])
w = (cosang > 0.8) & np.isfinite(d)
srt = np.argsort(d[w])[:int(__import__("os").environ.get("NT","8"))]; P = pts[w][srt]
out = dict(samples=len(pts), min_wall_mm=round(float(d[w].min()), 2), p01_mm=round(float(np.percentile(d[w], 0.1)), 2),
           frac_below_4mm=round(float((d[w] < 4.0).mean()), 5), n_below_4mm=int((d[w] < 4.0).sum()),
           thinnest=[dict(t=round(float(d[w][i]), 2), at=np.round(pts[w][i], 1).tolist()) for i in srt])
print(json.dumps(out))
