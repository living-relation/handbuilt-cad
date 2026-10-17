"""Smooth-shaded STEP/STL render (pyvista offscreen). No triangle lines; optional feature edges.
Usage: python smooth_render.py part.step out.png [--view iso|top|front|right|iso_below] [--edges] [--color #9aa3ad] [--size 1600x1200]"""
import os, sys, argparse
os.environ.setdefault('PYVISTA_OFF_SCREEN', 'true')
import numpy as np, pyvista as pv
pv.OFF_SCREEN = True

def to_mesh(path, tol=0.02, ang=0.2):
    if path.lower().endswith(('.stl', '.ply', '.obj', '.vtk')):
        m = pv.read(path)
    else:
        from build123d import import_step
        vs, fs = import_step(path).tessellate(tol, ang)
        v = np.array([[p.X, p.Y, p.Z] for p in vs]); f = np.hstack([[3, *t] for t in fs])
        m = pv.PolyData(v, f)
    return m.compute_normals(split_vertices=True, feature_angle=35)

def render(path, out, view='iso', edges=False, color='#9aa3ad', size=(1600, 1200)):
    m = to_mesh(path)
    p = pv.Plotter(off_screen=True, window_size=size); p.set_background('white')
    p.add_mesh(m, color=color, smooth_shading=True, show_edges=False, specular=0.3)
    if edges: p.add_mesh(m.extract_feature_edges(35, boundary_edges=False, non_manifold_edges=False, manifold_edges=False), color='black', line_width=1.2)
    {'iso': p.view_isometric, 'top': p.view_xy, 'front': p.view_xz, 'right': p.view_yz}.get(view, p.view_isometric)()
    if view == 'iso_below': p.view_isometric(); p.camera.elevation = -35
    p.enable_parallel_projection(); p.reset_camera(); p.screenshot(out); p.close(); return out

if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('out'); a.add_argument('--view', default='iso')
    a.add_argument('--edges', action='store_true'); a.add_argument('--color', default='#9aa3ad'); a.add_argument('--size', default='1600x1200')
    g = a.parse_args(); print(render(g.src, g.out, g.view, g.edges, g.color, tuple(int(x) for x in g.size.split('x'))))
