# chunk 16: global edge-break pass on a built STEP: fillet straight edges (r=R) one by one, keeping only results that stay one valid solid.
import sys, time
from build123d import *
src, out, R = sys.argv[1], sys.argv[2], float(sys.argv[3]); T = float(sys.argv[4]) if len(sys.argv) > 4 else 600
part = import_step(src); part = part.solids()[0] if hasattr(part, 'solids') else part
t0 = time.time(); ok = bad = 0
cents = [e.center() for e in part.edges() if e.geom_type == GeomType.LINE and e.length > 4.0]
print('candidates', len(cents), flush=True)
for c in cents:
    if time.time() - t0 > T: print('time cap'); break
    ee = [x for x in part.edges() if (x.center() - c).length < 0.05]
    if not ee: continue
    try:
        tr = fillet(ee, R)
        if len(tr.solids()) == 1 and tr.is_valid: part = tr.solids()[0]; ok += 1
        else: bad += 1
    except Exception: bad += 1
print('edge breaks ok', ok, 'failed', bad, 'vol', part.volume, 'mass7075', part.volume * 2.81e-6, flush=True)
export_step(part, out + '.step'); export_stl(part, out + '.stl', tolerance=0.05, angular_tolerance=0.2)
