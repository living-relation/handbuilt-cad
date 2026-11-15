"""CNC design check for any STEP file: likely setups, inside corners, vertical corners, thin walls.

    .venv/bin/python tools/cnc_check.py part.step                      # CNC metal wall floor (0.762 mm); 1.3× corner rule
    .venv/bin/python tools/cnc_check.py part.step --material plastic    # CNC plastic wall floor (1.52 mm)
    .venv/bin/python tools/cnc_check.py part.step --process printed --min-wall 2.0
    .venv/bin/python tools/cnc_check.py part.step --min-wall 2.0        # stricter CNC floor (never looser than the guide)
    .venv/bin/python tools/cnc_check.py part.step --spec cnc_spec.json  # your tools / rules
    .venv/bin/python tools/cnc_check.py part.step --strict              # exit 1 if anything is flagged or failed
    .venv/bin/python tools/cnc_check.py part.step --stl part.stl
    .venv/bin/python tools/cnc_check.py part.step --reach
    .venv/bin/python tools/cnc_check.py part.step --reach "+Z,-Z,+X,0.97/0/-0.24"

Writes <part>_cnc.txt (plain language) and <part>_cnc.json next to the STEP (or use --out PREFIX).

Spec JSON (every key optional; defaults shown):
    {"tool_radii_mm": [3.0, 5.0, 6.0],   # end mills you have (radius). Also used with the standard-size catalog
     "lip_max_mm": 0.1,                  # a concave edge next to a face narrower than this, with the faces either side of that
                                         # sliver within 15 deg of tangent, is a lip (tiny step, e.g. a blend run-out), not a corner. 0 = off
     "process": "machined",              # "machined" (CNC wall floor applies and thin walls FAIL) or "printed"
     "material": "metal",                # "metal" or "plastic" (CNC floors 0.762 mm / 1.52 mm). Ignored for printed
     "min_wall_mm": null,                # CNC: default is the guide floor (or a stricter value you set). Printed: no default
     "spindle_axis": "z",
     "wall_samples": 20000,
     "reach_samples": 20000,
     "reach_min_gain_pct": 0.25,
     "ray_chunk": 1000,
     "mesh_tol_mm": 0.02,
     "max_listed": 25}

CNC machined parts (default): walls under 0.030" (0.762 mm) metal or 0.060" (1.52 mm) plastic FAIL
(docs/CNC-MACHINING-RULES.md). A stricter --min-wall / spec / walls-config is kept; a looser one is raised to the floor.
3D printed parts (--process printed): no assumed minimum; pass --min-wall, spec min_wall_mm or --walls-config or
walls are "not checked". Thin printed spots are candidates to classify, never auto-failed here.

Inside corners: flags radii smaller than the smallest configured tool, radii under 1.3× the nearest standard (or
configured) tool radius, and radii that exactly match a standard tool size (docs/CNC-MACHINING-RULES.md CNC-CORNER-R).

It is a quick geometric screen, not CAM: setups ignore part-on-part shadowing (a lower bound), and walls
come from inward ray casting on a tessellated mesh. Holes (>=180 deg of arc) are assumed drilled/bored and are not corners.
--reach casts rays from surface points toward each tool direction: a point counts as reachable if nothing of the part
is in the way along that straight line (line of sight, not tool length / holder / cutter radius), then picks the
fewest directions that cover what is reachable at all. Meshing: if OCC can't tessellate the whole solid, faces are
meshed one by one (coarser retries), faces that still fail are skipped and counted; never a crash.
"""
import argparse, json, math, os, resource, sys, time
from collections import defaultdict
import numpy as np
from build123d import import_step, GeomType, Vector
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepTools import BRepTools
from OCP.TopAbs import TopAbs_IN
from OCP.gp import gp_Pnt

DEFAULTS = dict(tool_radii_mm=[3.0, 5.0, 6.0], lip_max_mm=0.1, min_wall_mm=None, process="machined", material="metal",
                spindle_axis="z", wall_samples=20000, reach_samples=20000, reach_min_gain_pct=0.25, ray_chunk=1000,
                mesh_tol_mm=0.02, max_listed=25)
AXES = {"x": Vector(1, 0, 0), "y": Vector(0, 1, 0), "z": Vector(0, 0, 1)}

