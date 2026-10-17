"""Six-view sheet (front/back/left/right/top/bottom + iso) of an STL or STEP, as one PNG.

    .venv/bin/python tools/views.py part.stl -o part_views.png
    .venv/bin/python tools/views.py part.step --six --name "My bracket"   # 6 labelled plain-grey views, no iso panel

--six    six orthographic views only (front/back/left/right/top/bottom), plain grey, no 3D iso panel.
         Drawn with a small z-buffer renderer (flat shading per face, one light fixed relative to the camera,
         dark outlines at sharp edges), so flat faces come out as one even grey without triangle seams.
--name   part name used in the view labels and the sheet title (default: the file name)
"""
import argparse, os, sys, numpy as np, trimesh, matplotlib
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

# (label, looking from, elevation, azimuth)
VIEWS = [("Front", "-Y", 0, -90), ("Back", "+Y", 0, 90), ("Left", "-X", 0, 180), ("Right", "+X", 0, 0),
         ("Top", "+Z", 90, -90), ("Bottom", "-Z", -90, -90), ("Iso", "", 30, -60)]

# --six: (label, looking from, forward = view direction, up)
SIX = [("Front", "-Y", (0, 1, 0), (0, 0, 1)), ("Back", "+Y", (0, -1, 0), (0, 0, 1)),
       ("Left", "-X", (1, 0, 0), (0, 0, 1)), ("Right", "+X", (-1, 0, 0), (0, 0, 1)),
       ("Top", "+Z", (0, 0, -1), (0, 1, 0)), ("Bottom", "-Z", (0, 0, 1), (0, 1, 0))]
LIGHT_CAM = np.array([-0.35, 0.45, 0.82])       # light in camera space (right, up, towards viewer): same for every view

def render_view(m, fwd, up, size=500, ss=2):
    """Orthographic z-buffer render of a trimesh: flat per-face grey, crease/silhouette outlines. Returns an RGB float image."""
    N = size * ss; fwd = np.array(fwd, float); up = np.array(up, float); right = np.cross(fwd, up)
    lo, hi = m.bounds; c = (lo + hi) / 2; s = 0.46 * N / (np.linalg.norm(hi - lo) / 2)
    v = m.vertices - c
    px = np.c_[v @ right * s + N / 2, N / 2 - v @ up * s]; dep = v @ fwd
    fn = m.face_normals.copy(); fn[fn @ fwd > 0] *= -1        # face the camera (z-buffer hides the far side anyway)
    l = LIGHT_CAM / np.linalg.norm(LIGHT_CAM); lw = l[0] * right + l[1] * up - l[2] * fwd
    shade = 0.22 + 0.50 * np.clip(fn @ lw, 0, 1) + 0.06 * np.clip(-(fn @ fwd), 0, 1)
    zbuf = np.full((N, N), np.inf); fid = np.full((N, N), -1)
    for i, tri in enumerate(m.faces):
        P = px[tri]; z = dep[tri]
        x0, y0 = np.maximum(np.floor(P.min(0)).astype(int), 0); x1, y1 = np.minimum(np.ceil(P.max(0)).astype(int), N - 1)
        if x1 < x0 or y1 < y0: continue
        d = (P[1, 1] - P[2, 1]) * (P[0, 0] - P[2, 0]) + (P[2, 0] - P[1, 0]) * (P[0, 1] - P[2, 1])
        if abs(d) < 1e-12: continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        a = ((P[1, 1] - P[2, 1]) * (X - P[2, 0]) + (P[2, 0] - P[1, 0]) * (Y - P[2, 1])) / d
        b = ((P[2, 1] - P[0, 1]) * (X - P[2, 0]) + (P[0, 0] - P[2, 0]) * (Y - P[2, 1])) / d
        g = 1 - a - b; inside = (a >= -1e-6) & (b >= -1e-6) & (g >= -1e-6)
        if not inside.any(): continue
        zz = a * z[0] + b * z[1] + g * z[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]; win = inside & (zz < sub)
        sub[win] = zz[win]; fid[y0:y1 + 1, x0:x1 + 1][win] = i
    img = np.ones((N, N)); hit = fid >= 0; img[hit] = shade[fid[hit]]
    # outlines: silhouette, and creases where neighbouring pixels' faces differ by > 25 deg or jump in depth
    nb = np.zeros((N, N, 3)); nb[hit] = fn[fid[hit]]; zf = np.where(hit, zbuf, np.nan)
    edge = np.zeros((N, N), bool); jump = 0.01 * N / s * 3
    for dy, dx in ((0, 1), (1, 0)):
        h1, h2 = hit[:N - dy, :N - dx], hit[dy:, dx:]
        n1, n2 = nb[:N - dy, :N - dx], nb[dy:, dx:]
        crease = (np.einsum("ijk,ijk->ij", n1, n2) < np.cos(np.radians(25))) | (np.abs(zf[:N - dy, :N - dx] - zf[dy:, dx:]) > jump)
        e = (h1 != h2) | (h1 & h2 & crease)
        edge[:N - dy, :N - dx] |= e; edge[dy:, dx:] |= e
    img[edge] = 0.25
    img = img.reshape(size, ss, size, ss).mean((1, 3))           # supersampled -> smooth edges
    return np.repeat(img[:, :, None], 3, axis=2)

