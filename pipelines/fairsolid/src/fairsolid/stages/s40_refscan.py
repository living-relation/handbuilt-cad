"""Stage 40 - reference scan mode (plan part 10).

Some scans are not parts. The oil catch scan is the space between the firewall
and the engine, scanned so a new bracket can be designed to fit it. Forcing
that into a closed solid is wrong, so this stage keeps it as separate open
surfaces and adds reference geometry to model against:

1. The scan is moved into the run's frame (stage 20) by rotation and
   translation only. Nothing is ever scaled; edge lengths are checked.
2. Floating scraps are dropped and the mesh is lightly smoothed (Taubin keeps
   the size).
3. The surface is split into smooth patches by region growing: a face joins a
   patch when it bends less than `crease_deg` from its neighbour and stays
   within `cone_deg` of the patch's mean direction. The cone keeps each patch
   a height field over its own plane, so one smooth surface can describe it.
   Small patches (hoses, brackets, clutter) are left out on purpose.
4. Each patch is resampled on a regular grid over its own plane and fitted
   with a smoothing cubic spline (scipy). x and y are linear in (u, v), so the
   spline is written out exactly as an OpenCascade B-spline surface.
5. Each surface is trimmed to its patch outline. The raw outline is a union of
   grid cells (stair-stepped); it is closed, resampled evenly, smoothed along
   its length and trimmed with a periodic spline, so the edges are tidy.
6. Reference geometry: the frame origin and axes, a datum plane for every
   patch that is flat within `datum_flat_mm`, and a point and direction for
   every other patch.
7. Optional: `knit` sews the patches into one shell (gaps stay open where
   the scan is open), and `patch_boxes` fits one bridging surface over every
   scan point inside an axis-aligned box, to model across a gap.

Writes 40_ref_surfaces.step (+ .stl), 40_ref_datums.step, 40_ref.json and
40_ref_render.png (grey scan on top, shaded surfaces below, same cameras).
"""
from __future__ import annotations

import argparse
import json
import time
from collections import deque
from pathlib import Path

import numpy as np
import trimesh
from scipy.interpolate import RectBivariateSpline, griddata
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

from ..geom import Frame
from ..subproc import emit

CELL_MM = 2.5           # grid step of the surface fit
CREASE_DEG = 12.0       # max bend between neighbouring faces inside a patch
CONE_DEG = 50.0         # max lean from the patch's mean direction
MIN_PATCH_FRAC = 0.015  # patches smaller than this share of the area are left out
DATUM_FLAT_MM = 0.5     # rms from a plane below which a patch gets a datum plane
ON_PATCH_MM = 3.0       # scan points this close to a surface count as "on a panel"
EDGE_MARGIN = 0.6       # tidy edges are grown by this many cells so neighbours meet


# == geometry helpers (no OpenCascade) ========================================

def rigid_to_frame(mesh: trimesh.Trimesh, frame: Frame) -> tuple[trimesh.Trimesh, dict]:
    """Rotate and translate into the frame. Never scales; proves it."""
    v = frame.to_canonical(np.asarray(mesh.vertices, float))
    out = trimesh.Trimesh(v, np.asarray(mesh.faces), process=False)
    e = np.asarray(mesh.edges_unique)[:2000]
    a = np.linalg.norm(np.asarray(mesh.vertices)[e[:, 0]] - np.asarray(mesh.vertices)[e[:, 1]], axis=1)
    b = np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1)
    ratio = float(np.median(b / np.maximum(a, 1e-12))) if len(e) else 1.0
    if abs(ratio - 1.0) > 1e-6:
        raise ValueError(f"frame changed the scan size (edge ratio {ratio}); refusing")
    return out, {"scale_applied": False, "edge_length_ratio": ratio}


def clean_mesh(mesh: trimesh.Trimesh, *, target_faces: int = 80_000,
               min_component_frac: float = 0.05, smooth_steps: int = 20) -> trimesh.Trimesh:
    """Drop floating scraps, decimate, light Taubin smoothing (size-preserving)."""
    import pymeshlab
    ms = pymeshlab.MeshSet()
    ms.add_mesh(pymeshlab.Mesh(np.asarray(mesh.vertices, float), np.asarray(mesh.faces)))
    ms.meshing_remove_connected_component_by_diameter(
        mincomponentdiag=pymeshlab.PercentageValue(100 * min_component_frac))
    if ms.current_mesh().face_number() > target_faces:
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=target_faces, preservenormal=True)
    if smooth_steps:
        ms.apply_coord_taubin_smoothing(stepsmoothnum=smooth_steps)
    m = ms.current_mesh()
    return trimesh.Trimesh(m.vertex_matrix(), m.face_matrix(), process=True)


