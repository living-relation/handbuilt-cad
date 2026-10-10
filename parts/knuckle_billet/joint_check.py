"""Bolted tongue-joint check (VDI-2230-style hand calc) from CalculiX strut-bolt reactions.
iter/<stem>.dat must carry NODE PRINT totals for STRUTO and STRUTI (see iter/fa2r.inp). Forces on the tongue = -(reactions).
Joint: foot on the flange top (z 82, normal +Z), bolts at (+/-24,-47), (+/-24,-62), 2 fitted dowels d8 at (+/-10,-64).
Usage: joint_check.py <stem> [d=10|12] [mu=0.2]"""
import sys, re, json, numpy as np
stem = sys.argv[1]; d = int(sys.argv[2]) if len(sys.argv) > 2 else 10; mu = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2
As, FvMin, FvMax = {10: (58.0, 30e3, 48e3), 12: (84.3, 44e3, 70e3)}[d]; Rp = 1100.0; PHI = 0.25
txt = open(f'iter/{stem}.dat').read(); cases = ['bump', 'corner', 'brake', 'combined', 'fatigue']; R = {}
for s, t, a, b, c in re.findall(r'total force \(fx,fy,fz\) for set (\w+) and time\s+(\S+)\s*\n\s*\n\s*(\S+)\s+(\S+)\s+(\S+)', txt):
    R.setdefault(cases[int(round(float(t))) - 1], {})[s] = np.array([float(a), float(b), float(c)])
Pp = {'STRUTO': np.array([-2.5, -147.5, 96.2]), 'STRUTI': np.array([-2.5, -79.0, 93.7])}
B = np.array([[-10, -57.1], [10, -57.1], [-28, -50.8], [28, -50.8]], float); J = np.array([0.0, B[:, 1].mean(), 82.0])
dB = B - B.mean(0); Sy = (dB[:, 1] ** 2).sum(); Sx = (dB[:, 0] ** 2).sum(); rT = np.hypot(dB[:, 0], dB[:, 1]).mean()
out = {}
for k in cases:
    F = np.zeros(3); M = np.zeros(3)
    for s, p in Pp.items(): f = -R[k][s]; F += f; M += np.cross(p - J, f)
    Fext = F[2] / 4 + np.abs(M[0]) * np.abs(dB[:, 1]).max() / Sy + np.abs(M[1]) * np.abs(dB[:, 0]).max() / Sx   # worst bolt, + = pull-off
    Fext = max(Fext, 0.0)
    Fb = FvMax + PHI * Fext; resid = FvMin - (1 - PHI) * Fext
    clamp = 4 * FvMin - (1 - PHI) * max(F[2], 0.0)
    shear = np.hypot(F[0], F[1]) + abs(M[2]) / rT        # in-plane force + torsion converted at the bolt radius (conservative sum)
    out[k] = dict(F_on_tongue_N=np.round(F).tolist(), M_Nmm=np.round(M).tolist(), worst_bolt_ext_N=round(Fext), bolt_max_N=round(Fb),
                  bolt_util=round(Fb / As / Rp, 2), residual_clamp_per_bolt_N=round(resid), no_gap=bool(resid > 0),
                  shear_equiv_N=round(shear), slip_SF=round(mu * clamp / shear, 2), slip_SF_mu0p5_shim=round(0.5 * clamp / shear, 2),
                  dowel_tau_if_all_shear_MPa=round(shear / (2 * np.pi * 16), 0), dowel_bearing_7075_MPa=round(shear / 2 / (8 * 12), 0))
json.dump(dict(bolt=f'M{d} 12.9', mu=mu, phi=PHI, cases=out), open(f'iter/{stem}_joint_M{d}.json', 'w'), indent=1)
for k, v in out.items(): print(k, {q: v[q] for q in ('worst_bolt_ext_N', 'bolt_util', 'residual_clamp_per_bolt_N', 'shear_equiv_N', 'slip_SF', 'slip_SF_mu0p5_shim', 'dowel_tau_if_all_shear_MPa', 'dowel_bearing_7075_MPa')})
