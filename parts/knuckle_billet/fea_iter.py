"""Baseline linear-static FEA of knuckle v4b (CalculiX C3D10). Linear elastic: stresses are the same for 6061 and
7075 (same nu, displacement-type supports); deflection scales with 1/E, so one run covers both alloys."""
import numpy as np, json, math, subprocess, os, sys
D = sys.argv[1]; STEM = sys.argv[2]; os.makedirs(D, exist_ok=True)
L = json.load(open('loads.json')); V = L['vehicle']
M = np.load(f'{D}/{STEM}_mesh.npz'); tags, X, conn = M['tags'], M['xyz'], M['conn']
idx = {int(t): i for i, t in enumerate(tags)}
E, NU = 68900.0, 0.33                       # MPa (6061-T6 run; 7075 deflection = x 68.9/71.7)
# ---------------- geometry of the kept features (from knuckle/v4b/knuckle.py)
def near_cyl(c, a, r, half_len, tol=0.35):
    c = np.array(c, float); a = np.array(a, float); a /= np.linalg.norm(a)
    d = X - c; s = d @ a; rad = np.linalg.norm(d - np.outer(s, a), axis=1)
    return np.where((np.abs(rad - r) < tol) & (np.abs(s) <= half_len + 0.01))[0]
def eye(c, ang_deg, plane, bore, length):
    t = math.radians(ang_deg)
    a = (math.cos(t), 0, -math.sin(t)) if plane == 'x' else (-math.sin(t), 0, math.cos(t))
    return near_cyl(c, a, bore/2, length/2)