def grow_patches(mesh: trimesh.Trimesh, *, crease_deg: float = CREASE_DEG,
                 cone_deg: float = CONE_DEG, min_area_frac: float = MIN_PATCH_FRAC) -> list[np.ndarray]:
    """Smooth patches (face index arrays), largest first; small ones dropped."""
    N = np.asarray(mesh.face_normals); A = np.asarray(mesh.area_faces)
    nbr = [[] for _ in range(len(N))]
    for a, b in np.asarray(mesh.face_adjacency):
        nbr[a].append(b); nbr[b].append(a)
    rough = np.array([np.mean([1 - N[i] @ N[j] for j in nb]) if nb else 1.0 for i, nb in enumerate(nbr)])
    c_crease, c_cone = np.cos(np.radians(crease_deg)), np.cos(np.radians(cone_deg))
    label = -np.ones(len(N), int)
    patches = []
    for seed in np.argsort(rough, kind="stable"):
        if label[seed] >= 0:
            continue
        rid = len(patches); label[seed] = rid
        q, members, nsum = deque([seed]), [seed], N[seed] * A[seed]
        while q:
            f = q.popleft(); nm = nsum / np.linalg.norm(nsum)
            for g in nbr[f]:
                if label[g] < 0 and N[f] @ N[g] > c_crease and N[g] @ nm > c_cone:
                    label[g] = rid; q.append(g); members.append(g); nsum = nsum + N[g] * A[g]
        patches.append(np.array(members))
    total = A.sum()
    keep = [p for p in patches if A[p].sum() > min_area_frac * total]
    return sorted(keep, key=lambda p: -A[p].sum())


def patch_axes(mesh: trimesh.Trimesh, faces: np.ndarray):
    """Centre and right-handed axes (e1, e2, n) with n the area-weighted normal."""
    pts = np.asarray(mesh.vertices)[np.unique(np.asarray(mesh.faces)[faces])]
    n = (np.asarray(mesh.face_normals)[faces] * np.asarray(mesh.area_faces)[faces, None]).sum(0)
    n = n / np.linalg.norm(n)
    e1 = np.cross(n, [0, 0, 1] if abs(n[2]) < 0.9 else [1, 0, 0]); e1 /= np.linalg.norm(e1)
    return pts, pts.mean(0), e1, np.cross(n, e1), n


def fit_heightfield(uvh: np.ndarray, *, cell: float = CELL_MM, noise: float = 0.1,
                    max_cells: int = 160) -> RectBivariateSpline:
    """Smoothing cubic spline h(u, v) over a regular grid covering the points."""
    lo, hi = uvh[:, :2].min(0) - cell, uvh[:, :2].max(0) + cell
    nu = int(min(max_cells, max(6, np.ceil((hi[0] - lo[0]) / cell))))
    nv = int(min(max_cells, max(6, np.ceil((hi[1] - lo[1]) / cell))))
    gu, gv = np.linspace(lo[0], hi[0], nu), np.linspace(lo[1], hi[1], nv)
    U, V = np.meshgrid(gu, gv, indexing="ij")
    h = griddata(uvh[:, :2], uvh[:, 2], (U, V), method="linear")
    hn = griddata(uvh[:, :2], uvh[:, 2], (U, V), method="nearest")
    h = gaussian_filter(np.where(np.isnan(h), hn, h), 0.7)
    return RectBivariateSpline(gu, gv, h, kx=3, ky=3, s=h.size * noise ** 2)


def raw_outline(uv: np.ndarray, cell: float = CELL_MM):
    """Union of occupied grid cells, closed over one-cell gaps (stair-stepped)."""
    from shapely.geometry import box
    from shapely.ops import unary_union
    ij = np.unique(np.floor(uv / cell).astype(int), axis=0)
    occ = unary_union([box(i * cell, j * cell, (i + 1) * cell, (j + 1) * cell) for i, j in ij])
    occ = occ.buffer(cell).buffer(-cell)
    return occ if occ.geom_type == "Polygon" else max(occ.geoms, key=lambda p: p.area)