# docs/CNC-MACHINING-RULES.md (Xometry 16 Apr 2025, p21/p36); metal 0.030", plastic 0.060" (guide's mm).
CNC_WALL_METAL_MM = 0.762
CNC_WALL_PLASTIC_MM = 1.52
CORNER_FACTOR = 1.3
CORNER_EXACT_TOL_MM = 0.02
# Standard end-mill diameters (metric + common fractional inch), stored as radii (mm).
_STD_DIAMETERS_MM = (
    1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 25,
    25.4 / 32, 25.4 / 16, 3 * 25.4 / 32, 25.4 / 8, 5 * 25.4 / 32, 3 * 25.4 / 16,
    25.4 / 4, 5 * 25.4 / 16, 3 * 25.4 / 8, 7 * 25.4 / 16, 25.4 / 2, 5 * 25.4 / 8, 3 * 25.4 / 4, 25.4,
)
STANDARD_TOOL_RADII_MM = tuple(sorted({round(d / 2.0, 6) for d in _STD_DIAMETERS_MM}))

def cnc_wall_floor_mm(material="metal"):
    mat = (material or "metal").lower()
    if mat in ("plastic", "composite", "plastics"):
        return CNC_WALL_PLASTIC_MM, "plastic"
    if mat != "metal":
        raise ValueError(f"material must be metal or plastic (got {material!r})")
    return CNC_WALL_METAL_MM, "metal"

def standard_tool_radii_mm(spec):
    extra = [float(x) for x in (spec.get("tool_radii_mm") or [])]
    return tuple(sorted(set(STANDARD_TOOL_RADII_MM) | set(extra)))

def corner_rule(r, configured, catalog=None, factor=CORNER_FACTOR, exact_tol=CORNER_EXACT_TOL_MM):
    """1.3× is measured against the configured tool list (the cutters on the job).
    Exact standard size is measured against that list plus the standard end-mill catalog."""
    configured = tuple(float(x) for x in configured)
    catalog = tuple(STANDARD_TOOL_RADII_MM if catalog is None else catalog)
    sizes = tuple(sorted(set(configured) | set(catalog)))
    exact = any(abs(r - t) <= exact_tol for t in sizes)
    fitting = [t for t in configured if t < r - exact_tol and r >= factor * t - 1e-6]
    under = not bool(fitting)
    smaller = [t for t in configured if t < r - exact_tol]
    if smaller:
        nearest = max(smaller)
    elif configured:
        nearest = min(configured, key=lambda t: abs(t - r))
    else:
        nearest = 0.0
    return dict(exact_standard=exact, under_1_3=under,
                nearest_tool_r=round(nearest, 4) if configured else None,
                required_r=round(factor * nearest, 4) if configured else None)

def resolve_min_wall(spec, cli=None, walls_config=None, process=None, material=None):
    """(min wall mm or None, source, extra).

    CNC (process machined): default is the guide floor; a stricter explicit value is kept; a looser one is raised.
    Printed: no default. Order for an explicit value: --min-wall, spec min_wall_mm, walls-config min_wall.
    """
    process = (process if process is not None else spec.get("process") or "machined").lower()
    if process not in ("machined", "printed"):
        raise ValueError(f"process must be machined or printed (got {process!r})")
    material = material if material is not None else spec.get("material") or "metal"
    extra = dict(process=process)
    if cli is not None:
        v, src = cli, "--min-wall"
    elif spec.get("min_wall_mm") is not None:
        v, src = spec["min_wall_mm"], "spec min_wall_mm"
    elif walls_config:
        import tomllib
        with open(walls_config, "rb") as f:
            cfg = tomllib.load(f)
        if cfg.get("min_wall") is None:
            raise ValueError(f"{walls_config}: no min_wall (it is required there; ask the user once, never assume one)")
        v, src = cfg["min_wall"], f"walls config {os.path.basename(walls_config)}"
    else:
        v, src = None, None
    if v is not None:
        v = float(v)
        if not v > 0:
            raise ValueError(f"minimum wall must be > 0 mm (got {v} from {src})")
    if process == "printed":
        extra.update(material=None, floor_mm=None, fail_thin=False)
        return v, src, extra
    floor, mat = cnc_wall_floor_mm(material)
    extra.update(material=mat, floor_mm=floor, fail_thin=True)
    if v is None:
        return floor, f"docs/CNC-MACHINING-RULES.md {mat} {floor} mm", extra
    if v < floor - 1e-9:
        return floor, f"{src} raised to CNC {mat} floor {floor} mm", extra
    return v, src, extra

NOT_CHECKED = ("not checked: no minimum wall given (never assumed for 3D printed parts). Pass --min-wall MM, "
               "spec min_wall_mm or --walls-config with the value the user set for structural / critical features")

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

