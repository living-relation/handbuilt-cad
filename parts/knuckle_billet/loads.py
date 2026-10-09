"""Load cases for the ST185 rear knuckle (estimates). Writes loads.json, used by fea_v4b.py and LOADS.md."""
import json, math
g = 9.81
V = dict(
    m_car=1560.0,      # kg: 1460 kg curb (turbocelica.nl, export GT-Four) + ~100 kg driver/gear
    rear_frac=0.40,    # rear axle share of mass (estimate; nose-heavy transverse-engine AWD)
    h_cg=0.50,         # m, CG height (estimate for a lowered 1300 mm-tall coupe)
    track_r=1.445,     # m, rear track (turbocelica.nl)
    wheelbase=2.525,   # m (turbocelica.nl)
    R_loaded=0.285,    # m, loaded radius of a ~23.0 in diameter 15 in slick (estimate)
    impact=1.25,       # impact factor on bump: solid joints + stiff slick sidewall, no bushing compliance (estimate)
)
m_r = V['m_car'] * V['rear_frac']
Fz0 = m_r * g / 2                     # static rear corner load, N
def dFz_lat(a):  return m_r * a * g * V['h_cg'] / V['track_r']   # outer-wheel load gain (whole rear axle mass, conservative)
cases = {}
# 1 bump: 4.0 g x 1.25 impact
cases['bump'] = dict(desc='Bump 4.0 g x 1.25 impact (solid joints, slick)', Fz=4.0*V['impact']*Fz0, Fy=0.0, Fx=0.0, brake=False)
# 2 cornering 1.8 g, outer wheel with lateral load transfer; Fy = 1.8 x outer-wheel Fz
Fz_c = Fz0 + dFz_lat(1.8); cases['corner'] = dict(desc='Cornering 1.8 g, outer rear wheel', Fz=Fz_c, Fy=1.8*Fz_c, Fx=0.0, brake=False)
# 3 braking 1.7 g on static rear load (conservative: real rear load drops under braking)
cases['brake'] = dict(desc='Braking 1.7 g x static corner load, torque reacted at caliper', Fz=Fz0, Fy=0.0, Fx=1.7*Fz0, brake=True)
# 4 combined 1.5 g bump + 1.5 g lateral + 1.2 g braking, outer wheel
Fz_l = Fz0 + dFz_lat(1.5)
cases['combined'] = dict(desc='Combined 1.5 g bump + 1.5 g lateral + 1.2 g braking, outer wheel', Fz=1.5*Fz0 + dFz_lat(1.5), Fy=1.5*Fz_l, Fx=1.2*Fz0, brake=True)
# 5 fatigue: 1 g vertical + 0.5 g lateral, outer wheel, ~1e6 cycles
Fz_f = Fz0 + dFz_lat(0.5); cases['fatigue'] = dict(desc='Fatigue 1 g + 0.5 g lateral (1e6 cycles)', Fz=Fz_f, Fy=0.5*Fz_f, Fx=0.0, brake=False)
for c in cases.values():
    c['T_brake_Nm'] = c['Fx'] * V['R_loaded'] if c['brake'] else 0.0
damper = dict(spike_N=6000.0, note='coilover damper force at ~3 m/s shaft speed with stiff valving (estimate); reacted by the strut clamp, already inside the bump reaction')
out = dict(vehicle=V, m_rear_axle=m_r, Fz0_N=Fz0, cases=cases, damper=damper)
json.dump(out, open('loads.json', 'w'), indent=1)
print(f"Fz0 = {Fz0:.0f} N")
for k, c in cases.items(): print(f"{k:9s} Fz {c['Fz']/1e3:6.2f}  Fy {c['Fy']/1e3:6.2f}  Fx {c['Fx']/1e3:5.2f} kN  T {c['T_brake_Nm']:6.0f} Nm")