def tidy_outline(poly, cell: float = CELL_MM, *, spacing: float | None = None, sigma: float = 2.0,
                 margin: float = 0.0):
    """Even, smooth boundary: resample every `spacing` mm along the outline and
    smooth the samples along the loop (Gaussian, `sigma` samples). Small notches
    and the grid's stair steps go; the overall shape and size stay. `margin`
    then grows the outline (round corners) so neighbouring surfaces meet
    instead of leaving a gap where the scan bends from one patch to the next."""
    from scipy.ndimage import gaussian_filter1d
    from shapely.geometry import Polygon
    spacing = spacing or 1.5 * cell
    ring = poly.exterior
    n = max(12, int(ring.length / spacing))
    pts = np.array([ring.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, n, endpoint=False)])
    sm = np.column_stack([gaussian_filter1d(pts[:, k], sigma, mode="wrap") for k in (0, 1)])
    out = Polygon(sm).buffer(0)
    if margin:
        out = out.buffer(margin, quad_segs=8)
    if out.geom_type != "Polygon":
        out = max(out.geoms, key=lambda p: p.area)
    return out


def turning(poly) -> float:
    """Total absolute turning of the outline in full turns (1.0 = a convex loop).
    Stair steps add a quarter turn per corner, so lower means tidier."""
    p = np.asarray(poly.exterior.coords)[:-1]
    d = np.roll(p, -1, 0) - p
    a = np.arctan2(d[:, 1], d[:, 0])
    da = (np.diff(np.r_[a, a[0]]) + np.pi) % (2 * np.pi) - np.pi
    return float(np.abs(da).sum() / (2 * np.pi))


def plane_fit(pts: np.ndarray):
    c = pts.mean(0)
    _, s, vt = np.linalg.svd(pts - c, full_matrices=False)
    n = vt[2]; rms = float(s[2] / np.sqrt(len(pts)))
    return c, n, rms


def point_to_mesh(points: np.ndarray, mesh: trimesh.Trimesh, k: int = 12,
                  max_edge: float = 1.5) -> np.ndarray:
    """Distance from each point to the mesh: exact point-to-triangle on the k
    triangles with the nearest centres (numpy only, no rtree). Long triangles
    are split first (to `max_edge`), because a flat B-spline face tessellates
    into a few huge triangles whose centres are far from most points on them."""
    v, f = trimesh.remesh.subdivide_to_size(np.asarray(mesh.vertices, float), np.asarray(mesh.faces), max_edge)
    tri = np.asarray(v, float)[np.asarray(f)]
    _, idx = cKDTree(tri.mean(1)).query(points, k=min(k, len(tri)))
    idx = idx.reshape(len(points), -1)
    best = np.full(len(points), np.inf)
    for j in range(idx.shape[1]):
        cp = trimesh.triangles.closest_point(tri[idx[:, j]], points)
        best = np.minimum(best, np.linalg.norm(cp - points, axis=1))
    return best


# == OpenCascade ==============================================================

def occ_surface(spl: RectBivariateSpline, c, e1, e2, n):
    """The scipy spline as an exact Geom_BSplineSurface in 3-D. x and y are
    linear in (u, v), so their control points are the Greville abscissae."""
    from OCP.Geom import Geom_BSplineSurface
    from OCP.gp import gp_Pnt
    from OCP.TColgp import TColgp_Array2OfPnt
    from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal
    tx, ty = spl.tck[0], spl.tck[1]
    C = spl.get_coeffs().reshape(len(tx) - 4, len(ty) - 4)
    gx = [tx[i + 1:i + 4].mean() for i in range(len(tx) - 4)]
    gy = [ty[j + 1:j + 4].mean() for j in range(len(ty) - 4)]
    poles = TColgp_Array2OfPnt(1, len(gx), 1, len(gy))
    for i, a in enumerate(gx):
        for j, b in enumerate(gy):
            p = c + a * e1 + b * e2 + C[i, j] * n
            poles.SetValue(i + 1, j + 1, gp_Pnt(*map(float, p)))

    def knots(t):
        uq, mult = np.unique(np.round(t, 9), return_counts=True)
        K, M = TColStd_Array1OfReal(1, len(uq)), TColStd_Array1OfInteger(1, len(uq))
        for i, (x, m) in enumerate(zip(uq, mult)):
            K.SetValue(i + 1, float(x)); M.SetValue(i + 1, int(m))
        return K, M
    (KU, MU), (KV, MV) = knots(tx), knots(ty)
    return Geom_BSplineSurface(poles, KU, KV, MU, MV, 3, 3)


