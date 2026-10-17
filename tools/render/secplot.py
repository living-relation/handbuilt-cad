import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from build123d import *
def section(solid, plane):
    """returns (triangles list, edge polylines) in plane coords"""
    sec = solid.intersect(Face.make_rect(4000, 4000, plane))
    tris = []; edges = []
    for f in (sec.faces() if sec is not None else []):
        V, T = f.tessellate(0.02, 0.2)
        P = np.array([[plane.to_local_coords(v).X, plane.to_local_coords(v).Y] for v in V])
        tris += [P[list(t)] for t in T]
        for e in f.edges():
            q = [plane.to_local_coords(e.position_at(t)) for t in np.linspace(0, 1, 60)]
            edges.append(np.array([[p.X, p.Y] for p in q]))
    return tris, edges
def draw_section(ax, sec, color='#c9d6e3'):
    from matplotlib.collections import PolyCollection
    tris, edges = sec
    ax.add_collection(PolyCollection(tris, fc=color, ec=color, lw=0.3, hatch='///'))
    for e in edges: ax.plot(e[:, 0], e[:, 1], 'k', lw=1.2)
def iso_lines(solid, view=(1, -1, 0.8)):
    from build123d import Vector
    vis, hid = solid.project_to_viewport(Vector(*view) * 1000, viewport_up=(0, 0, 1), look_at=(0, 0, 0))
    return vis, hid
def draw_iso(ax, solid, marks, view=(1, -1, 0.8), labels=None, offs=None):
    vis, hid = iso_lines(solid, view)
    for e in vis:
        p = np.array([[q.X, q.Y] for q in e.positions(np.linspace(0, 1, 30).tolist())]) if hasattr(e,'positions') else None
        p = np.array([[e.position_at(t).X, e.position_at(t).Y] for t in np.linspace(0, 1, 20)])
        ax.plot(p[:, 0], p[:, 1], 'k', lw=0.6)
    # project marks same way: build plane from view
    d = Vector(*view).normalized(); up = Vector(0, 0, 1); x = up.cross(d).normalized() if False else d.cross(up).normalized() * -1
    pl = Plane(origin=(0, 0, 0), x_dir=x, z_dir=d)
    for i, m in enumerate(marks):
        q = pl.to_local_coords(Vector(*m))
        ax.plot(q.X, q.Y, 'o', ms=18, mfc='none', mec='r', mew=2)
        if labels: ax.annotate(labels[i], (q.X, q.Y), xytext=(offs[i] if offs else (25, 25)), textcoords='offset points', color='r', fontsize=11, weight='bold',
                               arrowprops=dict(arrowstyle='-', color='r'))
    ax.set_aspect('equal'); ax.axis('off')