def _narrow(face, p, n, t, w, tol=0.01):
    """True when face is narrower than w at edge point p (n: face normal at p, t: edge tangent): neither point w away
    from p across the edge, in the face's tangent plane, lies on the face."""
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    d = n.cross(t)
    if d.length < 1e-9: return False
    d = d.normalized()
    for sg in (1, -1):
        q = p + d * (sg * w)
        dd = BRepExtrema_DistShapeShape(BRepBuilderAPI_MakeVertex(gp_Pnt(q.X, q.Y, q.Z)).Vertex(), face.wrapped)
        if dd.IsDone() and dd.Value() < tol + w * w: return False   # w*w: allows for the face curving away (radius >= w/2)
    return True

def _sliver_turn(e, fs, fo, w, adj):
    """fs is a face narrower than w all along concave edge e (checked at 1/4, 1/2, 3/4), fo the other face of e.
    Returns the angle (deg) between fo and the face on the far side of the sliver, or None if fs is not a sliver."""
    for u in (0.25, 0.5, 0.75):
        p = e.position_at(u)
        if not _narrow(fs, p, fs.normal_at(p), e.tangent_at(u), w): return None
    p = e.position_at(0.5); best = None
    for e2 in fs.edges():                                        # the sliver's other long edge = its edge nearest to p
        if e2.is_same(e): continue
        try: dist = e2.distance_to(p)
        except Exception: continue
        if best is None or dist < best[0]: best = (dist, e2)
    if best is None or best[0] > 2 * w: return None
    far = [g for g in adj.get(hash(best[1]), []) if not g.is_same(fs)]
    if not far: return None
    try:
        q = min((best[1].position_at(i / 10) for i in range(11)), key=lambda x: (x - p).length)   # far-edge point near p
        n1, n2 = fo.normal_at(p), far[0].normal_at(q)
    except Exception: return None
    return math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2)))))

def find_corners(part, spec):
    """Concave fillets smaller than the smallest tool, under 1.3× the nearest standard tool, exact standard sizes,
    sharp (r0) concave edges, and lips. A lip is a concave edge next to a sliver face (narrower than spec lip_max_mm
    all along the edge) where the faces on both sides of the sliver are within 15 deg of tangent: a tiny step such as
    the 0.015 mm run-out a section-loft blend leaves, which no tool has to cut. If the faces either side of the sliver
    turn more than that, it is a real corner split by a sliver face (a failed tiny fillet, a boolean seam): it stays a
    sharp corner, marked sliver_face."""
    rmin = min(spec["tool_radii_mm"]); ax = AXES[spec["spindle_axis"]]; lipw = spec.get("lip_max_mm", 0) or 0
    std_r = standard_tool_radii_mm(spec)
    small, sharp, holes, lips, guide_corners = [], [], [], [], []
    ef = edge_faces(part.solid); adj = {hash(e): fs for e, fs in ef}
    for f in part.solid.faces():
        try: rf = Part.round_face(f) if f.geom_type in (GeomType.CYLINDER, GeomType.TORUS) else None
        except Exception: rf = None                            # odd / degenerate face: skip, don't crash
        if not rf or not rf[5]: continue
        kind, r, ctr, d, arc, _ = rf
        if kind == "cylinder" and arc >= 179: holes.append(dict(d=round(2 * r, 3), axis=d, at=xyz(ctr), area=f.area)); continue
        vert = kind == "cylinder" and abs(d.dot(ax)) > 0.98
        rule = corner_rule(r, spec["tool_radii_mm"], std_r)
        rec = dict(r=round(r, 2), kind=kind, at=xyz(f.center()), area_mm2=round(f.area, 1), vertical=vert, **rule)
        if r < rmin - 1e-6:
            small.append(rec)
        if rule["under_1_3"] or rule["exact_standard"]:
            guide_corners.append(rec)
    for e, (f1, f2) in ef:
        if e.length < 0.2: continue
        p = e.position_at(0.5)
        try: n1, n2 = f1.normal_at(p), f2.normal_at(p)
        except Exception: continue
        ang = math.degrees(math.acos(max(-1.0, min(1.0, n1.dot(n2)))))
        if ang < 15: continue                                  # tangent join (fillet run-out)
        eps = min(0.05, 0.1 * e.length)
        if part.inside(p - n1 * eps + n2 * eps) and part.inside(p - n2 * eps + n1 * eps):
            c = dict(at=xyz(p), length=round(e.length, 1), edge=e.geom_type.name.lower(),
                     face_angle_deg=round(ang), vertical=is_vertical(e, n1, n2, ax), round_edge=e.geom_type == GeomType.CIRCLE)
            if lipw > 0:
                turn = None
                for fs, fo in ((f1, f2), (f2, f1)):
                    try: turn = _sliver_turn(e, fs, fo, lipw, adj)
                    except Exception: turn = None
                    if turn is not None: break
                if turn is not None and turn < 15:
                    lips.append(dict(at=c["at"], length=c["length"], face_angle_deg=c["face_angle_deg"], net_turn_deg=round(turn, 1))); continue
                if turn is not None: c.update(sliver_face=True, net_turn_deg=round(turn))
            sharp.append(c)
    sharp.sort(key=lambda c: -c["length"]); small.sort(key=lambda c: c["r"]); lips.sort(key=lambda c: -c["length"])
    guide_corners.sort(key=lambda c: c["r"])
    return small, sharp, holes, lips, guide_corners

