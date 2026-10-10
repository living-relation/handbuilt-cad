"""Interactive 3D viewer: writes a single HTML file you can open in any web browser (spin, zoom, pan).

    .venv/bin/python tools/viewer.py part.stl -o part.html
"""
import argparse, trimesh
from trimesh.viewer.notebook import scene_to_html

ap = argparse.ArgumentParser(); ap.add_argument("part", nargs="+"); ap.add_argument("-o", "--out", default="viewer.html")
a = ap.parse_args()
scene = trimesh.Scene()
for p in a.part:
    if p.lower().endswith((".step", ".stp")):
        from build123d import import_step, export_stl
        import tempfile, os
        t = os.path.join(tempfile.mkdtemp(), "p.stl"); export_stl(import_step(p), t, tolerance=0.05); p = t
    scene.add_geometry(trimesh.load(p, force="mesh"))
open(a.out, "w").write(scene_to_html(scene)); print("wrote", a.out, "- open it in a web browser")
