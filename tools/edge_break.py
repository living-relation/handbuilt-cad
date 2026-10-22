"""Edge break: fillet the straight edges of a solid one at a time, keeping only results that stay one valid solid.

Kernel fillet() on all edges at once often fails on real parts. This tries each straight edge on its own,
so a few bad edges don't block the rest.

usage: python tools/edge_break.py <in.step> <out_stem> <radius_mm> [--min-len 4] [--time-cap 600] [--density 2.81e-6] [--stl] [--allow-multi]
writes <out_stem>.step (plus <out_stem>.stl only with --stl) and prints edges ok / failed, volume and (with --density, kg/mm^3) mass.
"""
import argparse
import time

from build123d import GeomType, export_step, export_stl, fillet, import_step


def edge_break(part, radius, min_len=4.0, time_cap=600.0, match_tol=0.05, allow_multi=False):
    """Return (part, ok, failed). Straight edges longer than min_len are filleted one by one; a fillet is kept only if
    the result is a single valid solid. Edges are re-found by their centre after each change (tolerance match_tol)."""
    if hasattr(part, "solids") and part.solids():
        sols = part.solids()
        if len(sols) > 1:
            if not allow_multi:
                raise ValueError(f"input has {len(sols)} solids; edge_break works on one solid (pass allow_multi=True / --allow-multi to use the largest)")
            print(f"WARNING: input has {len(sols)} solids; using the largest only", flush=True)
        part = max(sols, key=lambda s: s.volume)
    t0 = time.time()
    ok = failed = 0
    centres = [e.center() for e in part.edges() if e.geom_type == GeomType.LINE and e.length > min_len]
    for c in centres:
        if time.time() - t0 > time_cap:
            print("time cap reached", flush=True)
            break
        edges = [x for x in part.edges() if (x.center() - c).length < match_tol]
        if not edges:
            continue
        try:
            trial = fillet(edges, radius)
            if len(trial.solids()) == 1 and trial.is_valid:
                part = trial.solids()[0]
                ok += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    return part, ok, failed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src")
    ap.add_argument("out_stem")
    ap.add_argument("radius", type=float)
    ap.add_argument("--min-len", type=float, default=4.0, help="only straight edges longer than this (mm)")
    ap.add_argument("--time-cap", type=float, default=600.0, help="stop trying new edges after this many seconds")
    ap.add_argument("--density", type=float, default=None, help="kg/mm^3 for a mass printout, e.g. 2.81e-6 for 7075")
    ap.add_argument("--stl", action="store_true", help="also write <out_stem>.stl (STEP only by default)")
    ap.add_argument("--allow-multi", action="store_true", help="input with several solids: warn and use the largest instead of stopping")
    a = ap.parse_args(argv)
    try:
        part, ok, failed = edge_break(import_step(a.src), a.radius, a.min_len, a.time_cap, allow_multi=a.allow_multi)
    except ValueError as ex:
        raise SystemExit(f"edge_break: {ex}")
    msg = f"edge breaks ok {ok} failed {failed} vol {part.volume:.1f}"
    if a.density:
        msg += f" mass_kg {part.volume * a.density:.4f}"
    print(msg, flush=True)
    export_step(part, a.out_stem + ".step")
    if a.stl:
        export_stl(part, a.out_stem + ".stl", tolerance=0.05, angular_tolerance=0.2)


if __name__ == "__main__":
    main()
