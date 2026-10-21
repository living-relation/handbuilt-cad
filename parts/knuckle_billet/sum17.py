"""chunk 17: robust stress (99.99th pct outside singular zones) per case for one run; usage sum17.py <dir> <stem>"""
import json, sys, numpy as np, meshio
D, stem = sys.argv[1], sys.argv[2]; R = json.load(open(f'{D}/{stem}_results.json'))
Sy, Su, Se = 503.0, 572.0, 159 * 0.85; out = {}
for c, r in R['cases'].items():
    m = meshio.read(f'{D}/{stem}_{c}.vtu'); vm = m.point_data['vonMises_MPa']; s = m.point_data['singular_zone'] > 0
    rob = float(np.percentile(vm[~s], 99.99)); i = np.argmax(np.where(s, 0, vm)); at = [round(float(v), 1) for v in m.points[i]]
    out[c] = dict(robust=round(rob, 1), SF=round(Sy / rob, 2), peak=round(r['vm_max'], 1), at_robust_max=at)
    if c == 'fatigue': out[c].update(SF_goodman_R0=round(1 / ((rob/2)/Se + (rob/2)/Su), 2), SF_reversed=round(Se / rob, 2))
json.dump(out, open(f'{D}/{stem}_sum17.json', 'w'), indent=1); print(stem, json.dumps(out))