def find_setups(part, holes):
    """Greedy cover: fewest tool directions so every flat face is reachable and every hole is on-axis.
    A flat face is reachable from t if it faces the tool (n.t > 0) or is a wall the side of the cutter can cut (n.t = 0);
    facing area scores double, so big floors pick the direction that looks straight at them."""
    items = []
    for f in part.solid.faces():
        if f.geom_type != GeomType.PLANE: continue
        try: items.append(("plane", f.normal_at(f.center()), f.area))
        except Exception: pass
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
        out.append(dict(direction=dir_name(t), vector=xyz(t, 3), vec=t, flat_faces=sum(items[i][0] == "plane" for i in cov),
                        holes=sum(items[i][0] == "hole" for i in cov)))
        left = [i for i in left if i not in cov]
    return out

# ------------------------------------------------------------------ mesh
def _face_triangulation(face, tol, ang):
    """Triangulation of one face, meshing it on its own (coarser each retry) if the solid pass left it empty."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopLoc import TopLoc_Location
    for k in (1, 5, 25):
        if k > 1:
            try: BRepMesh_IncrementalMesh(face.wrapped, tol * k, False, min(ang * k, 1.0), True)
            except Exception: continue
        loc = TopLoc_Location(); tri = BRep_Tool.Triangulation_s(face.wrapped, loc)
        if tri is not None and tri.NbTriangles() > 0: return tri, loc, k
    return None, None, None

def mesh_faces(solid, tol, ang):
    """Face-by-face mesh: (vertices, triangles, faces_skipped, faces_coarse)."""
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_REVERSED
    try: BRepMesh_IncrementalMesh(solid.wrapped, tol, False, ang, True)
    except Exception: pass                                     # per-face retries below
    V, T, n0, skipped, coarse = [], [], 0, 0, 0
    for f in solid.faces():
        try:
            tri, loc, k = _face_triangulation(f, tol, ang)
            if tri is None: skipped += 1; continue
            tr = loc.Transformation(); rev = f.wrapped.Orientation() == TopAbs_REVERSED
            nodes = [tri.Node(i).Transformed(tr) for i in range(1, tri.NbNodes() + 1)]
            tris = [tri.Triangle(i).Get() for i in range(1, tri.NbTriangles() + 1)]
        except Exception:
            skipped += 1; continue
        coarse += k > 1
        V += [(p.X(), p.Y(), p.Z()) for p in nodes]
        T += [(n0 + a - 1, n0 + c - 1, n0 + b - 1) if rev else (n0 + a - 1, n0 + b - 1, n0 + c - 1) for a, b, c in tris]
        n0 += len(nodes)
    return np.array(V, float).reshape(-1, 3), np.array(T, int).reshape(-1, 3), skipped, coarse

def mesh_tol(part, spec):
    return float(spec.get("mesh_tol_mm") or 0.02)

def load_mesh(part, stl=None, tol=0.02, ang=0.2):
    """(trimesh.Trimesh or None, info). From --stl if given, else the STEP: whole-solid tessellation, then face by face."""
    import trimesh
    nf = len(part.solid.faces()); info = dict(source="step", faces=nf, faces_skipped=0, faces_coarse=0, tol_mm=round(tol, 3), notes=[])
    m = None
    if stl:
        try:
            m = trimesh.load(stl, force="mesh"); info.update(source=os.path.basename(stl)); info["notes"] += bbox_mismatch(part, m)
        except Exception as ex:
            info["notes"].append(f"could not read {os.path.basename(stl)} ({str(ex)[:80]}); meshing the STEP instead"); m = None
    if m is None:
        try:
            v, t = part.solid.tessellate(tol, ang)
            m = trimesh.Trimesh(np.array([[p.X, p.Y, p.Z] for p in v]), np.array(t), process=True); info["method"] = "whole solid"
        except Exception as ex:
            v, t, sk, co = mesh_faces(part.solid, tol, ang)
            info.update(method="face by face", whole_solid_error=str(ex)[:120], faces_skipped=sk, faces_coarse=co)
            m = trimesh.Trimesh(v, t, process=True) if len(t) else None
            if co: info["notes"].append(f"{co} face(s) needed a coarser mesh")
            if sk: info["notes"].append(f"{sk} of {nf} face(s) could not be meshed and are left out (use --stl for a full mesh)")
    if m is None or len(m.faces) == 0:
        info["notes"].append("no usable mesh: wall scan and reach skipped"); return None, info
    open_edges = len(trimesh.grouping.group_rows(m.edges_sorted, require_count=1))
    info.update(triangles=int(len(m.faces)), watertight=bool(m.is_watertight), open_edges=open_edges,
                ray_engine=type(m.ray).__module__.split(".")[-1])
    if open_edges > 10: info["notes"].append(f"mesh has {open_edges} open edges: rays can leak through gaps, treat results near them with care")
    return m, info

def bbox_mismatch(part, m):
    bb = part.solid.bounding_box(); a = np.array([[bb.min.X, bb.min.Y, bb.min.Z], [bb.max.X, bb.max.Y, bb.max.Z]])
    err = float(np.abs(a - m.bounds).max()); size = float(np.ptp(a, axis=0).max())
    if err > max(0.5, 0.01 * size):
        return [f"WARNING: STL bounding box differs from the STEP by up to {err:.1f} mm (units or position?); results are for the STL"]
    return []

def cast(m, o, d, chunk, first=True):
    """Ray casts in batches to cap memory. first=True: (hit_dist, hit_face) arrays; else bool 'hit anything'."""
    n = len(o); D = np.broadcast_to(d, o.shape) if np.ndim(d) == 1 else d
    if not first:
        out = np.zeros(n, bool)
        for s in range(0, n, chunk): out[s:s + chunk] = m.ray.intersects_any(o[s:s + chunk], np.ascontiguousarray(D[s:s + chunk]))
        return out
    dist, face = np.full(n, np.inf), np.full(n, -1)
    for s in range(0, n, chunk):
        loc, ir, it = m.ray.intersects_location(o[s:s + chunk], np.ascontiguousarray(D[s:s + chunk]), multiple_hits=False)
        dist[s + ir] = np.linalg.norm(loc - o[s + ir], axis=1); face[s + ir] = it
    return dist, face

def sample(m, n, seed):
    import trimesh
    pts, fi = trimesh.sample.sample_surface_even(m, n, seed=seed)
    return pts, m.face_normals[fi]

# ------------------------------------------------------------------ walls
def find_thin_walls(m, spec):
    pts, nr = sample(m, spec["wall_samples"], 0)
    o = pts - nr * 0.01
    d, it = cast(m, o, -nr, spec["ray_chunk"])
    hit = it >= 0; cos = np.zeros(len(pts)); cos[hit] = -np.einsum("ij,ij->i", m.face_normals[it[hit]], nr[hit])
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

# ------------------------------------------------------------------ reach
def parse_dirs(text):
    """'+Z,-Z,+X,0.97/0/-0.24' -> list of unit vectors."""
    out = []
    for tok in text.replace(";", ",").split(","):
        tok = tok.strip().lower()
        if not tok: continue
        if tok[-1] in AXES and len(tok) <= 2: v = AXES[tok[-1]] * (-1 if tok.startswith("-") else 1)
        else: v = Vector(*[float(c) for c in tok.split("/")])
        out.append(v.normalized())
    return out

def reach_candidates(setups, holes, max_extra=24):
    """6 axes + the face-count setup directions + the biggest hole axes (both ways), duplicates within ~2.5 deg merged."""
    cands = [s * a for a in AXES.values() for s in (1, -1)] + [s["vec"] for s in setups]
    for h in sorted(holes, key=lambda h: -h["area"]):
        if len(cands) >= 6 + len(setups) + max_extra: break
        cands += [h["axis"], -h["axis"]]
    out = []
    for c in cands:
        if not any(c.dot(o) > 0.999 for o in out): out.append(c.normalized())
    return out

def visibility(m, pts, nr, dirs, chunk):
    """V[i, j] = surface point i can be seen straight from direction j (faces it or is a wall, nothing in the way)."""
    V = np.zeros((len(pts), len(dirs)), bool)
    for j, v in enumerate(dirs):
        d = np.array([v.X, v.Y, v.Z]); ok = nr @ d > -0.02
        if ok.any():
            o = pts[ok] + nr[ok] * 0.05
            V[np.where(ok)[0], j] = ~cast(m, o, d, chunk, first=False)
    return V

def greedy_cover(V, min_gain=0.001):
    """Fewest columns covering what any column covers; stops when the next one adds < min_gain of the surface."""
    left, chosen = V.any(axis=1), []
    while left.any():
        gain = (V & left[:, None]).sum(axis=0); j = int(gain.argmax())
        if gain[j] < max(1, min_gain * len(V)): break
        chosen.append((j, int(gain[j]))); left &= ~V[:, j]
    return chosen

def find_reach(m, spec, setups, holes, planned=None):
    pts, nr = sample(m, spec["reach_samples"], 1); n = len(pts); area = m.area / n
    dirs = planned or reach_candidates(setups, holes)
    V = visibility(m, pts, nr, dirs, spec["ray_chunk"])
    pct = lambda k: round(100.0 * int(k) / n, 2)               # int(): numpy and Python round halves differently
    chosen = greedy_cover(V, spec["reach_min_gain_pct"] / 100.0); cum = np.zeros(n, bool); cover = []
    for j, g in chosen:
        cum |= V[:, j]; cover.append(dict(direction=dir_name(dirs[j]), vector=xyz(dirs[j], 3), adds_pct=pct(g), total_pct=pct(cum.sum())))
    est = [i for i, d in enumerate(dirs) if any(d.dot(s["vec"]) > 0.999 for s in setups)]
    est_cov = pct(V[:, est].any(axis=1).sum()) if est else None
    bad = ~V.any(axis=1); cells = {}
    for p in pts[bad]: k = tuple((np.round(p / 10) * 10).astype(int)); cells[k] = cells.get(k, 0) + 1
    worst = sorted(cells.items(), key=lambda kv: -kv[1])[:10]
    rest = round(pct(V.any(axis=1).sum()) - (cover[-1]["total_pct"] if cover else 0), 2)
    return dict(samples=n, mode="planned" if planned else "candidate", n_directions_tried=len(dirs), left_to_small_directions_pct=rest,
                unreachable_pct=pct(bad.sum()), unreachable_mm2=round(float(bad.sum() * area)),
                min_directions=cover, setup_estimate_cover_pct=est_cov,
                per_direction=[dict(direction=dir_name(d), vector=xyz(d, 3), sees_pct=pct(V[:, j].sum())) for j, d in enumerate(dirs)],
                unreachable_areas=[dict(around=[int(x) for x in k], mm2=int(round(c * area))) for k, c in worst])

def report_text(name, part, spec, setups, small, sharp, walls, mesh, reach, lips=(), guide_corners=()):
    L = spec["max_listed"]; rmin = min(spec["tool_radii_mm"]); ax = spec["spindle_axis"].upper()
    vert = [c for c in sharp if c["vertical"]] + [c for c in small if c["vertical"]]
    bb = part.solid.bounding_box().size
    out = [f"CNC check: {name}",
           f"size {bb.X:.1f} x {bb.Y:.1f} x {bb.Z:.1f} mm, volume {part.solid.volume/1000:.2f} cm3, "
           f"{part.n_solids} solid(s), valid: {part.valid}",
           f"rules: tools r {spec['tool_radii_mm']} mm (smallest r{rmin}, corners 1.3× / no exact standard size), "
           + (f"min wall {spec['min_wall_mm']} mm ({spec.get('min_wall_source')})" if spec.get('min_wall_mm') is not None
              else "min wall not set") + f", spindle {ax}", "",
           f"1. Setups: about {len(setups)} tool direction(s) needed (lower bound, ignores shadowing)"]
    out += [f"   - from {s['direction']}: {s['flat_faces']} flat faces, {s['holes']} holes" for s in setups]
    out += ["", f"2. Inside corners smaller than the smallest tool (r{rmin}): {len(small)} rounded, {len(sharp)} sharp (r0)"]
    out += [f"   - r{c['r']} {c['kind']} at {c['at']}" for c in small[:L]]
    n_u = sum(1 for c in guide_corners if c.get("under_1_3"))
    n_e = sum(1 for c in guide_corners if c.get("exact_standard"))
    out += [f"   guide rule (docs/CNC-MACHINING-RULES.md CNC-CORNER-R): {n_u} under 1.3× nearest standard tool, {n_e} exact standard size"]
    for c in guide_corners[:L]:
        why = []
        if c.get("under_1_3"): why.append(f"need ≥ r{c['required_r']} (1.3× r{c['nearest_tool_r']})")
        if c.get("exact_standard"): why.append("exact standard tool size")
        out.append(f"   - r{c['r']} {c['kind']} at {c['at']}: " + ", ".join(why))
    if len(guide_corners) > L: out.append(f"   ... {len(guide_corners) - L} more in the JSON")
    rnd = sum(c["round_edge"] for c in sharp)
    if sharp: out.append(f"   sharp edges ({rnd} are round edges such as bore shoulders or grooves, usually fine when turned or bored):")
    out += [f"   - {c['length']} mm {c['edge']} edge at {c['at']}, faces meet at {c['face_angle_deg']} deg"
            + (f" (split by a sliver face, {c['net_turn_deg']} deg turn across it)" if c.get("sliver_face") else "") for c in sharp[:L]]
    if len(sharp) > L: out.append(f"   ... {len(sharp) - L} more in the JSON")
    if spec.get("lip_max_mm"):
        out.append(f"   lips (not counted above): {len(lips)} concave edge(s), {sum(c['length'] for c in lips):.0f} mm in total, next to a face "
                   f"narrower than {spec['lip_max_mm']} mm with the faces either side within 15 deg of tangent (tiny steps such as "
                   f"blend run-outs; listed in the JSON, lip_max_mm 0 turns this off)")
    out += ["", f"3. Vertical inside corners a {ax}-down cutter can't make: {len(vert)}"]
    out += [f"   - {'sharp' if 'length' in c else 'r' + str(c['r'])} at {c['at']}" + (f", {c['length']} mm tall" if 'length' in c else "")
            for c in vert[:L]]
    if vert: out.append(f"   Fix: add a corner radius of 1.3× the nearest standard tool (never an exact standard size); r{rmin} is the smallest configured tool.")
    if walls and walls.get("checked") is False:
        out += ["", f"4. Walls: {walls['reason']}"]
    elif walls:
        out += ["", f"4. Walls thinner than {spec['min_wall_mm']} mm: {len(walls['thin_spots'])} spot(s) "
                f"(thinnest wall found {walls['min_wall_mm']} mm, {walls['wall_samples']} wall samples)"]
        out += [f"   - {s['t_mm']} mm at {s['at']}" for s in walls["thin_spots"][:L]]
        if walls["thin_spots"]:
            if walls.get("fail_thin"):
                out.append("   FAIL: CNC walls under the minimum in docs/CNC-MACHINING-RULES.md "
                           f"({walls.get('material') or 'metal'} floor {walls.get('floor_mm', spec['min_wall_mm'])} mm, "
                           "or a stricter project minimum). Thicker is better; don't design to the minimum.")
            else:
                out.append("   These are candidates: for 3D printed parts the minimum applies to structural / critical "
                           "features only. Classify each one (structural = fix; other or unclear = flag for the user to "
                           "change or approve); never auto-fix or auto-fail.")
    else: out += ["", "4. Walls: not checked (no usable mesh)"]
    msrc = f"mesh: {mesh['source']}" + (f" ({mesh['method']})" if mesh.get("method") else "") + (f", {mesh['triangles']} triangles, {mesh['open_edges']} open edge(s)" if mesh.get("triangles") else "")
    out.append("   " + msrc); out += [f"   note: {t}" for t in mesh["notes"]]
    if reach:
        out += ["", f"5. Reach (line of sight from {reach['n_directions_tried']} {reach['mode']} direction(s), {reach['samples']} surface points):",
                f"   fewest directions that cover the reachable surface: {len(reach['min_directions'])} (each adds >= {spec['reach_min_gain_pct']}%)"]
        out += [f"   - from {c['direction']}: +{c['adds_pct']}% -> {c['total_pct']}%" for c in reach["min_directions"]]
        if reach["setup_estimate_cover_pct"] is not None and reach["mode"] == "candidate":
            out.append(f"   the {len(setups)} setup(s) from item 1 see {reach['setup_estimate_cover_pct']}% of the surface")
        if reach["left_to_small_directions_pct"] > 0:
            out.append(f"   ({reach['left_to_small_directions_pct']}% more is visible only from directions that each add < {spec['reach_min_gain_pct']}%; per_direction in the JSON)")
        out.append(f"   unreachable from every direction tried: {reach['unreachable_pct']}% (~{reach['unreachable_mm2']} mm2)")
        out += [f"   - ~{a['mm2']} mm2 around {a['around']}" for a in reach["unreachable_areas"][:L]]
    failed = bool(walls and walls.get("fail_thin") and walls.get("thin_spots"))
    flagged = bool(small or guide_corners or [c for c in sharp if not c["round_edge"]] or vert or (walls and walls.get("thin_spots")) or failed)
    if failed and flagged:
        result = "FAIL (see walls above); other items to look at"
    elif failed:
        result = "FAIL (see walls above)"
    elif flagged:
        result = "things to look at (see above)"
    else:
        result = "nothing flagged"
    out += ["", "Result: " + result]
    return "\n".join(out), flagged, failed

def peak_rss_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)     # Linux: KiB

def main(argv=None):
    ap = argparse.ArgumentParser(description="CNC design check of a STEP file (setups, inside corners, vertical corners, thin walls, optional reach).",
                                 epilog="Spec keys and defaults: " + json.dumps(DEFAULTS))
    ap.add_argument("step", help="part .step/.stp")
    ap.add_argument("--spec", help="JSON with any of the spec keys below (tool radii, min wall, samples, ray_chunk, ...)")
    ap.add_argument("--out", help="output prefix (default: STEP path without extension + '_cnc')")
    ap.add_argument("--stl", help="mesh of the same part (same units and position) for the wall scan / reach instead of meshing the STEP")
    ap.add_argument("--reach", nargs="?", const="auto", metavar="DIRS",
                    help="surface reachability; alone = try the 6 axes + setup + hole directions, or give planned directions "
                         "like '+Z,-Z,+X,0.97/0/-0.24'")
    ap.add_argument("--process", choices=("machined", "printed"), help="machined (default): CNC wall floors apply and thin walls FAIL; "
                    "printed: no assumed minimum, thin spots are candidates")
    ap.add_argument("--material", choices=("metal", "plastic"), help="CNC wall floor: metal 0.762 mm (default) or plastic 1.52 mm")
    ap.add_argument("--min-wall", type=float, metavar="MM", help="minimum wall in mm. CNC: default is the guide floor; a stricter value "
                    "is kept, a looser one is raised to the floor. Printed: required or walls are not checked")
    ap.add_argument("--walls-config", metavar="TOML", help="the project's wall-check config (tools/checks/walls.example.toml format); "
                    "its min_wall is used when --min-wall and spec min_wall_mm are not given")
    ap.add_argument("--strict", action="store_true", help="exit 1 if anything is flagged")
    a = ap.parse_args(argv)
    spec = dict(DEFAULTS, **(json.load(open(a.spec)) if a.spec else {}))
    if a.process: spec["process"] = a.process
    if a.material: spec["material"] = a.material
    try:
        spec["min_wall_mm"], spec["min_wall_source"], wall_meta = resolve_min_wall(spec, a.min_wall, a.walls_config)
    except (ValueError, OSError) as ex: sys.exit(f"cnc_check: {ex}")
    spec["process"] = wall_meta["process"]
    spec["material"] = wall_meta["material"]
    if spec["spindle_axis"] not in AXES: sys.exit("spindle_axis must be x, y or z")
    try: planned = parse_dirs(a.reach) if a.reach and a.reach != "auto" else None
    except Exception: sys.exit(f"--reach: can't read directions {a.reach!r} (use e.g. '+Z,-X,0.97/0/-0.24'; put --reach after the STEP file)")
    T = {}; t0 = time.perf_counter(); tic = lambda k: T.__setitem__(k, round(time.perf_counter() - t0 - sum(T.values()), 1))
    part = Part(a.step); tic("load_step")
    small, sharp, holes, lips, guide_corners = find_corners(part, spec); tic("corners")
    setups = find_setups(part, holes); tic("setups")
    m, mesh = load_mesh(part, a.stl, mesh_tol(part, spec)); tic("mesh")
    if m is None: walls = None
    elif spec["min_wall_mm"] is None: walls = dict(checked=False, reason=NOT_CHECKED)
    else: walls = dict(find_thin_walls(m, spec), checked=True, min_wall_set_mm=spec["min_wall_mm"], source=spec["min_wall_source"],
                      **{k: wall_meta[k] for k in ("process", "material", "floor_mm", "fail_thin")})
    tic("walls")
    reach = find_reach(m, spec, setups, holes, planned) if (a.reach and m is not None) else None
    if a.reach: tic("reach")
    txt, flagged, failed = report_text(os.path.basename(a.step), part, spec, setups, small, sharp, walls, mesh, reach, lips, guide_corners)
    txt += f"\n(time {sum(T.values()):.1f} s, peak memory {peak_rss_mb():.0f} MB)"
    pre = a.out or os.path.splitext(a.step)[0] + "_cnc"
    open(pre + ".txt", "w").write(txt + "\n")
    setups_js = [{k: v for k, v in s.items() if k != "vec"} for s in setups]
    js = dict(part=a.step, spec=spec, n_solids=part.n_solids, valid=part.valid, setups=setups_js,
              holes=[dict(h, axis=xyz(h["axis"], 3), area=round(h["area"], 1)) for h in holes], small_fillets=small, sharp_concave_edges=sharp, lips=lips,
              vertical_corners=[c for c in sharp + small if c["vertical"]], guide_corners=guide_corners,
              mesh=mesh, walls=walls, reach=reach, flagged=flagged, failed=failed,
              timing_s=T, peak_rss_mb=peak_rss_mb())
    json.dump(js, open(pre + ".json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(txt); print(f"wrote {pre}.txt, {pre}.json")
    sys.exit(1 if a.strict and flagged else 0)

if __name__ == "__main__": main()
