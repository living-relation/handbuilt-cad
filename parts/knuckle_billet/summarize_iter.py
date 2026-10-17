"""Append one row per iteration to iterations.csv (7075-T651; robust = 99.99th pct von Mises outside 3 mm of supports)."""
import json, sys, csv, os, numpy as np, meshio
stem, note = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ''
R = json.load(open(f'iter/{stem}_results.json')); B = json.load(open(f'iter/{stem}_build.json'))
I = json.load(open(f'iter/{stem}_interface.json'))
Sy, Su, Se = 503.0, 572.0, 159 * 0.85
row = dict(iter=stem, mass_7075_kg=round(B['report']['mass_7075_kg'], 3), mass_6061_kg=round(B['report']['mass_6061_kg'], 3), one_valid_solid=B['report']['n_solids'] == 1 and B['report']['valid'], interface_ok=I['all_ok'])
worst = 1e9; per = {}
for c, r in R['cases'].items():
    m = meshio.read(f'iter/{stem}_{c}.vtu'); vm = m.point_data['vonMises_MPa']; s = m.point_data['singular_zone'] > 0
    rob = float(np.percentile(vm[~s], 99.99)); per[c] = dict(peak=r['vm_max'], robust=rob, at=r['at'], umax_7075=r['umax_7075'])
    row[f'{c}_robust_MPa'] = round(rob, 1); row[f'{c}_peak_MPa'] = round(r['vm_max'], 1); row[f'{c}_SF_yield_robust'] = round(Sy / rob, 2)
    row[f'{c}_umax_mm'] = round(r['umax_7075'], 3)
    if c != 'fatigue': worst = min(worst, Sy / rob)
f = per['fatigue']['robust']; row['fatigue_SF_goodman_R0'] = round(1 / ((f/2)/Se + (f/2)/Su), 2); row['fatigue_SF_reversed'] = round(Se / f, 2)
row['worst_SF_yield_robust'] = round(worst, 2); row['note'] = note
new = not os.path.exists('iterations.csv')
with open('iterations.csv', 'a', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(row)); new and w.writeheader(); w.writerow(row)
json.dump(per, open(f'iter/{stem}_summary.json', 'w'), indent=1)
print(json.dumps(row, indent=0)); print(json.dumps({c: dict(robust=round(v['robust']), peak=round(v['peak']), at=v['at']) for c, v in per.items()}))
