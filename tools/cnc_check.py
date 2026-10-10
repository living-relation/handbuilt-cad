"""CNC design check for any STEP file: likely setups, inside corners, vertical corners, thin walls.

    .venv/bin/python tools/cnc_check.py part.step                      # defaults
    .venv/bin/python tools/cnc_check.py part.step --spec cnc_spec.json  # your tools / rules
    .venv/bin/python tools/cnc_check.py part.step --strict              # exit 1 if anything is flagged

Writes <part>_cnc.txt (plain language) and <part>_cnc.json next to the STEP (or use --out PREFIX).

Spec JSON (every key optional; defaults shown):
    {"tool_radii_mm": [3.0, 5.0, 6.0],   # end mills you have (radius). Smallest = tightest inside corner you can cut
     "min_wall_mm": 1.5,                 # thinner walls are flagged (aluminium rule of thumb; use more for parts that carry load)
     "spindle_axis": "z",                # the "Z-down" direction for the vertical-corner check (x, y or z)
     "wall_samples": 20000,              # surface points used for the wall scan
     "max_listed": 25}                   # longest lists are cut to this many entries in the text report

It is a quick geometric screen, not CAM: setups ignore part-on-part shadowing (a lower bound), and walls
come from inward ray casting on a tessellated mesh. Holes (>=180 deg of arc) are assumed drilled/bored and are not corners.
"""
import argparse, json, math, os, sys
from collections import defaultdict
import numpy as np
from build123d import import_step, GeomType, Vector
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepTools import BRepTools
from OCP.TopAbs import TopAbs_IN
from OCP.gp import gp_Pnt

DEFAULTS = dict(tool_radii_mm=[3.0, 5.0, 6.0], min_wall_mm=1.5, spindle_axis="z", wall_samples=20000, max_listed=25)
AXES = {"x": Vector(1, 0, 0), "y": Vector(0, 1, 0), "z": Vector(0, 0, 1)}

def xyz(v, nd=1): return [round(v.X, nd), round(v.Y, nd), round(v.Z, nd)]

def dir_name(d):
    for k, a in AXES.items():
        if abs(d.dot(a)) > 0.999: return ("+" if d.dot(a) > 0 else "-") + k.upper()
    return "tilted (%.2f, %.2f, %.2f)" % (d.X, d.Y, d.Z)

class Part:
    """Solid + point classifier + per-face helpers."""
    def __init__(self, path):
        shp = import_step(path); sols = shp.solids()
        if not sols: sys.exit(f"{path}: no solid found")
        self.n_solids, self.valid = len(sols), shp.is_valid
        self.solid = max(sols, key=lambda s: s.volume)
        self.clf = BRepClass3d_SolidClassifier(self.solid.wrapped)

    def inside(self, p):
        self.clf.Perform(gp_Pnt(p.X, p.Y, p.Z), 1e-5); return self.clf.State() == TopAbs_IN

    @staticmethod
    def round_face(f):
        """(kind, radius, axis_point, axis_dir, arc_deg, concave) for cylinders / tori, else None."""
        s = BRepAdaptor_Surface(f.wrapped)
        u0, u1, _, _ = BRepTools.UVBounds_s(f.wrapped); arc = math.degrees(u1 - u0)
        p = f.position_at(0.5, 0.5); n = f.normal_at(p)
        if f.geom_type == GeomType.CYLINDER:
            c = s.Cylinder(); r = c.Radius(); ax = c.Axis()
            o = Vector(ax.Location().X(), ax.Location().Y(), ax.Location().Z()); d = Vector(ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z())
            w = p - o; ctr = o + d * w.dot(d)               # nearest axis point = centre of the arc
            return ("cylinder", r, ctr, d, arc, n.dot(ctr - p) > 0)
        if f.geom_type == GeomType.TORUS:
            t = s.Torus(); R, r = t.MajorRadius(), t.MinorRadius(); pos = t.Position()
            o = Vector(pos.Location().X(), pos.Location().Y(), pos.Location().Z()); d = Vector(pos.Direction().X(), pos.Direction().Y(), pos.Direction().Z())
            w = p - o; radial = w - d * w.dot(d)
            ctr = o + radial.normalized() * R if radial.length > 1e-9 else o   # centre of the tube cross-section
            return ("torus", r, ctr, d, arc, n.dot(ctr - p) > 0)
        return None

def edge_faces(solid):
    m = defaultdict(list); keep = {}
    for f in solid.faces():
        for e in f.edges():
            h = hash(e); keep[h] = e
            if not any(g.is_same(f) for g in m[h]): m[h].append(f)
    return [(keep[h], fs) for h, fs in m.items() if len(fs) == 2]

def is_vertical(e, n1, n2, ax):
    tang = [e.tangent_at(t) for t in (0.1, 0.5, 0.9)]
    return all(abs(t.dot(ax)) > 0.98 for t in tang) and abs(n1.dot(ax)) < 0.2 and abs(n2.dot(ax)) < 0.2

