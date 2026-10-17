"""Render the two 2D pictures Dan wants for every part: a BOTTOM view and a TRIMETRIC view.

Same camera and style for every model, so pictures can be compared. Pure matplotlib painter's
algorithm on a triangle mesh: no GPU, no Fusion. Needs: trimesh, numpy, matplotlib (+ build123d only
when the input is a STEP).

  python tools/render_views.py MODEL.step [MORE.step ...] --out outdir --name "Short title"

Every input file is one part of the model; each gets its own grey shade so assemblies read clearly.
Writes  <out>/2d_bottom_view.png  and  <out>/2d_trimetric.png.

Axis convention: the bottom view looks along -Z from the +Z side with +Y up on the page, which is the
"looking up from underneath" view when +Z is the part's top. If a part's own axes differ, pass
--bottom-dir X,Y,Z (the direction the camera looks along) and --up X,Y,Z.
The trimetric camera uses unequal axis angles (default look direction -0.62,0.58,-0.30 from the
front-right-above; change with --tri-dir).
"""
import argparse
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import PolyCollection

PALETTE = [(0.72, 0.72, 0.74), (0.85, 0.55, 0.2), (0.45, 0.55, 0.7), (0.4, 0.7, 0.45),
           (0.75, 0.45, 0.5), (0.6, 0.6, 0.35), (0.5, 0.45, 0.7), (0.35, 0.65, 0.65)]


def load_mesh(path, tol=0.05, ang=0.3):
    if path.lower().endswith((".stl", ".ply", ".obj")):
        return trimesh.load(path, force="mesh")
    from build123d import export_stl, import_step
    with tempfile.TemporaryDirectory() as d:
        tmp = os.path.join(d, "m.stl")
        export_stl(import_step(path), tmp, tolerance=tol, angular_tolerance=ang)
        return trimesh.load(tmp, force="mesh")


def paint(ax, meshes, view_dir, up_hint, title):
    vd = np.asarray(view_dir, float); vd /= np.linalg.norm(vd)
    up_hint = np.asarray(up_hint, float)
    rt = np.cross(vd, up_hint); rt /= np.linalg.norm(rt)
    up = np.cross(rt, vd)
    light = -vd + 0.6 * up + 0.3 * rt; light /= np.linalg.norm(light)
    polys, cols, depth = [], [], []
    for i, m in enumerate(meshes):
        tri = np.asarray(m.triangles); fn = np.asarray(m.face_normals)
        inten = 0.30 + 0.70 * np.clip(np.abs(fn @ light), 0, 1)
        polys += list(np.stack([tri @ rt, tri @ up], -1))
        cols += list(np.array(PALETTE[i % len(PALETTE)]) * inten[:, None])
        depth += list((tri @ vd).mean(1))
    order = np.argsort(depth)[::-1]            # far faces first
    ax.add_collection(PolyCollection([polys[k] for k in order], facecolors=[cols[k] for k in order], edgecolors="none"))
    ax.autoscale(); ax.set_aspect("equal"); ax.axis("off"); ax.set_title(title, fontsize=10)


def vec(s):
    return [float(x) for x in s.split(",")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="+")
    ap.add_argument("--out", default=".")
    ap.add_argument("--name", default="")
    ap.add_argument("--bottom-dir", default="0,0,-1")
    ap.add_argument("--up", default="0,1,0")
    ap.add_argument("--tri-dir", default="-0.62,0.58,-0.30")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    meshes = [load_mesh(p) for p in a.models]
    fig, ax = plt.subplots(figsize=(11, 11))
    paint(ax, meshes, vec(a.bottom_dir), vec(a.up), f"{a.name} - BOTTOM VIEW".strip(" -"))
    fig.savefig(os.path.join(a.out, "2d_bottom_view.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 11))
    paint(ax, meshes, vec(a.tri_dir), vec(a.up) if a.up != "0,1,0" else [0, 0, 1], f"{a.name} - TRIMETRIC".strip(" -"))
    fig.savefig(os.path.join(a.out, "2d_trimetric.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
    print("wrote", os.path.join(a.out, "2d_bottom_view.png"), "and", os.path.join(a.out, "2d_trimetric.png"))


if __name__ == "__main__":
    main()
