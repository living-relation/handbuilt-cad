"""Chunk 17: robust stress (99.99th pct outside singular zones) per load case for one FEA run.
usage: python sum17.py <dir> <stem> [--sy 503] [--su 572] [--se 135.15]
reads <dir>/<stem>_results.json and <dir>/<stem>_<case>.vtu, writes <dir>/<stem>_sum17.json."""
import argparse, json, numpy as np, meshio

# Material defaults: 7075-T651 plate, MPa. Sy / Su are typical minimums from the Aluminum Association / MMPDS
# property tables. SE_7075 is the rotating-beam fatigue strength at 5e8 cycles (159 MPa, ASM handbook value)
# times 0.85 as a surface-finish factor for a machined part. Change them with --sy / --su / --se for other materials.
SY_7075, SU_7075, SE_7075 = 503.0, 572.0, 159 * 0.85
ap = argparse.ArgumentParser(); ap.add_argument('dir'); ap.add_argument('stem')
ap.add_argument('--sy', type=float, default=SY_7075); ap.add_argument('--su', type=float, default=SU_7075); ap.add_argument('--se', type=float, default=SE_7075)
a = ap.parse_args(); D, stem = a.dir, a.stem; R = json.load(open(f'{D}/{stem}_results.json'))
Sy, Su, Se = a.sy, a.su, a.se; out = {}
for c, r in R['cases'].items():
    m = meshio.read(f'{D}/{stem}_{c}.vtu'); vm = m.point_data['vonMises_MPa']; s = m.point_data['singular_zone'] > 0
    rob = float(np.percentile(vm[~s], 99.99)); i = np.argmax(np.where(s, 0, vm)); at = [round(float(v), 1) for v in m.points[i]]
    out[c] = dict(robust=round(rob, 1), SF=round(Sy / rob, 2), peak=round(r['vm_max'], 1), at_robust_max=at)
    if c == 'fatigue': out[c].update(SF_goodman_R0=round(1 / ((rob/2)/Se + (rob/2)/Su), 2), SF_reversed=round(Se / rob, 2))
json.dump(out, open(f'{D}/{stem}_sum17.json', 'w'), indent=1); print(stem, json.dumps(out))