def six_sheet(m, name, out):
    ext = m.bounds[1] - m.bounds[0]
    fig, axs = plt.subplots(2, 3, figsize=(15, 10.5))
    for ax, (label, frm, fwd, up) in zip(axs.flat, SIX):
        ax.imshow(render_view(m, fwd, up), vmin=0, vmax=1, interpolation="lanczos"); ax.set_axis_off()
        ax.set_title(f"{name} - {label.upper()} (FROM {frm})")
    fig.suptitle(f"{name}   |   size X {ext[0]:.1f} x Y {ext[1]:.1f} x Z {ext[2]:.1f} mm   |   "
                 f"volume {m.volume/1000:.1f} cm³   |   watertight: {m.is_watertight}", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96)); fig.savefig(out, dpi=90); print("wrote", out)

def main():
    ap = argparse.ArgumentParser(description="Picture sheet of a part: 6 orthographic views (+ iso unless --six).")
    ap.add_argument("part"); ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--faces", type=int, default=60000, help="simplify big meshes to about this many faces")
    ap.add_argument("--six", action="store_true", help="only the 6 labelled orthographic views, plain grey, no 3D iso panel")
    ap.add_argument("--name", default=None, help="part name for the labels and title (default: file name)")
    a = ap.parse_args()
    name = a.name or os.path.basename(a.part)
    m = load(a.part)
    out = a.out or a.part.rsplit(".", 1)[0] + "_views.png"
    if a.six: return six_sheet(m, name, out)                      # every face kept: no random thinning
    if len(m.faces) > a.faces:
        idx = np.random.default_rng(0).choice(len(m.faces), a.faces, replace=False); faces = m.faces[idx]
    else: faces = m.faces
    tris = m.vertices[faces]
    light = np.array([0.4, -0.5, 0.8]); light /= np.linalg.norm(light)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]); n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
    lo, hi = m.bounds; c = (lo + hi) / 2; r = (hi - lo).max() / 2
    fig = plt.figure(figsize=(16, 9))
    for i, (label, frm, el, az) in enumerate(VIEWS):
        ax = fig.add_subplot(2, 4, i + 1, projection="3d", proj_type="ortho")
        ax.view_init(elev=el, azim=az)
        # light follows the camera so every view is readable
        e, z = np.radians(el), np.radians(az)
        cam = np.array([np.cos(e) * np.cos(z), np.cos(e) * np.sin(z), np.sin(e)])
        shade = 0.35 + 0.65 * np.clip(np.abs(n @ (0.7 * cam + 0.3 * light)), 0, 1)
        col = np.c_[shade * 0.62, shade * 0.66, shade * 0.72, np.ones_like(shade)]
        ax.add_collection3d(Poly3DCollection(tris, facecolors=col, edgecolor="none"))
        for f, k in zip((ax.set_xlim, ax.set_ylim, ax.set_zlim), range(3)): f(c[k] - r, c[k] + r)
        ax.set_box_aspect((1, 1, 1)); ax.set_axis_off()
        ax.set_title(f"{label} ({frm})" if frm else label)
    ext = hi - lo
    info = (f"{name}\nsize X {ext[0]:.1f} x Y {ext[1]:.1f} x Z {ext[2]:.1f} mm\n"
            f"volume {m.volume/1000:.1f} cm³\nwatertight: {m.is_watertight}")
    fig.add_subplot(2, 4, 8).axis("off")
    fig.text(0.78, 0.25, info, fontsize=12, va="center")
    fig.tight_layout(); fig.savefig(out, dpi=90); print("wrote", out)

if __name__ == "__main__": main()