def find_corners(part, spec):
    """Concave fillets smaller than the smallest tool, and sharp (r0) concave edges."""
    rmin = min(spec["tool_radii_mm"]); ax = AXES[spec["spindle_axis"]]
    small, sharp, holes = [], [], []
    for f in part.solid.faces():
        rf = Part.round_face(f) if f.geom_type in (GeomType.CYLINDER, GeomType.TORUS) else None
        if not rf or not rf[5]: continue
        kind, r, ctr, d, arc, _ = rf
        if kind == "cylinder" and arc >= 179: holes.append(dict(d=round(2 * r, 3), axis=d, at=xyz(ctr), area=f.area)); continue
        if r < rmin - 1e-6:
            vert = kind == "cylinder" and abs(d.dot(ax)) > 0.98
            small.append(dict(r=round(r, 2), kind=kind, at=xyz(f.center()), area_mm2=round(f.area, 1), vertical=vert))
    for e, (f1, f2) in edge_faces(part.solid):
        if e.length < 0.2: continue
        p = e.position_at(0.5)
        try: n1, n2 = f1.normal_at(p), f2.normal_at(p)
        except Exception: continue
        ang = math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2)))))
        if ang < 15: continue                                  # tangent join (fillet run-out)
        eps = min(0.05, 0.1 * e.length)
        if part.inside(p - n1 * eps + n2 * eps) and part.inside(p - n2 * eps + n1 * eps):
            sharp.append(dict(at=xyz(p), length=round(e.length, 1), edge=e.geom_type.name.lower(),
                              face_angle_deg=round(ang), vertical=is_vertical(e, n1, n2, ax),
                              round_edge=e.geom_type == GeomType.CIRCLE))
    sharp.sort(key=lambda c: -c["length"]); small.sort(key=lambda c: c["r"])
    return small, sharp, holes

def find_setups(part, holes):
    """Greedy cover: fewest tool directions so every flat face is reachable and every hole is on-axis.
    A flat face is reachable from t if it faces the tool (n.t > 0) or is a wall the side of the cutter can cut (n.t = 0);
    facing area scores double, so big floors pick the direction that looks straight at them."""
    items = [("plane", f.normal_at(f.center()), f.area) for f in part.solid.faces() if f.geom_type == GeomType.PLANE]
    items += [("hole", h["axis"], h["area"]) for h in holes]
    cands = [s * a for a in AXES.values() for s in (1, -1)]
    for _, d, _ in items:
        for s in (1, -1):
            if not any((s * d - c).length < 1e-3 for c in cands): cands.append(s * d)
    def weight(it, t):                                        # 0 = can't reach, 0.5 = wall, 1 = facing / on-axis
        if it[0] == "hole": return 1.0 if abs(abs(it[1].dot(t)) - 1) < 1e-3 else 0.0
        c = it[1].dot(t); return 1.0 if c > 0.01 else 0.5 if c >= -0.01 else 0.0
    left, out = list(range(len(items))), []
    while left:
        t = max(cands, key=lambda c: (sum(items[i][2] * weight(items[i], c) for i in left), -len(dir_name(c))))
        cov = [i for i in left if weight(items[i], t) > 0]
        if not cov: break
        out.append(dict(direction=dir_name(t), vector=xyz(t, 3), flat_faces=sum(items[i][0] == "plane" for i in cov),
                        holes=sum(items[i][0] == "hole" for i in cov)))
        left = [i for i in left if i not in cov]
    return out

def find_thin_walls(part, spec):
    import trimesh
    v, t = part.solid.tessellate(0.02, 0.2)
    m = trimesh.Trimesh(np.array([[p.X, p.Y, p.Z] for p in v]), np.array(t), process=True)
    pts, fi = trimesh.sample.sample_surface_even(m, spec["wall_samples"], seed=0); nr = m.face_normals[fi]
    o = pts - nr * 0.01
    loc, ir, it = m.ray.intersects_location(o, -nr, multiple_hits=False)
    d = np.full(len(pts), np.inf); d[ir] = np.linalg.norm(loc - o[ir], axis=1)
    cos = np.zeros(len(pts)); cos[ir] = -np.einsum("ij,ij->i", m.face_normals[it], nr[ir])
    wall = (cos > 0.8) & np.isfinite(d)                         # opposite face roughly parallel = a real wall
    thin = wall & (d < spec["min_wall_mm"])
    spots = {}
    for p, t_ in zip(pts[thin], d[thin]):                       # group thin samples into 5 mm cells
        k = tuple(np.round(p / 5.0).astype(int))
        if k not in spots or t_ < spots[k][0]: spots[k] = (t_, p)
    spots = sorted(spots.values(), key=lambda s: s[0])
    return dict(samples=int(len(pts)), wall_samples=int(wall.sum()),
                min_wall_mm=round(float(d[wall].min()), 2) if wall.any() else None,
                thin_samples=int(thin.sum()),
                thin_spots=[dict(t_mm=round(float(t_), 2), at=np.round(p, 1).tolist()) for t_, p in spots])