def trimmed_faces(surf, outline, c, e1, e2, n, depth: float) -> tuple[list, str]:
    """Trim the surface to `outline` (in the patch plane) by intersecting it with
    a prism. A periodic spline prism gives smooth edges; a polyline is the
    fallback."""
    import cadquery as cq
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    face = cq.Face(BRepBuilderAPI_MakeFace(surf, 1e-6).Face())
    pl = cq.Plane(origin=tuple(c - n * depth / 2), xDir=tuple(e1), normal=tuple(n))
    pts = [tuple(map(float, p)) for p in list(outline.exterior.coords)[:-1]]
    for how in ("spline", "polyline"):
        try:
            wp = cq.Workplane(pl)
            wp = wp.spline(pts, periodic=True).close() if how == "spline" else wp.polyline(pts).close()
            prism = wp.extrude(depth).val()
            fs = face.intersect(prism).Faces()
            if fs:
                return fs, how
        except Exception:
            continue
    return [], "failed"


def sew(faces: list, tol: float):
    """Knit the faces into a shell. Returns (shape, free_edges, multiple_edges)."""
    import cadquery as cq
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
    s = BRepBuilderAPI_Sewing(tol)
    for f in faces:
        s.Add(f.wrapped)
    s.Perform()
    return cq.Shape.cast(s.SewedShape()), int(s.NbFreeEdges()), int(s.NbMultipleEdges())


def datum_shapes(datums: dict):
    """Square planar faces for datum planes plus the frame origin, for CAD."""
    import cadquery as cq
    out = [cq.Vertex.makeVertex(0, 0, 0)]
    for d in datums["planes"]:
        side = max(10.0, float(d["size_mm"]))
        out.append(cq.Face.makePlane(side, side, cq.Vector(*d["point"]), cq.Vector(*d["normal"])))
    return cq.Compound.makeCompound(out)


def tessellate(shape, tol: float = 0.05, angular: float = 0.05) -> trimesh.Trimesh:
    # BRepMesh barely refines gently curved B-spline faces on the linear
    # deflection alone (a 3 mm sag came out as 20-40 mm triangles), so the
    # angular limit is what keeps this mesh on the surface. The STEP is exact.
    vs, ts = shape.tessellate(tol, angular)
    return trimesh.Trimesh(np.array([v.toTuple() for v in vs]), np.array(ts), process=False)


# == render (matplotlib, like the rest of Fairsolid: no GL context) ============

RENDER_VIEWS = (("iso front", (1.0, -1.2, 0.9)), ("iso back", (-1.0, 1.2, 0.9)), ("from below", (0.3, -0.4, -1.0)))


def _view_matrix(d):
    d = np.asarray(d, float); d /= np.linalg.norm(d)
    up = np.array([0, 0, 1.0]) if abs(d[2]) < 0.95 else np.array([0, 1.0, 0])
    x = np.cross(up, d); x /= np.linalg.norm(x)
    return np.vstack([x, np.cross(d, x), d])   # rows: screen x, screen y, towards viewer


