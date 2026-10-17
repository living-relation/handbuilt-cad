"""Batch edge-break chamfer of every sharp CONVEX edge of a finished solid (chamfers where fillets fail).

Tries all edges at once, then splits the set in halves recursively; a single edge that will not chamfer is skipped
and reported (never dropped silently). A result only counts when it is one valid solid that did not gain volume.

    .venv/bin/python tools/chamfer_batch.py in.step out.step [--size 0.8] [--min-angle 25] [--time 600]

Writes out.step and out.step.chamfer.json (size, chamfered count, skipped edge mid-points).
Ported from handbuilt-models knuckle_billet/baseline_al (2026-10-11).
"""
import argparse, json, math, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnc_check as C
from build123d import Vector, export_step, import_step
from OCP.BRepClass3d import BRepClass3d_SolidClassifier


def convex_keys(part, size, amin):
    """Mid-points of the sharp convex edges (dihedral >= amin deg) long enough to take a `size` chamfer."""
    P = C.Part.__new__(C.Part); P.solid = part; P.clf = BRepClass3d_SolidClassifier(part.wrapped); ks = []
    for e, (f1, f2) in C.edge_faces(part):
        if e.length < 2 * size + 0.5: continue
        p = e.position_at(0.5)
        try: n1, n2 = f1.normal_at(p), f2.normal_at(p)
        except Exception: continue
        if math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2))))) < amin: continue
        eps = min(0.05, 0.1 * e.length)
        if P.inside(p - n1 * eps + n2 * eps) and P.inside(p - n2 * eps + n1 * eps): continue   # concave
        ks.append((round(p.X, 2), round(p.Y, 2), round(p.Z, 2)))
    return ks


def edges_at(part, ks):
    E = part.edges()
    return [min(E, key=lambda e: (e.position_at(0.5) - Vector(*k)).length) for k in ks]


def _ok(s, v0):
    return s is not None and s.is_valid and len(s.solids()) == 1 and s.volume < v0 + 1e-6


def chamfer_batch(part, size=0.8, amin=25.0, tmax=600.0):
    """Returns (part, done_keys, skipped_keys)."""
    t0 = time.time(); done, skipped = [], []

    def attempt(part, ks):
        if not ks or time.time() - t0 > tmax:
            skipped.extend(ks); return part
        try:
            s = part.chamfer(size, None, edges_at(part, ks)); s = s.solids()[0] if _ok(s, part.volume) else None
        except Exception:
            s = None
        if s is not None:
            done.extend(ks); return s
        if len(ks) == 1:
            skipped.extend(ks); return part
        h = len(ks) // 2; part = attempt(part, ks[:h]); return attempt(part, ks[h:])

    return attempt(part, convex_keys(part, size, amin)), done, skipped


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    a.add_argument('src'); a.add_argument('out')
    a.add_argument('--size', type=float, default=0.8); a.add_argument('--min-angle', type=float, default=25.0)
    a.add_argument('--time', type=float, default=600.0)
    g = a.parse_args(argv)
    t0 = time.time(); part = import_step(g.src).solids()[0]
    part, done, skipped = chamfer_batch(part, g.size, g.min_angle, g.time)
    export_step(part, g.out)
    json.dump(dict(size=g.size, chamfered=len(done), skipped=skipped), open(g.out + '.chamfer.json', 'w'))
    print('CHAMFER %.1f: %d edges chamfered, %d skipped, %.0fs, vol %.0f' % (g.size, len(done), len(skipped), time.time() - t0, part.volume))
    for k in skipped:
        print('WARNING skipped edge at', k)
    return 0


if __name__ == '__main__':
    sys.exit(main())
