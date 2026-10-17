import os
"""Rev2 hole corrections (ISO coarse tap drills, thread >=1.5D, drill = thread + ~3P, ISO 273 medium clearance).
Plug each old hole with a slightly oversize cylinder (flush to the opening plane), re-cut any other hole the plug
touched, then cut the new hole (118 deg drill point for blind holes)."""
import sys, math, json, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','drawing'))
from build123d import *
import feat

def cyl(base, d, t0, t1, r):
    d = Vector(*d); p0 = Vector(*(base + d_np(d) * t0))
    L = t1 - t0
    return Solid.make_cylinder(r, L, Plane(origin=p0, z_dir=d))

def d_np(v): return np.array([v.X, v.Y, v.Z])

def cone_tip(base, d, t, r, sgn):
    # drill point from radius r at t, tip at t + sgn*h
    h = r / math.tan(math.radians(59))
    d = Vector(*d)
    if sgn > 0:
        return Solid.make_cone(r, 0, h, Plane(origin=Vector(*(base + d_np(d) * t)), z_dir=d))
    return Solid.make_cone(r, 0, h, Plane(origin=Vector(*(base + d_np(d) * t)), z_dir=-d))

def fix(path, out, rules):
    sol = import_step(path).solids()[0]
    v0 = sol.volume
    holes, _, _ = feat.analyze(sol)
    log = []
    new = sol
    PL = []; CU = []
    for h in holes:
        key = round(h['dia'], 2)
        rule = next((r for r in rules if abs(r['old'] - h['dia']) < 0.02 and r.get('through', h['through']) == h['through']
                     and r.get('axis', h['axis']) == h['axis'] and len(h['segs']) == 1
                     and ('oldlen' not in r or abs(max(b-a for a,b in h['segs'].values())-r['oldlen'])<0.1)), None)
        if not rule: continue
        d = np.asarray(h['d'], float); base = np.asarray(h['base'], float)
        lo, hi = h['lo'], h['hi']
        rmax = h['dia'] / 2 + max([(b - a) * math.tan(c) for a, b, c in h['cones']] + [0])
        plug = cyl(base, d, lo, hi, rmax + 0.05)
        for o in holes:
            if o is h: continue
            for rr, (a, b) in o['segs'].items():
                c = cyl(np.asarray(o['base']), np.asarray(o['d']), a, b, rr)
                ii = c.intersect(plug)
                iv = 0 if ii is None else (sum(x.volume for x in ii) if isinstance(ii, list) else ii.volume)
                if iv > 1e-6: plug = plug.cut(c)
        PL.append(plug)
        rn = rule['new'] / 2
        if h['through']:
            cut = cyl(base, d, lo - 1, hi + 1, rn); depth = 'THRU'
        else:
            # opening end
            if h['open_lo']: t_open, sgn = lo, +1
            else: t_open, sgn = hi, -1
            D = rule['depth']
            t_end = t_open + sgn * D
            a, b = sorted([t_open - sgn * 1.0, t_end])
            cut = cyl(base, d, a, b, rn).fuse(cone_tip(base, d, t_end, rn, sgn))
            depth = D
        CU.append(cut)
        pos = np.round(base + d * ((lo + hi) / 2), 2)
        old_desc = f"Ø{h['dia']:.3f} " + ("THRU" if h['through'] else f"x {max(b-a for a,b in h['segs'].values()):.2f} deep (full Ø)")
        log.append(dict(axis=h['axis'], pos=[float(x) for x in pos], old=old_desc, new=f"Ø{rule['new']} " + (depth if depth == 'THRU' else f"x {depth} deep (full Ø) + 118° point"),
                        purpose=rule['purpose'], thread=rule.get('thread', '')))
    if PL: new = sol.fuse(*PL).clean()
    if CU: new = new.cut(*CU).clean()
    sols = new.solids()
    print("  solids", len(sols), [(round(s.volume,1), tuple(round(c,1) for c in s.bounding_box().min), tuple(round(c,1) for c in s.bounding_box().max)) for s in sols[:4]])
    sols = sorted(sols, key=lambda s: -s.volume)
    assert len(sols) == 1 and sols[0].volume > 0, path
    new = sols[0]
    export_step(new, out)
    return new, v0, log

if __name__ == '__main__':
    cfg = json.load(open(sys.argv[1]))
    res = {}
    for job in cfg:
        for p in job['parts']:
            new, v0, log = fix(p['src'], p['out'], p['rules'])
            res[p['out']] = dict(valid=new.is_valid, vol_old=v0, vol_new=new.volume, changes=log)
            print(p['out'], 'valid', new.is_valid, 'dV mm3 %.2f' % (new.volume - v0), 'changes', len(log))
    json.dump(res, open(sys.argv[2], 'w'), indent=1)
