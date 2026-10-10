"""Six-view sheet (front/back/left/right/top/bottom + iso) of an STL or STEP, as one PNG.

    .venv/bin/python tools/views.py part.stl -o part_views.png
"""
import argparse, sys, numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def load(path):
    if path.lower().endswith((".step", ".stp")):
        from build123d import import_step, export_stl
        import tempfile, os
        tmp = os.path.join(tempfile.mkdtemp(), "p.stl"); export_stl(import_step(path), tmp, tolerance=0.05)
        path = tmp
    return trimesh.load(path, force="mesh")

VIEWS = [("Front (-Y)", 0, -90), ("Back (+Y)", 0, 90), ("Left (-X)", 0, 180), ("Right (+X)", 0, 0),
         ("Top (+Z)", 90, -90), ("Bottom (-Z)", -90, -90), ("Iso", 30, -60)]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("part"); ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--faces", type=int, default=60000, help="simplify big meshes to about this many faces")
    a = ap.parse_args()
    m = load(a.part)
    if len(m.faces) > a.faces:
        idx = np.random.default_rng(0).choice(len(m.faces), a.faces, replace=False); faces = m.faces[idx]
    else: faces = m.faces
    tris = m.vertices[faces]
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]); n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
    lo, hi = m.bounds; c = (lo + hi) / 2; r = (hi - lo).max() / 2
    fig = plt.figure(figsize=(16, 9))
    for i, (name, el, az) in enumerate(VIEWS):
        ax = fig.add_subplot(2, 4, i + 1, projection="3d", proj_type="ortho")
        ax.view_init(elev=el, azim=az)
        # light follows the camera so every view is readable
        e, z = np.radians(el), np.radians(az)
        cam = np.array([np.cos(e) * np.cos(z), np.cos(e) * np.sin(z), np.sin(e)])
        shade = 0.35 + 0.65 * np.clip(np.abs(n @ (0.7 * cam + 0.3 * light)), 0, 1)
        col = np.c_[shade * 0.62, shade * 0.66, shade * 0.72, np.ones_like(shade)]
        ax.add_collection3d(Poly3DCollection(tris, facecolors=col, edgecolor="none"))
        for f, k in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), range(3)): f(c[k] - r, c[k] + r)
        ax.set_box_aspect((1, 1, 1)); ax.set_axis_off(); ax.set_title(name)
    ext = hi - lo
    fig.add_subplot(2, 4, 8).axis("off")
    fig.text(0.78, 0.25, f"{a.part.split('/')[-1]}\nsize X {ext[0]:.1f} x Y {ext[1]:.1f} x Z {ext[2]:.1f} mm\n"
             f"volume {m.volume/1000:.1f} cm³\nwatertight: {m.is_watertight}", fontsize=12, va="center")
    out = a.out or a.part.rsplit(".", 1)[0] + "_views.png"
    fig.tight_layout(); fig.savefig(out, dpi=90); print("wrote", out)

if __name__ == "__main__": main()
