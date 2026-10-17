"""Run the project's R127 wall + attachment check (check_printed_walls.py functions) on any STL."""
import sys, importlib, json, time, trimesh
mod = importlib.import_module(sys.argv[1])          # check_printed_walls (PITCH 0.2) or cpw_p03 (PITCH 0.3)
res = {}
for p in sys.argv[2:]:
    t = time.time(); m = trimesh.load(p, force='mesh')
    w = mod.walls(m); at = mod.attachments(m)
    res[p] = dict(vol_cm3=round(m.volume / 1000, 2), W=len(w), A=None if at is None else len(at), walls=[list(map(float, g)) for g in w], attach=[list(x) for x in (at or [])])
    print(f'{p}: {m.volume/1000:.2f} cm3  W={len(w)}  A={res[p]["A"]}  ({time.time()-t:.0f}s)')
    for g in w[:30]: print('   W  x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f  (%d sections)' % tuple(g))
    for x in (at or [])[:30]: print('   A  %s: x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f  %.1f mm3' % tuple(x))
json.dump(res, open(sys.stdout.name if False else '/dev/null', 'w'))