sets = {
 'SEAT':  near_cyl((0, 0, 29.75), (0, 0, 1), 37.0, 16.25),                 # bearing seat 74.0, z 13.5-46
 'STRUTO': near_cyl((-2.5, -147.5, 96.2), (1, 0, 0), 14.3/2, 27.5),          # strut clamp bolt, outer/upper
 'STRUTI': near_cyl((-2.5, -79.0, 93.7), (1, 0, 0), 14.0/2, 27.5),           # strut clamp bolt, inner/lower
 'EYEL':  eye((-79.15, 86.0, 83.0), 0.0, 'x', 35.0, 26.0),                    # lateral link (assumed No.1)
 'EYER':  eye((65.9, 73.9, 112.6), 13.6, 'x', 35.5, 26.0),                    # lateral link (assumed No.2)
 'EYET':  eye((-6.6, 138.1, 129.0), 8.7, 'z', 40.0, 40.0),                    # TRAILING ARM (owner, chunk 16); fixed in X = fore-aft = along the arm
 'EAR1':  near_cyl((-101.5, 29.0, 52.0), (0, 0, 1), 5.0, 12.0),              # assumed caliper bolt
 'EAR2':  near_cyl((-41.0, -97.0, 54.5), (0, 0, 1), 4.5, 15.5),              # assumed caliper bolt
}
cnt = {k: len(v) for k, v in sets.items()}; print('node sets', cnt, flush=True)
assert all(n > 20 for n in cnt.values()), cnt
# ---------------- write deck
zc = 29.75; zp = float(os.environ.get('ZP', '20.0')); R = V['R_loaded'] * 1000            # contact patch: z = +20 mm (estimate), y = +R (down)
ref, rot = len(tags) + 1, len(tags) + 2
with open(f'{D}/{STEM}.inp', 'w') as f:
    f.write('*NODE, NSET=NALL\n')
    for i, (x, y, z) in enumerate(X): f.write(f'{i+1},{x:.5f},{y:.5f},{z:.5f}\n')
    f.write(f'{ref},0,0,{zc}\n{rot},0,0,{zc}\n')
    f.write('*ELEMENT, TYPE=C3D10, ELSET=EALL\n')
    for e, c in enumerate(conn):
        n = [idx[int(t)] + 1 for t in c]; n = n[:8] + [n[9], n[8]]          # gmsh -> ccx tet10 order
        f.write(f'{e+1},' + ','.join(map(str, n)) + '\n')
    for k, v in sets.items():
        f.write(f'*NSET, NSET={k}\n'); [f.write(f'{i+1},\n') for i in v]
    f.write(f'*MATERIAL, NAME=AL\n*ELASTIC\n{E},{NU}\n*SOLID SECTION, ELSET=EALL, MATERIAL=AL\n')
    f.write(f'*RIGID BODY, NSET=SEAT, REF NODE={ref}, ROT NODE={rot}\n')     # bearing outer race: stiff steel ring
    # supports: strut clamp = rigid (coilover strut + solid top mount); links/strut rod = two-force members (solid joints)
    # chunk 17: suspension position (POS env) rotates each two-force link about its inboard pivot.
    # lateral arms: direction eye->inboard pivot = (0, -sin a, cos a) (rising inboard by a, -Y up); trailing rod: eye->front pivot = (cos b, -sin b, 0) (+X forward)
    POS = os.environ.get('POS', 'legacy')
    ang = dict(legacy=(0.0, 0.0), bump=(0.0, -7.0), mid=(5.0, -3.5), ride=(9.0, 0.0), droop=(17.0, 7.0))[POS]
    a, b = math.radians(ang[0]), math.radians(ang[1])
    dl = (0.0, -math.sin(a), math.cos(a)); dr = (math.cos(b), -math.sin(b), 0.0)
    for nm in ('EYEL', 'EYER'):
        f.write(f'*TRANSFORM, NSET={nm}, TYPE=R\n{dl[0]:.6f},{dl[1]:.6f},{dl[2]:.6f},1.0,0.0,0.0\n')
    f.write(f'*TRANSFORM, NSET=EYET, TYPE=R\n{dr[0]:.6f},{dr[1]:.6f},{dr[2]:.6f},0.0,0.0,1.0\n')
    f.write('*BOUNDARY\nSTRUTO,1,3\nSTRUTI,1,3\nEYEL,1,1\nEYER,1,1\nEYET,1,1\n')
    CASES = os.environ.get('CASES', ','.join(L['cases'])).split(',')
    for name, c in [(k, L['cases'][k]) for k in CASES]:
        F = np.array([-c['Fx'], -c['Fz'], c['Fy']])          # on tyre from ground: braking -X, up = -Y, cornering inboard = +Z
        r = np.array([0.0, R, zp - zc]); Mo = np.cross(r, F)   # N*mm about hub centre
        Mz = Mo[2]; Mo[2] = 0.0                                # brake torque goes rotor -> caliper, not through the bearing
        if not c['brake']: assert abs(Mz) < 1e-6
        f.write(f'*STEP\n*STATIC\n*CLOAD, OP=NEW\n{ref},1,{F[0]:.3f}\n{ref},2,{F[1]:.3f}\n{ref},3,{F[2]:.3f}\n')
        f.write(f'{rot},1,{Mo[0]:.3f}\n{rot},2,{Mo[1]:.3f}\n')
        if c['brake']:                                         # caliper reaction: tangential forces on the two ear holes
            for s, ctr in (('EAR1', (-101.5, 29.0)), ('EAR2', (-41.0, -97.0))):
                p = np.array(ctr); rr = np.linalg.norm(p); t = np.array([-p[1], p[0]]) / rr   # z x p_hat
                Fi = (Mz / 2 / rr) * t / len(sets[s])
                for i in sets[s]: f.write(f'{i+1},1,{Fi[0]:.5f}\n{i+1},2,{Fi[1]:.5f}\n')
        f.write('*NODE FILE\nU\n*EL FILE\nS\n*NODE PRINT, NSET=NALL, TOTALS=ONLY\nRF\n*END STEP\n')
json.dump(dict(sets=cnt, nodes=len(tags), tets=len(conn), zc=zc, zp=zp, R=R), open(f'{D}/{STEM}_deck_info.json', 'w'))
print('deck written', flush=True)
if '--run' in sys.argv:
    env = dict(os.environ, OMP_NUM_THREADS='8', CCX_NPROC_STIFFNESS='8', CCX_NPROC_RESULTS='8')
    subprocess.run(['ccx', '-i', STEM], cwd=D, env=env, stdout=open(f'{D}/ccx.log', 'w'), stderr=subprocess.STDOUT)
    print('ccx done', flush=True)