def report_text(name, part, spec, setups, small, sharp, walls):
    L = spec["max_listed"]; rmin = min(spec["tool_radii_mm"]); ax = spec["spindle_axis"].upper()
    vert = [c for c in sharp if c["vertical"]] + [c for c in small if c["vertical"]]
    bb = part.solid.bounding_box().size
    out = [f"CNC check: {name}",
           f"size {bb.X:.1f} x {bb.Y:.1f} x {bb.Z:.1f} mm, volume {part.solid.volume/1000:.2f} cm3, "
           f"{part.n_solids} solid(s), valid: {part.valid}",
           f"rules: tools r {spec['tool_radii_mm']} mm (smallest r{rmin}), min wall {spec['min_wall_mm']} mm, spindle {ax}", "",
           f"1. Setups: about {len(setups)} tool direction(s) needed (lower bound, ignores shadowing)"]
    out += [f"   - from {s['direction']}: {s['flat_faces']} flat faces, {s['holes']} holes" for s in setups]
    out += ["", f"2. Inside corners smaller than the smallest tool (r{rmin}): {len(small)} rounded, {len(sharp)} sharp (r0)"]
    out += [f"   - r{c['r']} {c['kind']} at {c['at']}" for c in small[:L]]
    rnd = sum(c["round_edge"] for c in sharp)
    if sharp: out.append(f"   sharp edges ({rnd} are round edges such as bore shoulders or grooves, usually fine when turned or bored):")
    out += [f"   - {c['length']} mm {c['edge']} edge at {c['at']}, faces meet at {c['face_angle_deg']} deg" for c in sharp[:L]]
    if len(sharp) > L: out.append(f"   ... {len(sharp) - L} more in the JSON")
    out += ["", f"3. Vertical inside corners a {ax}-down cutter can't make: {len(vert)}"]
    out += [f"   - {'sharp' if 'length' in c else 'r' + str(c['r'])} at {c['at']}" + (f", {c['length']} mm tall" if 'length' in c else "")
            for c in vert[:L]]
    if vert: out.append(f"   Fix: add a corner radius of at least r{rmin} in CAD (a bit more than the tool is kinder), or accept the tool radius there.")
    out += ["", f"4. Walls thinner than {spec['min_wall_mm']} mm: {len(walls['thin_spots'])} spot(s) "
            f"(thinnest wall found {walls['min_wall_mm']} mm, {walls['wall_samples']} wall samples)"]
    out += [f"   - {s['t_mm']} mm at {s['at']}" for s in walls["thin_spots"][:L]]
    flagged = bool(small or [c for c in sharp if not c["round_edge"]] or vert or walls["thin_spots"])
    out += ["", "Result: " + ("things to look at (see above)" if flagged else "nothing flagged")]
    return "\n".join(out), flagged

def main():
    ap = argparse.ArgumentParser(description="CNC design check of a STEP file (setups, inside corners, vertical corners, thin walls).",
                                 epilog="Spec keys and defaults: " + json.dumps(DEFAULTS))
    ap.add_argument("step", help="part .step/.stp")
    ap.add_argument("--spec", help="JSON with tool_radii_mm, min_wall_mm, spindle_axis, wall_samples, max_listed")
    ap.add_argument("--out", help="output prefix (default: STEP path without extension + '_cnc')")
    ap.add_argument("--strict", action="store_true", help="exit 1 if anything is flagged")
    a = ap.parse_args()
    spec = dict(DEFAULTS, **(json.load(open(a.spec)) if a.spec else {}))
    if spec["spindle_axis"] not in AXES: sys.exit("spindle_axis must be x, y or z")
    part = Part(a.step)
    small, sharp, holes = find_corners(part, spec)
    setups = find_setups(part, holes)
    walls = find_thin_walls(part, spec)
    txt, flagged = report_text(os.path.basename(a.step), part, spec, setups, small, sharp, walls)
    pre = a.out or os.path.splitext(a.step)[0] + "_cnc"
    open(pre + ".txt", "w").write(txt + "\n")
    js = dict(part=a.step, spec=spec, n_solids=part.n_solids, valid=part.valid, setups=setups,
              holes=[dict(h, axis=xyz(h["axis"], 3), area=round(h["area"], 1)) for h in holes], small_fillets=small, sharp_concave_edges=sharp,
              vertical_corners=[c for c in sharp + small if c["vertical"]], walls=walls, flagged=flagged)
    json.dump(js, open(pre + ".json", "w"), indent=1)
    print(txt); print(f"wrote {pre}.txt, {pre}.json")
    sys.exit(1 if a.strict and flagged else 0)

if __name__ == "__main__": main()