def render_pair(scan: trimesh.Trimesh, result: trimesh.Trimesh, out_path: Path, *, title: str,
                face_budget: int = 25_000) -> Path:
    """Top row: plain grey scan. Bottom row: shaded result. Same camera per column."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    def budget(m):
        if len(m.faces) <= face_budget:
            return m
        try:
            return m.simplify_quadric_decimation(face_count=face_budget)
        except Exception:
            keep = np.random.default_rng(0).choice(len(m.faces), face_budget, replace=False)
            return trimesh.Trimesh(m.vertices, np.asarray(m.faces)[keep], process=False)
    S, Rm = budget(scan), budget(result)
    c = np.asarray(scan.bounds).mean(0); span = float(np.linalg.norm(scan.extents)) * 0.52
    light = np.array([0.35, 0.45, 0.82]); light /= np.linalg.norm(light)
    fig, axes = plt.subplots(2, len(RENDER_VIEWS), figsize=(6 * len(RENDER_VIEWS), 11))
    for col, (name, d) in enumerate(RENDER_VIEWS):
        M = _view_matrix(d)
        for row, (m, base, lab) in enumerate(((S, np.array([0.74, 0.74, 0.74]), "scan"),
                                              (Rm, np.array([0.50, 0.65, 0.85]), "surfaces"))):
            ax = axes[row, col]
            T = (np.asarray(m.triangles, float) - c) @ M.T
            nv = np.asarray(m.face_normals, float) @ M.T
            order = np.argsort(T[:, :, 2].mean(1))
            facing = np.where(nv[:, 2:3] < 0, -nv, nv)
            inten = 0.25 + 0.75 * np.clip(facing @ (M @ light), 0, 1)
            ax.add_collection(PolyCollection(T[order][:, :, :2], facecolors=(base * inten[:, None])[order],
                                             edgecolors="none", antialiased=False))
            ax.set_xlim(-span, span); ax.set_ylim(-span, span); ax.set_aspect("equal"); ax.axis("off")
            ax.set_title(f"{lab} - {name}", fontsize=11)
    fig.suptitle(title, fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=90); plt.close(fig)
    return out_path


# == the stage ================================================================

def run_refscan(scan_path: Path, frame_path: Path, out_dir: Path, *, cell: float = CELL_MM,
                noise: float = 0.1, target_faces: int = 80_000, knit: bool = False,
                knit_tol: float = 1.0, patch_boxes: list | None = None, tidy: bool = True,
                n_measure: int = 150_000, render: bool = True) -> dict:
    import cadquery as cq
    t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    frame = Frame.load(frame_path)
    raw = trimesh.load(scan_path, process=False, force="mesh")
    scan, rigid = rigid_to_frame(raw, frame)
    mesh = clean_mesh(scan, target_faces=target_faces)
    patches = grow_patches(mesh)
    A = np.asarray(mesh.area_faces); total = float(A.sum())
    faces, rows, datums = [], [], {"origin": [0.0, 0.0, 0.0], "axes": {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]},
                                   "planes": [], "points": []}
    for k, p in enumerate(patches):
        pts, c, e1, e2, n = patch_axes(mesh, p)
        uvh = (pts - c) @ np.stack([e1, e2, n]).T
        row = {"patch": k, "area_mm2": round(float(A[p].sum()), 1)}
        try:
            spl = fit_heightfield(uvh, cell=cell, noise=noise)
            surf = occ_surface(spl, c, e1, e2, n)
            rough_poly = raw_outline(uvh[:, :2], cell)
            poly = tidy_outline(rough_poly, cell, margin=EDGE_MARGIN * cell) if tidy else rough_poly.simplify(cell / 3)
            fs, how = trimmed_faces(surf, poly, c, e1, e2, n, float(np.ptp(uvh[:, 2])) + 20)
            if not fs:
                raise RuntimeError("trim gave no face")
            faces += fs
            row.update(ok=True, trim=how, n_faces=len(fs),
                       outline_turns_raw=round(turning(rough_poly.simplify(cell / 3)), 2),
                       outline_turns=round(turning(poly), 2))
        except Exception as exc:          # one bad patch must not lose the rest
            row.update(ok=False, error=str(exc)[:200])
        pc, pn, prms = plane_fit(pts)
        if pn @ n < 0:
            pn = -pn
        size = float(np.ptp(uvh[:, :2], axis=0).min())
        if prms <= DATUM_FLAT_MM:
            datums["planes"].append({"patch": k, "point": [round(float(x), 3) for x in pc],
                                     "normal": [round(float(x), 5) for x in pn], "rms_mm": round(prms, 3),
                                     "size_mm": round(size, 1)})
        else:
            datums["points"].append({"patch": k, "point": [round(float(x), 3) for x in c],
                                     "direction": [round(float(x), 5) for x in n], "plane_rms_mm": round(prms, 3)})
        rows.append(row)
    for b in patch_boxes or []:
        lo, hi = np.asarray(b[:3], float), np.asarray(b[3:], float)
        inside = np.all((mesh.vertices >= lo) & (mesh.vertices <= hi), axis=1)
        row = {"patch_box": [float(x) for x in b], "n_points": int(inside.sum())}
        if inside.sum() >= 30:
            pts = np.asarray(mesh.vertices)[inside]
            c, n, _ = plane_fit(pts)
            e1 = np.cross(n, [0, 0, 1] if abs(n[2]) < 0.9 else [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
            uvh = (pts - c) @ np.stack([e1, e2, n]).T
            try:
                from shapely.geometry import MultiPoint
                surf = occ_surface(fit_heightfield(uvh, cell=cell, noise=noise), c, e1, e2, n)
                hull = MultiPoint([tuple(q) for q in uvh[:, :2]]).convex_hull
                fs, how = trimmed_faces(surf, tidy_outline(hull, cell), c, e1, e2, n, float(np.ptp(uvh[:, 2])) + 20)
                faces += fs; row.update(ok=bool(fs), trim=how, n_faces=len(fs))
            except Exception as exc:
                row.update(ok=False, error=str(exc)[:200])
        else:
            row.update(ok=False, error="fewer than 30 scan points in the box")
        rows.append(row)
    if not faces:
        raise RuntimeError("no surface could be fitted")
    comp = cq.Compound.makeCompound(faces)
    knit_info = None
    if knit:
        shell, free, multi = sew(faces, knit_tol)
        knit_info = {"tolerance_mm": knit_tol, "free_edges": free, "multiple_edges": multi}
        comp = shell
    step = out_dir / "40_ref_surfaces.step"
    cq.exporters.export(cq.Workplane().add(comp), str(step))
    cq.exporters.export(cq.Workplane().add(datum_shapes(datums)), str(out_dir / "40_ref_datums.step"))
    res_mesh = tessellate(comp); res_mesh.export(out_dir / "40_ref_surfaces.stl")
    pts, _ = trimesh.sample.sample_surface(scan, n_measure, seed=0)
    d = point_to_mesh(np.asarray(pts), res_mesh)
    on = d <= ON_PATCH_MM
    pct = lambda m, x: round(float(100 * np.mean(m <= x)), 1)
    metrics = {
        "all_points": {"median_mm": round(float(np.median(d)), 4), "p95_mm": round(float(np.percentile(d, 95)), 3),
                       "pct_within_0.2mm": pct(d, .2), "pct_within_0.5mm": pct(d, .5)},
        "on_panels": {"share_of_scan_pct": round(float(100 * on.mean()), 1),
                      "median_mm": round(float(np.median(d[on])), 4), "p95_mm": round(float(np.percentile(d[on], 95)), 3),
                      "pct_within_0.2mm": pct(d[on], .2), "pct_within_0.5mm": pct(d[on], .5)},
        "n_points": int(len(d)), "on_panel_cutoff_mm": ON_PATCH_MM}
    ok = [r for r in rows if r.get("ok") and "outline_turns" in r]
    tid = {"mean_turns_raw": round(float(np.mean([r["outline_turns_raw"] for r in ok])), 2) if ok else None,
           "mean_turns_tidy": round(float(np.mean([r["outline_turns"] for r in ok])), 2) if ok else None,
           "note": "full turns of each patch outline; 1.0 = a smooth convex loop, stair steps add a quarter turn each"}
    render_path = None
    if render:
        render_path = render_pair(scan, res_mesh, out_dir / "40_ref_render.png",
                                  title=f"Reference scan: {len(faces)} surfaces "
                                        f"(median {metrics['on_panels']['median_mm']:.2f} mm on panels)")
    report = {"stage": "40_refscan", "mode": "reference scan (plan part 10)", "scan": str(scan_path),
              "frame": str(frame_path), **rigid, "cell_mm": cell, "noise_mm": noise,
              "n_patches_found": len(patches), "n_surfaces": len(faces),
              "covered_area_frac": round(float(sum(A[p].sum() for p in patches) / total), 3),
              "patches": rows, "datums": datums, "knit": knit_info, "edges": tid, "metrics": metrics,
              "files": {"surfaces_step": str(step), "surfaces_stl": str(out_dir / "40_ref_surfaces.stl"),
                        "datums_step": str(out_dir / "40_ref_datums.step"),
                        "render": str(render_path) if render_path else None},
              "runtime_s": round(time.time() - t0, 1)}
    (out_dir / "40_ref.json").write_text(json.dumps(report, indent=1))
    report["report"] = str(out_dir / "40_ref.json")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scan"); ap.add_argument("frame"); ap.add_argument("out_dir")
    ap.add_argument("--cell", type=float, default=CELL_MM)
    ap.add_argument("--noise", type=float, default=0.1)
    ap.add_argument("--knit", action="store_true")
    ap.add_argument("--knit-tol", type=float, default=1.0)
    ap.add_argument("--patch-box", type=float, nargs=6, action="append", default=[])
    ap.add_argument("--no-tidy", action="store_true")
    a = ap.parse_args()
    res = run_refscan(Path(a.scan), Path(a.frame), Path(a.out_dir), cell=a.cell, noise=a.noise,
                      knit=a.knit, knit_tol=a.knit_tol, patch_boxes=a.patch_box, tidy=not a.no_tidy)
    emit({k: res[k] for k in ("n_surfaces", "n_patches_found", "covered_area_frac", "metrics", "edges",
                              "knit", "datums", "files", "report", "runtime_s", "scale_applied")})


if __name__ == "__main__":
    main()
