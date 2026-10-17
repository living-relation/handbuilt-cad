"""Mesh / solid sanity check for print files (MJF/SLS/FDM): watertight, non-manifold edges, solid count, zero-volume slivers.
Usage: python mesh_check.py part.step|part.stl [--json out.json]"""
import os, sys, json, argparse
os.environ.setdefault('PYVISTA_OFF_SCREEN', 'true')
import pyvista as pv
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'render'))
from smooth_render import to_mesh

def check(path):
    r = {'file': path}
    if not path.lower().endswith('.stl'):
        from build123d import import_step
        s = import_step(path); sol = s.solids()
        r['solids'] = len(sol); r['valid'] = all((x.is_valid() if callable(x.is_valid) else x.is_valid) for x in sol)
        r['volumes'] = [round(x.volume, 3) for x in sol]
        r['tiny_faces'] = sum(1 for x in sol for f in x.faces() if f.area < 0.01)
    m = to_mesh(path).clean()
    r['open_edges'] = int(m.n_open_edges)
    r['non_manifold_edges'] = int(m.extract_feature_edges(boundary_edges=False, feature_edges=False, manifold_edges=False, non_manifold_edges=True).n_cells)
    r['bodies'] = int(m.connectivity().point_data['RegionId'].max() + 1)
    r['pass'] = r['open_edges'] == 0 and r['non_manifold_edges'] == 0 and r.get('valid', True) and r.get('tiny_faces', 0) == 0
    return r

if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('src'); a.add_argument('--json'); g = a.parse_args()
    r = check(g.src); print(json.dumps(r, indent=1))
    if g.json: json.dump(r, open(g.json, 'w'), indent=1)
    sys.exit(0 if r['pass'] else 1)
