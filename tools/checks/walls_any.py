"""Run the wall (W) and attachment (A) detection of check_printed_walls.py on any mesh file, without a project config.
Detection only: it lists thin spots but does not classify them (structural vs flag needs the project's wall config).
    python tools/checks/walls_any.py --min-wall 2.0 [--attach-min 3.0] [--step 0.5] [--pitch 0.2] part.stl [more.stl ...]
"""
import argparse, os, sys, time
import trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_printed_walls as CPW  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--min-wall', type=float, required=True, help='mm; no default - use the project\'s saved minimum wall')
ap.add_argument('--attach-min', type=float, default=None)
ap.add_argument('--step', type=float, default=CPW.STEP)
ap.add_argument('--pitch', type=float, default=CPW.PITCH)
ap.add_argument('files', nargs='+')
a = ap.parse_args()
for p in a.files:
    t = time.time(); m = trimesh.load(p, force='mesh')
    w = CPW.walls(m, a.min_wall, a.step)
    at = CPW.attachments(m, a.attach_min, a.pitch) if a.attach_min else None
    print(f'{p}: {m.volume/1000:.2f} cm3  W={len(w)}  A={"skipped" if at is None else len(at)}  ({time.time()-t:.0f}s)')
    for g in w[:30]: print('   W  x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f  (%d sections)' % tuple(g))
    for x in (at or [])[:30]: print('   A  %s: x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f  %.1f mm3' % tuple(x))
