"""Stage 30 - fit the flat, round and freeform areas, snap, report.

The first chunk of the surface-fit build (docs/SURFACE_FIT_PLAN.md, part 3).
It runs after orientation (stage 20) and only measures: there is NO trimming
or knitting here, and no solid is made. What comes out is

  30_fit.json    the fit report: every area, its least-squares fit, its error
                 against the averaged scan, what was snapped and why, the
                 tolerance used, the unit table, and the overall size check
  30_areas.png   the area map - every face coloured by the area it belongs to,
                 grey for "other"
  30_labels.npy  the area id of every face of the averaged scan (-1 = other)

Decisions from the plan that this follows to the letter:

* Error is always measured against the AVERAGED scan surface (10_clean.ply,
  the Poisson surface), never against raw points.
* The scan is read once at true size. The only transform applied is the
  rigid one from stage 20, and it is checked to be rigid. The unit choice
  (metric / inch) only picks which hole-size table snapping uses. It never
  scales anything.
* Snapping happens only when it stays within tolerance: a snap is accepted
  only if it moves the fitted surface by no more than the tolerance anywhere
  over the area it describes.
* The overall size of the result is checked against the scan. If it is off -
  and above all if it is off by about 25.4x, a unit mix-up - the run stops.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy.optimize import least_squares
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from ..geom import Frame
from ..primitives import (
    Cylinder, Plane, dedupe_cylinders, extract_cylinders, extract_holes,
    extract_planes, noise_floor, refine_plane, surface_noise,
)
from ..subproc import emit

# -- tolerance -----------------------------------------------------------
# the user's ranges (plan part 1): small machined parts 0.02-0.1 mm, large
# objects 0.1-0.2 mm. A part counts as "small" when its longest side is at
# most SMALL_PART_MM. The default inside the band is twice the measured
# noise of the averaged surface, clamped to the band; the value actually used
# is always written to the report.
SMALL_PART_MM = 50.0
BAND_SMALL = (0.02, 0.1)
BAND_LARGE = (0.1, 0.2)
TOL_NOISE_FACTOR = 2.0

# -- area map --------------------------------------------------------------
# A face joins a flat/round area when it lies within LABEL_NOISE_FACTOR x
# noise (or the tolerance, if larger) of the surface and faces the same way
# to within LABEL_ANGLE_DEG. Patches smaller than MIN_PATCH_MM2 (or
# MIN_PATCH_FRAC of the surface) are noise and go back to "other".
LABEL_NOISE_FACTOR = 3.0
LABEL_ANGLE_DEG = 25.0
MIN_PATCH_MM2 = 4.0
MIN_PATCH_FRAC = 0.001

# -- snapping ----------------------------------------------------------------
# Directions within SNAP_ANGLE_DEG of parallel or of square are candidates;
# the tolerance check then decides. Axes closer than COAX_CANDIDATE_MM (or
# 5x tolerance) are coaxial candidates.
SNAP_ANGLE_DEG = 3.0
COAX_CANDIDATE_MM = 1.0

# Size check: a ratio within this fraction of 25.4 (or 1/25.4) is reported
# as a unit mix-up rather than an ordinary size error.
INCH = 25.4
UNIT_RATIO_SLACK = 0.03

# Plane detection: RANSAC inlier band, and the rms above which a "plane" is
# treated as a chord across a curved surface rather than a flat face.
PLANE_RANSAC_MM = 0.4


# Hole finder: smallest diameter looked for (the metric table starts at 1).
HOLE_MIN_D_MM = 2.0

# Round check for everything the old circle search (extract_cylinders) finds:
# bosses and the larger cylinders. Same evidence the hole finder asks of a
# hole: the faces that lie on the circle AND face along its radius must
# cover ROUND_MIN_COVERAGE of the turn, and fit within ROUND_MAX_RMS_NOISE x
# the measured noise. Its own 55% coverage counted any point in the band,
# whichever way it faced, over the whole length of the part, so cast texture
# and freeform curves at different heights added up to a "circle" - and the
# per-area refit then turned a 20-degree sliver into a d84 or d243 "boss".
# The check runs twice: on each candidate before the area map (so its faces
# can go to a flat face instead), and on each area after its own fit (the
# refit can move the axis and radius a long way on a short arc).
ROUND_MIN_COVERAGE = 0.6
ROUND_MAX_RMS_NOISE = 3.0
ROUND_FACING_DEG = 30.0
ROUND_BINS = 36


def plane_max_rms(nf: float) -> float:
    return max(5.0 * nf, 0.25 * PLANE_RANSAC_MM)


# Points used for a nonlinear cylinder fit; the error stats always use all.
FIT_POINT_CAP = 40_000


class SizeCheckError(RuntimeError):
    """The model's overall size does not match the scan. The run must stop."""


# == hole-size tables =========================================================

def _metric_table() -> np.ndarray:
    """Common metric hole sizes (diameters, mm).

    0.5 mm steps to 12, whole mm to 50, 2 mm to 100, 5 mm to 300, plus the
    ISO coarse tap-drill sizes that fall between those steps.
    """
    sizes = set(np.round(np.arange(1.0, 12.0 + 1e-9, 0.5), 3))
    sizes |= set(np.arange(13.0, 50.0 + 1e-9, 1.0))
    sizes |= set(np.arange(52.0, 100.0 + 1e-9, 2.0))
    sizes |= set(np.arange(105.0, 300.0 + 1e-9, 5.0))
    sizes |= {2.5, 3.3, 4.2, 6.8, 8.5, 10.2, 14.0, 17.5, 21.0}
    return np.array(sorted(float(s) for s in sizes))


def _inch_table() -> np.ndarray:
    """Fractional-inch hole sizes, converted to mm (the size, not the part).

    1/64" steps to 1/2", 1/32" to 1", 1/16" to 2", 1/8" to 4", 1/4" to 12".
    """
    fr = set()
    for step, top in ((64, 0.5), (32, 1.0), (16, 2.0), (8, 4.0), (4, 12.0)):
        k = 1
        while k / step <= top + 1e-12:
            fr.add(round(k / step, 9))
            k += 1
    return np.array(sorted(f * INCH for f in fr))


HOLE_TABLES = {"metric": _metric_table(), "inch": _inch_table()}


def nearest_size(diameter: float, table: str) -> float:
    """Closest standard diameter in the named table (mm)."""
    t = HOLE_TABLES[table]
    return float(t[np.argmin(np.abs(t - diameter))])


def snap_hole(diameter: float, table: str, tol: float) -> float | None:
    """Standard diameter if the radius moves by <= tol, else None.

    Only the hole's own size changes. The table is chosen by the unit
    setting; nothing else is scaled.
    """
    d = nearest_size(diameter, table)
    return d if abs(d - diameter) / 2.0 <= tol + 1e-12 else None


def guess_units(diameters: list[float]) -> tuple[str, dict]:
    """Guess metric or inch from how close the holes sit to each table.

    Only a guess, written to the report; the user makes the final pick
    (plan part 3). Ties go to metric.
    """
    if not diameters:
        return "metric", {"reason": "no holes found; metric by default"}
    err = {u: float(np.median([abs(nearest_size(d, u) - d) for d in diameters]))
           for u in HOLE_TABLES}
    guess = "inch" if err["inch"] < err["metric"] else "metric"
    return guess, {"median_error_mm": err, "n_holes": len(diameters),
                   "reason": "smaller median distance to a standard size"}


# == size check ===============================================================

def check_size(model_extents, scan_extents, tol: float) -> dict:
    """Compare overall sizes per axis. Raises SizeCheckError when off.

    Passes when every axis is within tol of the scan. A ratio near 25.4 or
    1/25.4 is called out as a unit mix-up (mm vs inch), the failure the plan
    singles out.
    """
    m = np.asarray(model_extents, dtype=float)
    s = np.asarray(scan_extents, dtype=float)
    diff = m - s
    ratio = np.divide(m, s, out=np.full(3, np.nan), where=s > 0)
    out = {
        "model_extents_mm": [round(float(v), 4) for v in m],
        "scan_extents_mm": [round(float(v), 4) for v in s],
        "diff_mm": [round(float(v), 4) for v in diff],
        "ratio": [round(float(v), 6) for v in ratio],
        "tolerance_mm": tol,
    }
    unit_err = [bool(np.isfinite(r) and (abs(r / INCH - 1) <= UNIT_RATIO_SLACK
                                         or abs(r * INCH - 1) <= UNIT_RATIO_SLACK))
                for r in ratio]
    if any(unit_err):
        out["status"] = "STOPPED"
        out["message"] = (
            "overall size is about 25.4x off the scan (mm/inch mix-up); "
            f"ratios {out['ratio']}. Run stopped - the scan is never rescaled.")
        raise SizeCheckError(json.dumps(out))
    if np.any(np.abs(diff) > tol + 1e-9):
        k = int(np.argmax(np.abs(diff)))
        out["status"] = "STOPPED"
        out["message"] = (f"overall size off the scan by {diff[k]:+.4f} mm on "
                          f"{'XYZ'[k]} (tolerance {tol} mm). Run stopped.")
        raise SizeCheckError(json.dumps(out))
    out["status"] = "PASS"
    return out


def slab_extents(scan_pts: np.ndarray, model_pts: np.ndarray, band: float,
                 min_points: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Overall size of model and scan, measured the averaged way.

    For each axis and each end, the slab is every vertex the model places
    within `band` of its outermost position. The extent is the distance
    between the two slabs' median positions - once where the model puts the
    vertices, once where the averaged scan has them. Same vertices, so it
    compares size, not noise or sampling (plan part 1: against the averaged
    surface).

    Two biases this avoids, both seen on a perfect synthetic part: choosing
    the slab by SCAN position picks the vertices whose noise points outward
    (scan looks too big), and averaging includes the rounded rim where a
    flat end face meets its sides (scan looks too small). The median over
    the whole end face is immune to both.
    """
    se, me = np.zeros(3), np.zeros(3)
    for a in range(3):
        mc = model_pts[:, a]
        order = np.argsort(mc, kind="stable")
        ends = []
        for idx_end, sign in ((order[:min_points], 1), (order[-min_points:], -1)):
            edge = mc[idx_end[0]] if sign > 0 else mc[idx_end[-1]]
            sel = np.abs(mc - edge) <= band
            if sel.sum() < min_points:
                sel = np.zeros(len(mc), bool)
                sel[idx_end] = True
            ends.append((np.median(model_pts[sel, a]), np.median(scan_pts[sel, a])))
        (m_lo, s_lo), (m_hi, s_hi) = ends
        me[a], se[a] = m_hi - m_lo, s_hi - s_lo
    return me, se


# == small geometry helpers ===================================================

def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def _perp_basis(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    helper = np.eye(3)[int(np.argmin(np.abs(a)))]
    u = _unit(np.cross(a, helper))
    return u, np.cross(a, u)


def _stats(res: np.ndarray) -> dict:
    r = np.abs(np.asarray(res, dtype=float))
    return {"rms_mm": round(float(np.sqrt(np.mean(r ** 2))), 5),
            "mean_abs_mm": round(float(r.mean()), 5),
            "p95_mm": round(float(np.percentile(r, 95)), 5),
            "max_mm": round(float(r.max()), 5),
            "n_points": int(len(r))}


def plane_residual(pts, n, d) -> np.ndarray:
    return pts @ n - d


def cyl_residual(pts, a, p, r) -> np.ndarray:
    rel = pts - p
    perp = rel - np.outer(rel @ a, a)
    return np.linalg.norm(perp, axis=1) - r


def _axis_foot(a: np.ndarray, p: np.ndarray, near: np.ndarray) -> np.ndarray:
    """Point on the axis line closest to `near` (keeps points readable)."""
    return p + float((near - p) @ a) * a


def fit_circle_fixed_axis(pts, a, p0) -> tuple[np.ndarray, float]:
    """Least-squares axis position and radius with the axis direction fixed."""
    u, v = _perp_basis(a)
    rel = pts - p0
    xy = np.column_stack([rel @ u, rel @ v])
    x, y = xy[:, 0], xy[:, 1]
    A = np.column_stack([x, y, np.ones(len(x))])
    sol, *_ = np.linalg.lstsq(A, x ** 2 + y ** 2, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r0 = float(np.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 1e-12)))

    def res(q):
        return np.hypot(x - q[0], y - q[1]) - q[2]
    q = least_squares(res, [cx, cy, r0]).x
    return p0 + q[0] * u + q[1] * v, float(abs(q[2]))


def fit_cylinder(pts, axis0, point0, radius0) -> tuple[np.ndarray, np.ndarray, float]:
    """Full least-squares cylinder: axis direction, axis position and radius.

    Starts from the detected cylinder. On short arcs the free fit can wander
    (a 20-degree sliver barely constrains the axis); when the axis turns by
    more than 10 degrees or the radius changes by more than 20% the
    fixed-axis fit is kept instead, and the report says which was used.
    """
    a0 = _unit(axis0)
    c = pts.mean(axis=0)
    p0 = _axis_foot(a0, np.asarray(point0, float), c)
    u, v = _perp_basis(a0)

    def unpack(x):
        a = _unit(a0 + x[0] * u + x[1] * v)
        return a, p0 + x[2] * u + x[3] * v, x[4]

    def res(x):
        a, p, r = unpack(x)
        return cyl_residual(pts, a, p, r)

    try:
        sol = least_squares(res, [0, 0, 0, 0, radius0])
        a, p, r = unpack(sol.x)
        turned = np.degrees(np.arccos(min(1.0, abs(float(a @ a0)))))
        if sol.success and turned <= 10 and abs(r - radius0) <= 0.2 * radius0:
            return a, _axis_foot(a, p, c), float(abs(r))
    except Exception:
        pass
    p, r = fit_circle_fixed_axis(pts, a0, p0)
    return a0, _axis_foot(a0, p, c), r


# == area map =================================================================

def arc_coverage(C, W, mask, axis, point) -> float:
    """Share of the turn (in ROUND_BINS sectors) that masked faces occupy."""
    if not np.any(mask):
        return 0.0
    a = _unit(axis)
    u, v = _perp_basis(a)
    rel = C[mask] - np.asarray(point, float)
    ang = np.arctan2(rel @ v, rel @ u)
    h = np.histogram(ang, bins=ROUND_BINS, range=(-np.pi, np.pi), weights=W[mask])[0]
    return float(np.count_nonzero(h > 0)) / ROUND_BINS


def round_evidence(C, N, W, axis, point, radius, *, band: float,
                   mask: np.ndarray | None = None) -> dict:
    """How convincingly the faces describe a cylinder (round check).

    Faces count when their centre lies within `band` of the cylinder and
    their normal points along its radius (within ROUND_FACING_DEG, all on
    one side - outward for a boss, inward for a hole, whichever has more
    area). Returns the share of the turn they cover and their area-weighted
    rms distance from the cylinder. `mask` limits the faces looked at.
    """
    a = _unit(axis)
    p = np.asarray(point, float)
    rel = C - p
    perp = rel - np.outer(rel @ a, a)
    rad = np.linalg.norm(perp, axis=1)
    uhat = perp / np.maximum(rad, 1e-12)[:, None]
    d = rad - float(radius)
    f = np.einsum("ij,ij->i", N, uhat)
    cos_f = np.cos(np.radians(ROUND_FACING_DEG))
    near = np.abs(d) <= band
    if mask is not None:
        near &= mask
    out, inn = near & (f >= cos_f), near & (f <= -cos_f)
    side = out if W[out].sum() >= W[inn].sum() else inn
    if not side.any():
        return {"coverage": 0.0, "rms_mm": None, "area_mm2": 0.0, "side": "none"}
    rms = float(np.sqrt(np.average(d[side] ** 2, weights=W[side])))
    return {"coverage": round(arc_coverage(C, W, side, a, p), 4),
            "rms_mm": round(rms, 5), "area_mm2": round(float(W[side].sum()), 2),
            "side": "outward" if side is out else "inward"}


def round_check(ev: dict, nf: float) -> str | None:
    """None when the evidence is a convincing round, else the reason not."""
    why = []
    if ev["coverage"] < ROUND_MIN_COVERAGE:
        why.append(f"covers {ev['coverage'] * 100:.0f}% of the turn "
                   f"(needs {ROUND_MIN_COVERAGE * 100:.0f}%)")
    if ev["rms_mm"] is None:
        why.append("no face on it faces along its radius")
    elif ev["rms_mm"] > ROUND_MAX_RMS_NOISE * nf:
        why.append(f"fit rms {ev['rms_mm']:.3f} mm is over "
                   f"{ROUND_MAX_RMS_NOISE:g} x noise ({ROUND_MAX_RMS_NOISE * nf:.3f} mm)")
    return "; ".join(why) or None


def _detect(mesh: trimesh.Trimesh) -> tuple[list[Plane], list[Cylinder], float,
                                            list[bool], list[dict], dict]:
    """Planes, cylinders, noise floor, which cylinders came from the hole
    finder, the circle-search candidates the round check turned away, and
    how the noise was measured."""
    planes = extract_planes(mesh, thresh=PLANE_RANSAC_MM)
    # Noise is measured on the real flat faces (robust, trimmed sigma), not
    # as the rms of the plane-finder's 0.4 mm capture band: that band holds
    # chords across curves and the neighbours' edges, and on the pedal
    # adapter it read 0.179 mm against faces that fit to 0.06-0.09 mm rms.
    # Everything below scales with it: the join distance, the round check,
    # the flat check and the default tolerance.
    nf, noise_info = surface_noise(mesh, planes, band=PLANE_RANSAC_MM)
    # The hole finder and the circle search gate each candidate on the rms of
    # the faces inside the same 0.4 mm capture band, so that gate is compared
    # with the capture-band scale it is measured on (as before), not with
    # the face noise: 3 x 0.092 dropped two real holes (d5.1, d5.8) of the
    # pedal adapter whose capture-band rms is well inside 3 x 0.179.
    nf_capture = noise_floor(planes)
    # RANSAC also "finds" planes that are chords across a curved surface
    # (bores, fillets). Their points fill the whole inlier band, so their rms
    # is about band/sqrt(3) = 0.23 mm; a real face sits near the noise. The
    # cut is deliberately loose: 3x noise dropped the real boss bottom of the
    # stepped test part on one Poisson run (rms 0.07 at 0.02 mm noise).
    planes = [p for p in planes if p.rms <= plane_max_rms(nf)]
    axes: list[np.ndarray] = []
    for p in sorted(planes, key=lambda p: -p.area):
        n = np.asarray(p.normal, float)
        if all(abs(float(n @ a)) < 0.995 for a in axes):
            axes.append(n)
        if len(axes) == 3:
            break
    for e in np.eye(3):
        if all(abs(float(e @ a)) < 0.995 for a in axes):
            axes.append(e)
    # Holes come from their own finder (normal-directed voting): the
    # cylinder RANSAC below almost never draws three points from one small
    # hole on a busy part. Faces already on a flat face are left out of the
    # vote. Holes go first so a duplicate found by both keeps the hole fit.
    C = np.asarray(mesh.triangles_center, float)
    N = face_normals_smoothed(mesh)
    on_flat = np.zeros(len(C), dtype=bool)
    cos_f = np.cos(np.radians(LABEL_ANGLE_DEG))
    for p in planes:
        n = np.asarray(p.normal, float)
        on_flat |= (np.abs(C @ n - p.offset) <= PLANE_RANSAC_MM) & (N @ n >= cos_f)
    holes = extract_holes(mesh, axes, normals=N, exclude=on_flat,
                          thresh=PLANE_RANSAC_MM, r_min=HOLE_MIN_D_MM / 2,
                          max_rms=3 * nf_capture)
    # The circle search's own candidates must pass the round check
    # (ROUND_*); the hole finder has already applied the same test to holes.
    W = np.asarray(mesh.area_faces, float)
    others, rejected = [], []
    for c in extract_cylinders(mesh, axes, max_rms=3 * nf_capture):
        ev = round_evidence(C, N, W, c.axis, c.point, c.radius, band=PLANE_RANSAC_MM)
        why = round_check(ev, nf)
        if why is None:
            others.append(c)
        else:
            rejected.append({"stage": "candidate", "diameter_mm": round(2 * c.radius, 3),
                             "axis": [round(float(x), 4) for x in _unit(c.axis)],
                             **ev, "why": why})
    cyls = dedupe_cylinders(holes + others)
    hole_ids = {id(c) for c in holes}
    from_holes = [id(c) in hole_ids for c in cyls]
    return planes, cyls, nf, from_holes, rejected, noise_info


def face_normals_smoothed(mesh) -> np.ndarray:
    """Face normals averaged over the face's three vertex normals.

    A sliver triangle's own normal is at the mercy of a few hundredths of a
    millimetre of noise; the vertex normals average over the neighbourhood.
    """
    vn = np.asarray(mesh.vertex_normals, float)[np.asarray(mesh.faces)].sum(axis=1)
    fn = np.asarray(mesh.face_normals, float)
    ln = np.linalg.norm(vn, axis=1)
    out = fn.copy()
    good = ln > 1e-9
    out[good] = vn[good] / ln[good, None]
    return out


def label_faces(mesh, planes, cyls, *, label_dist: float,
                angle_deg: float = LABEL_ANGLE_DEG,
                min_patch: float,
                own_dist: dict[int, float] | None = None) -> tuple[np.ndarray, dict]:
    """Give every face a primitive index (planes first, then cylinders) or -1.

    A face belongs to a surface when its centre lies within label_dist of it
    (or own_dist[i] for primitive i, when given) and its normal agrees with
    the surface normal there. Where two surfaces both qualify (along an edge)
    the nearer one wins. Connected patches below min_patch mm2 are returned
    to "other".
    """
    own_dist = own_dist or {}
    C = np.asarray(mesh.triangles_center, float)
    N = face_normals_smoothed(mesh)
    cos_t, sin_t = np.cos(np.radians(angle_deg)), np.sin(np.radians(angle_deg))
    best = np.full(len(C), np.inf)
    lab = np.full(len(C), -1, dtype=np.int64)

    prims = [("plane", p) for p in planes] + [("cyl", c) for c in cyls]
    for i, (kind, g) in enumerate(prims):
        reach = own_dist.get(i, label_dist)
        if kind == "plane":
            n = np.asarray(g.normal, float)
            d = np.abs(C @ n - g.offset)
            ok = (d <= reach) & (N @ n >= cos_t)
        else:
            a, p = _unit(g.axis), np.asarray(g.point, float)
            rel = C - p
            perp = rel - np.outer(rel @ a, a)
            rad = np.linalg.norm(perp, axis=1)
            d = np.abs(rad - g.radius)
            uhat = perp / np.maximum(rad, 1e-12)[:, None]
            ok = ((d <= reach) & (np.abs(N @ a) <= sin_t)
                  & (np.abs(np.einsum("ij,ij->i", N, uhat)) >= cos_t))
        take = ok & (d < best)
        best[take] = d[take]
        lab[take] = i

    # Split each label into connected patches and drop the small ones.
    adj = np.asarray(mesh.face_adjacency)
    same = adj[(lab[adj[:, 0]] >= 0) & (lab[adj[:, 0]] == lab[adj[:, 1]])]
    nfc = len(C)
    g = coo_matrix((np.ones(len(same)), (same[:, 0], same[:, 1])), shape=(nfc, nfc))
    ncomp, comp = connected_components(g, directed=False)
    area = np.asarray(mesh.area_faces, float)
    comp_area = np.bincount(comp, weights=area, minlength=ncomp)
    keep = (lab >= 0) & (comp_area[comp] >= min_patch)
    lab[~keep] = -1
    patches = {}
    for i in np.unique(lab[lab >= 0]):
        patches[int(i)] = int(len(np.unique(comp[lab == i])))
    return lab, patches


# == edge bands =================================================================

# A face joins an area when it lies within label_dist (3x noise, wider than
# the tolerance on purpose, so noisy faces are not lost). Along the area's
# border that also pulls in the start of whatever comes next: the rounded
# edge where two faces meet, the foot of a rib standing on a flat face. Those
# faces are a different surface, and they are what pushed area 0 (the base,
# 3252 mm2) just past tolerance. EDGE_BAND_* control how they are found.
EDGE_BAND_WIDTH_MM = 2.0         # only faces this close to the border can go
EDGE_BAND_MIN_FACES = 3          # a band is at least this many faces
EDGE_BAND_KEEP_FRAC = 0.5        # never trim an area below half its size
EDGE_BAND_PASSES = 1             # trim once, then refit (2 passes trimmed
                                 # ~0.7% more of the part for one more area)


def edge_bands(mesh, fmask: np.ndarray, res_face: np.ndarray, tol: float,
               adj: np.ndarray | None = None, pinhole_mm2: float = 4.0) -> np.ndarray:
    """Faces of an area that belong to a neighbouring surface, not to it.

    A face is suspect when its centre is more than tol off the fitted
    surface AND within EDGE_BAND_WIDTH_MM of the area's border (a rounded
    edge or a rib foot is a strip along the border; a big patch off the
    face in its middle is form error and must keep counting). Suspect
    faces are joined into connected groups; a group is an edge band - and
    is returned - only when ALL of these hold:

    * it touches the area's border (a face outside the area, or the open
      edge of the scan), because an edge or a rib foot always does. Gaps
      inside the area smaller than pinhole_mm2 - faces that missed the area
      only because their normal was noisy - are not border;
    * it has at least EDGE_BAND_MIN_FACES faces;
    * it sits off the surface coherently, on one side: the area-weighted
      mean of its signed distance is itself beyond tol.

    Scattered noise and bumps inside the face fail the first or last test
    and stay in the area, so they still count against the tolerance. This
    only stops the area from being blamed for the surface next to it.
    """
    out = np.zeros(len(fmask), dtype=bool)
    if adj is None:
        adj = np.asarray(mesh.face_adjacency)
    bad = fmask & (np.abs(res_face) > tol)
    if not bad.any():
        return out
    farea = np.asarray(mesh.area_faces, float)
    nfc = len(fmask)
    C = np.asarray(mesh.triangles_center, float)
    # border: in the area, next to a face outside it or to an open edge
    a0, a1 = adj[:, 0], adj[:, 1]
    outside = ~fmask
    oo = outside[a0] & outside[a1]
    go = coo_matrix((np.ones(int(oo.sum())), (a0[oo], a1[oo])), shape=(nfc, nfc))
    nco, comp_o = connected_components(go, directed=False)
    co_area = np.bincount(comp_o, weights=farea, minlength=nco)
    outside &= co_area[comp_o] >= pinhole_mm2        # pinholes count as inside
    border = np.zeros(nfc, dtype=bool)
    cross = (fmask[a0] & outside[a1]) | (outside[a0] & fmask[a1])
    border[a0[cross & fmask[a0]]] = True
    border[a1[cross & fmask[a1]]] = True
    n_nb = np.bincount(adj.ravel(), minlength=nfc)
    border |= fmask & (n_nb < 3)
    if not border.any():
        return out
    near, _ = cKDTree(C[border]).query(C[bad], distance_upper_bound=EDGE_BAND_WIDTH_MM)
    keep = np.isfinite(near)
    bad[np.flatnonzero(bad)[~keep]] = False
    if not bad.any():
        return out
    both = bad[a0] & bad[a1]
    g = coo_matrix((np.ones(int(both.sum())), (a0[both], a1[both])), shape=(nfc, nfc))
    _, comp = connected_components(g, directed=False)
    cb = comp[bad]
    _, inv, counts = np.unique(cb, return_inverse=True, return_counts=True)
    w = farea[bad]
    mean_res = np.bincount(inv, weights=w * res_face[bad]) / np.bincount(inv, weights=w)
    touches = np.bincount(inv, weights=border[bad].astype(float)) > 0
    band = touches & (counts >= EDGE_BAND_MIN_FACES) & (np.abs(mean_res) > tol)
    idx = np.flatnonzero(bad)
    out[idx[band[inv]]] = True
    return out


# == flat check =================================================================

# A face joins a flat area when it lies within label_dist of the plane (3x
# noise, or the tolerance if larger; 0.54 mm on the pedal adapter while the
# noise was read off the capture band) and faces
# within LABEL_ANGLE_DEG of it. A gently curved surface passes both tests
# over a strip several millimetres wide. Once the round check sent the fake
# bosses' faces back, those curves joined the nearest plane (pedal adapter
# areas 6 and 11 got worse), and a coarse curved patch became the worst
# "flat" of the part (area 17, p95 0.66 mm). The flat check is the round
# check's twin, for planes. Both tests average over the scan around each face
# (or over the whole area), which is what makes them "systematic": cast
# texture goes up and down and averages out; a curve does not.
#
# * per face: around each corner, the area's points within FLAT_SMOOTH_MM
#   (area-weighted) must sit on the plane - mean distance no more than the
#   off-plane limit (FLAT_OFF_NOISE_FACTOR x noise, at least the low end of
#   the tolerance range, never more than the tolerance) - and the faces around it must face the plane's way, mean
#   normal within FLAT_MAX_TILT_DEG. Corners, not face centres: the pass
#   rule measures at the vertices, and on a coarse patch big tilted
#   triangles have centres on the plane and corners well off it. Faces that
#   fail go back to "other", pieces left smaller than the minimum patch go
#   with them, and the plane is refitted; FLAT_PASSES times.
# * per area: the best second-order surface through what is left (a bowl,
#   saddle or trough) may bend away from its own best plane by no more than
#   the off-plane limit over 95% of the area. If it bends more, the area is
#   a curve, not a flat, and all of it goes to "other".
#
# Neither test touches the pass rule: what is left is still measured against
# the tolerance at the 95th percentile of its points, noise and all.
FLAT_SMOOTH_MM = 2.5
FLAT_OFF_NOISE_FACTOR = 2.0
FLAT_MAX_TILT_DEG = 15.0
FLAT_PASSES = 3


def flat_off_limit(nf: float, tol: float, floor: float = 0.0) -> float:
    """How far the averaged scan may sit off a flat before it is not on it.

    FLAT_OFF_NOISE_FACTOR x noise, never less than `floor` (the low end of
    the user's tolerance range for the part's size) and never more than the
    tolerance. The floor matters once noise is measured on the clean faces:
    on the averaged stepped test part it is 0.011 mm, a 0.022 mm limit, and
    the stage-10 rounding along every edge then cost the top face an 18%
    strip (a 0.03 mm limit still took 7%). The test compares a 2.5 mm local
    MEAN, which noise barely moves; what trips a limit that tight is form
    far finer than any tolerance in the range.
    """
    return min(max(FLAT_OFF_NOISE_FACTOR * nf, floor), tol)


def local_mean(X: np.ndarray, W: np.ndarray, vals: np.ndarray,
               radius: float) -> np.ndarray:
    """Weighted mean of `vals` over the points of X within `radius` of each.

    Each point counts itself, so a point with no neighbour in reach keeps
    its own value. `vals` may be one value or one vector per point.
    """
    n = len(X)
    if n == 0:
        return np.zeros((0,) + np.shape(vals)[1:])
    pairs = cKDTree(X).query_pairs(radius, output_type="ndarray")
    rows = np.concatenate([pairs[:, 0], pairs[:, 1], np.arange(n)])
    cols = np.concatenate([pairs[:, 1], pairs[:, 0], np.arange(n)])
    A = coo_matrix((W[cols], (rows, cols)), shape=(n, n)).tocsr()
    den = np.asarray(A.sum(axis=1)).ravel()
    num = A @ np.asarray(vals)
    return num / (den[:, None] if num.ndim == 2 else den)


def _area_vertices(faces: np.ndarray, farea: np.ndarray, mask: np.ndarray):
    """Vertices of the masked faces, each weighted by a third of its faces'
    area, and every masked face as indices into that vertex list."""
    fv = faces[mask]
    vidx, inv = np.unique(fv.ravel(), return_inverse=True)
    w = np.bincount(inv, weights=np.repeat(farea[mask] / 3.0, 3), minlength=len(vidx))
    return vidx, w, inv.reshape(-1, 3)


def flat_off_faces(verts, faces, C, N, W, mask, n, d, *, limit: float,
                   radius: float = FLAT_SMOOTH_MM,
                   tilt_deg: float = FLAT_MAX_TILT_DEG) -> np.ndarray:
    """Faces of a flat area whose surroundings are not on its plane.

    Distance is taken at the area's VERTICES - the same points the pass rule
    measures - so a coarse patch of big tilted triangles cannot hide behind
    face centres that happen to sit on the plane. Each vertex gets the
    area-weighted mean signed distance of the area's vertices within
    `radius`; a face goes when any of its corners is beyond `limit` on that
    average, or when the mean normal of the area's faces within `radius`
    leans more than `tilt_deg` off the plane. Single noisy points cannot trip
    either test; a curve, a step or a rib foot can.
    """
    out = np.zeros(len(mask), dtype=bool)
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return out
    n = _unit(n)
    vidx, wv, fv = _area_vertices(faces, W, mask)
    P = verts[vidx]
    sres = local_mean(P, wv, P @ n - d, radius)
    far = (np.abs(sres) > limit)[fv].any(axis=1)
    snrm = local_mean(C[idx], W[idx], N[idx], radius)
    ln = np.linalg.norm(snrm, axis=1)
    cos_tilt = (snrm @ n) / np.maximum(ln, 1e-12)
    out[idx[far | (cos_tilt < np.cos(np.radians(tilt_deg)))]] = True
    return out


def small_pieces(adj: np.ndarray, mask: np.ndarray, W: np.ndarray,
                 min_area: float) -> np.ndarray:
    """Faces of `mask` in connected pieces smaller than `min_area` mm2."""
    nfc = len(mask)
    both = mask[adj[:, 0]] & mask[adj[:, 1]]
    e = adj[both]
    g = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nfc, nfc))
    ncomp, comp = connected_components(g, directed=False)
    carea = np.bincount(comp[mask], weights=W[mask], minlength=ncomp)
    return mask & (carea[comp] < min_area)


def _wpercentile(x: np.ndarray, w: np.ndarray, q: float) -> float:
    o = np.argsort(x)
    cw = np.cumsum(w[o])
    return float(x[o][min(int(np.searchsorted(cw, q / 100.0 * cw[-1])), len(x) - 1)])


def flat_bend(verts, faces, W, mask, n) -> dict:
    """How far the area's best second-order surface bends off a plane.

    Fits height over the plane as a full quadratic (6 terms) through the
    area's vertices, each weighted by its share of face area, removes the
    quadratic's own best-fit plane, and returns the 95th percentile (by area)
    of what is left: the bend. Noise cannot make a bend over dozens of
    points; a bowl, saddle or trough does. Also returns the principal
    curvature radii of the quadratic, for the report.
    """
    n = _unit(n)
    u, v = _perp_basis(n)
    vidx, w, _ = _area_vertices(faces, W, mask)
    c = verts[vidx]
    if len(c) < 12:
        return {"bend_p95_mm": 0.0, "radii_mm": None, "n_points": int(len(c))}
    x = c @ u - np.average(c @ u, weights=w)
    y = c @ v - np.average(c @ v, weights=w)
    h = c @ n
    A = np.column_stack([x * x, x * y, y * y, x, y, np.ones_like(x)])
    sw = np.sqrt(w)
    sol, *_ = np.linalg.lstsq(A * sw[:, None], h * sw, rcond=None)
    q = A[:, :3] @ sol[:3]
    lin, *_ = np.linalg.lstsq(A[:, 3:] * sw[:, None], q * sw, rcond=None)
    bend = np.abs(q - A[:, 3:] @ lin)
    k = np.linalg.eigvalsh(np.array([[2 * sol[0], sol[1]], [sol[1], 2 * sol[2]]]))
    radii = [round(float(1.0 / abs(kk)), 1) if abs(kk) > 1e-9 else None for kk in k]
    return {"bend_p95_mm": round(_wpercentile(bend, w, 95), 5), "radii_mm": radii,
            "n_points": int(len(c))}


# == pass check: judge the smooth shape, not the scan's texture ===============

# The pass rule is unchanged: an area is within tolerance when 95% of its
# points lie within the tolerance of its fitted surface. What changed is
# WHICH distance is compared. The averaged scan still carries cast texture
# about a millimetre across; on the pedal adapter ten flats had rms
# 0.10-0.12 mm (the shape is right) and still missed 0.184 mm at the 95th
# percentile, on texture peaks alone. the user's models are smooth solids that
# never carry the texture, so the test should not fail a face on it either.
#
# * Each area's distances are averaged (area-weighted) over its OWN points
#   within PASS_SMOOTH_MM - never across into the next area, so an edge, a
#   step or a hole wall is not blurred into its neighbour.
# * On a hole or boss the reach runs ALONG the axis only: around the turn it
#   is ROUND_ARC_SQUEEZE times shorter (a quarter of a millimetre, less than
#   the point spacing). Out-of-round shape - a D flat, an oval - is the same
#   all along the axis, so axial averaging leaves it whole; a 1 mm reach
#   around a d4 turn would span 60 degrees and shave a D's error by a third.
# * Smoothing may take off at most the texture limit at any point
#   (TEXTURE_NOISE_FACTOR x noise: the same 3x the area map uses to call a
#   face "on" a surface). A point that stands further than that off its
#   smoothed surroundings is not texture - a ridge, a dent, a burr - and
#   keeps its raw distance. (2x noise would put the limit at the tolerance
#   itself, and plain texture of the measured noise crosses 2 sigma on ~5%
#   of points - the whole 95% budget - so the limit would decide the test.)
# * Anything wider than the smoothing reach is shape and passes through
#   untouched: a bowed face, a D-shaped hole, a step all still fail.
#
# Only this comparison sees the smoothed copy. The fits, the snaps, the size
# check and the model points never do: the model is the fitted planes and
# cylinders, and no texture goes into it. The raw statistics stay in the
# report ("final") next to the judged ones ("judged").
PASS_SMOOTH_MM = 1.0
ROUND_ARC_SQUEEZE = 4.0
TEXTURE_NOISE_FACTOR = 3.0


def texture_limit(nf: float) -> float:
    """Most that smoothing may take off one point before it counts as real."""
    return TEXTURE_NOISE_FACTOR * nf


def pass_coords(P: np.ndarray, axis=None, point=None) -> np.ndarray:
    """Coordinates the pass-check smoothing measures reach in.

    A flat: the points as they are. A round (axis and point given): distance
    along the axis kept, distance around the turn stretched ROUND_ARC_SQUEEZE
    times, so a ball of PASS_SMOOTH_MM reaches that far along the wall and
    only a quarter of it around. Radial position is dropped (every point
    goes on the median circle), so texture never moves a point out of reach.
    """
    P = np.asarray(P, float)
    if axis is None:
        return P
    a = _unit(axis)
    rel = P - np.asarray(point, float)
    along = rel @ a
    perp = rel - np.outer(along, a)
    # Around the turn only: every point is put on one circle first, so the
    # point's own distance from the axis (texture, a D flat) never decides
    # what is in reach - only where it sits along and around the wall.
    rad = np.linalg.norm(perp, axis=1)
    ring = float(np.median(rad)) if len(rad) else 0.0
    perp = perp / np.maximum(rad, 1e-12)[:, None] * ring
    return np.column_stack([along, ROUND_ARC_SQUEEZE * perp])


def judged_residual(P: np.ndarray, w: np.ndarray, res: np.ndarray, *,
                    radius: float, cap: float) -> tuple[np.ndarray, np.ndarray]:
    """Signed distances the pass rule compares, and which points kept raw.

    `P` are one area's points, `w` their area weights, `res` their signed
    distance from the area's fitted surface. Each distance is replaced by the
    weighted mean over the area's points within `radius`, unless that would
    move it by more than `cap` - then the point is a real feature, not
    texture, and its raw distance stands.
    """
    res = np.asarray(res, dtype=float)
    if len(res) == 0:
        return res.copy(), np.zeros(0, dtype=bool)
    sm = local_mean(np.asarray(P, float), np.asarray(w, float), res, radius)
    keep_raw = np.abs(res - sm) > cap
    return np.where(keep_raw, res, sm), keep_raw


def pass_check(P, w, res, *, tol: float, cap: float, radius: float = PASS_SMOOTH_MM,
               axis=None, point=None) -> dict:
    """The 95% rule on the judged (texture-smoothed) distances of one area.

    Give `axis` and `point` for a hole or boss (smoothing along the axis).
    """
    j, keep_raw = judged_residual(pass_coords(P, axis, point), w, res,
                                  radius=radius, cap=cap)
    st = _stats(j)
    st.update(smooth_radius_mm=round(float(radius), 4),
              texture_limit_mm=round(float(cap), 5),
              along_axis_only=axis is not None,
              raw_kept_frac=round(float(keep_raw.mean()) if len(keep_raw) else 0.0, 4),
              within_tol=bool(st["p95_mm"] <= tol))
    return {"stats": st, "residual": j}


# == freeform splines (plan part 4, first measuring step) ===================
# Connected "other" faces - what flat and round fitting left behind - are
# grouped into patches. Each patch gets one smooth spline, scored with the
# same smoothed 95% check as every other area. Measuring only: nothing here
# is trimmed or knitted, and these patches are not moved into the size-check
# model (a stiff patch can sit millimetres off a cast curve; pulling the
# model there would fake a size error).
#
# Stiffness is the plan's user setting (a slider or a range). The number
# below is PROPOSED, not a decision the user has made. It sits at the stiff
# end on purpose. The solid should look like a machined part: straight
# flats, true rounds, and, where a face is genuinely curved, one fair simple
# surface. The scan is never perfect. A looser spline would bend to follow
# texture and small waviness, more patches would pass, and the scan would
# end up in the model. That trade is refused. A patch that misses the
# tolerance keeps this stiff surface and is reported outside tolerance.
# Nothing retries a failed patch at a lower stiffness.
#
# stiffness 1 -> degree 2 (3 by 3 = 9 control points), a quadratic fairing.
# stiffness 0 -> degree 6 (7 by 7 = 49). Proposed default: 1.
# The control points cover the whole patch, so millimetre texture cannot be
# followed; the stiff end also refuses longer waviness.
SPLINE_STIFFNESS_PROPOSED = 1.0
SPLINE_DEGREE_STIFF = 2
SPLINE_DEGREE_LOOSE = 6

# One spline is a height field over one plane. A connected "other" region on
# a real part wraps the whole way around, so it is cut into charts whose
# smoothed normals stay within CHART_NORMAL_DEG of the seed face. That cut
# is what lets one quadratic describe the chart. It is not tightened when a
# chart misses the tolerance, and it is not a way to chase the scan. An edge
# whose faces differ by more than CHART_CREASE_DEG is not crossed, so a
# sharp crease is never bridged by one patch.
CHART_NORMAL_DEG = 30.0
CHART_CREASE_DEG = 35.0


def spline_degree(stiffness: float) -> int:
    """Polynomial degree for a stiffness in 0 (loosest) to 1 (stiffest)."""
    s = float(np.clip(stiffness, 0.0, 1.0))
    return int(round(SPLINE_DEGREE_LOOSE + s * (SPLINE_DEGREE_STIFF - SPLINE_DEGREE_LOOSE)))


def _chart_frame(pts, w, normal_hint):
    """Orthonormal frame: n is the patch's best-fit plane, u and v span it."""
    w = np.maximum(np.asarray(w, float), 0.0)
    if float(w.sum()) <= 0:
        w = np.ones(len(pts))
    origin = np.average(pts, axis=0, weights=w)
    X = np.asarray(pts, float) - origin
    sw = np.sqrt(w)[:, None]
    cov = (X * sw).T @ (X * sw) / float(w.sum())
    _, evecs = np.linalg.eigh(cov)
    n = _unit(evecs[:, 0])
    u = evecs[:, 2]
    u = _unit(u - n * float(u @ n))
    if normal_hint is not None and float(n @ np.asarray(normal_hint, float)) < 0:
        n = -n
    v = _unit(np.cross(n, u))
    return origin, n, u, v


def _cheb_design(xn, yn, deg: int) -> np.ndarray:
    Tx = np.polynomial.chebyshev.chebvander(xn, deg)
    Ty = np.polynomial.chebyshev.chebvander(yn, deg)
    return np.column_stack([Tx[:, i] * Ty[:, j]
                            for i in range(deg + 1) for j in range(deg + 1)])


def spline_distance(pts, frame) -> np.ndarray:
    """Signed distance from points to a fitted height-field spline.

    Positive means the point sits on the side of the patch normal. The
    distance is the true one, not the raw height, so a tilted chart is not
    punished for slope.
    """
    X = np.asarray(pts, float) - frame["origin"]
    x, y, h = X @ frame["u"], X @ frame["v"], X @ frame["n"]
    deg = int(frame["degree"])
    xn = 2.0 * (x - frame["x0"]) / frame["xs"] - 1.0
    yn = 2.0 * (y - frame["y0"]) / frame["ys"] - 1.0
    coef = frame["coef"]
    s = _cheb_design(xn, yn, deg) @ coef
    eps = 1e-4
    sx = ((_cheb_design(xn + eps, yn, deg) - _cheb_design(xn - eps, yn, deg)) @ coef
          / (2.0 * eps) * (2.0 / frame["xs"]))
    sy = ((_cheb_design(xn, yn + eps, deg) - _cheb_design(xn, yn - eps, deg)) @ coef
          / (2.0 * eps) * (2.0 / frame["ys"]))
    return (h - s) / np.sqrt(1.0 + sx * sx + sy * sy)


def fit_spline_patch(pts, weights=None, *, stiffness=SPLINE_STIFFNESS_PROPOSED,
                     normal_hint=None, tol: float, cap: float,
                     smooth_mm: float = PASS_SMOOTH_MM) -> dict | None:
    """Fit one stiff spline to a patch and score it with the smoothed 95% check.

    Returns None when the points are too few or too flat in one direction to
    be a surface. The stiffness passed in is the stiffness used: a miss does
    not loosen it.
    """
    pts = np.asarray(pts, float)
    w = np.ones(len(pts)) if weights is None else np.asarray(weights, float)
    deg = spline_degree(stiffness)
    ncoef = (deg + 1) ** 2
    if len(pts) < ncoef + 6:
        return None
    origin, n, u, v = _chart_frame(pts, w, normal_hint)
    X = pts - origin
    x, y, h = X @ u, X @ v, X @ n
    xs = float(x.max() - x.min())
    ys = float(y.max() - y.min())
    if xs < 0.3 or ys < 0.3:
        return None
    x0, y0 = float(x.min()), float(y.min())
    xn = 2.0 * (x - x0) / xs - 1.0
    yn = 2.0 * (y - y0) / ys - 1.0
    A = _cheb_design(xn, yn, deg)
    sw = np.sqrt(np.maximum(w, 0.0))
    if float(sw.sum()) <= 0:
        sw = np.ones(len(pts))
    coef, *_ = np.linalg.lstsq(A * sw[:, None], h * sw, rcond=None)
    frame = {"origin": origin, "n": n, "u": u, "v": v,
             "x0": x0, "xs": xs, "y0": y0, "ys": ys,
             "degree": deg, "coef": coef}
    res = spline_distance(pts, frame)
    pc = pass_check(pts, w, res, tol=tol, cap=cap, radius=smooth_mm)
    final = _stats(res)
    return {"stiffness": float(stiffness), "degree": deg, "n_control": ncoef,
            "frame": frame, "residual": res, "final": final,
            "judged": pc["stats"], "judged_residual": pc["residual"],
            "within_tol": pc["stats"]["within_tol"],
            "within_tol_raw": bool(final["p95_mm"] <= tol)}


def freeform_charts(other, adj, normals, farea, min_patch):
    """Connected 'other' faces, cut into charts one quadratic can describe.

    Returns the charts (each an array of face indices) and the mm2 of other
    faces left in pieces smaller than the minimum patch.
    """
    n = len(other)
    neigh: list[list[int]] = [[] for _ in range(n)]
    if len(adj):
        both = other[adj[:, 0]] & other[adj[:, 1]]
        for a, b in np.asarray(adj[both], int):
            neigh[a].append(int(b))
            neigh[b].append(int(a))
    cos_n = float(np.cos(np.radians(CHART_NORMAL_DEG)))
    cos_c = float(np.cos(np.radians(CHART_CREASE_DEG)))
    assigned = np.zeros(n, dtype=bool)
    order = np.flatnonzero(other)
    if len(order) == 0:
        return [], 0.0
    order = order[np.argsort(-farea[order], kind="stable")]
    charts = []
    leftover = 0.0
    for seed in order:
        seed = int(seed)
        if assigned[seed]:
            continue
        n0 = normals[seed]
        assigned[seed] = True
        stack = [seed]
        members: list[int] = []
        while stack:
            f = stack.pop()
            members.append(f)
            nf = normals[f]
            for nb in neigh[f]:
                if assigned[nb]:
                    continue
                if float(normals[nb] @ n0) < cos_n:
                    continue
                if float(normals[nb] @ nf) < cos_c:
                    continue
                assigned[nb] = True
                stack.append(nb)
        memb = np.asarray(members, dtype=np.int64)
        area = float(farea[memb].sum())
        if area >= min_patch and len(memb) >= 6:
            charts.append(memb)
        else:
            leftover += area
    return charts, leftover


def _round_vec(v) -> list[float]:
    return [round(float(x), 6) for x in np.asarray(v, float)]


def _free_area(aid, fmask, farea, fitted, pts, vidx, **extra) -> dict:
    frame = fitted["frame"]
    return {
        "id": aid, "type": "freeform", "kind": "spline",
        "n_faces": int(fmask.sum()),
        "area_mm2": round(float(farea[fmask].sum()), 2),
        "n_patches": 1, "snaps": [],
        "stiffness": fitted["stiffness"],
        "stiffness_status": "PROPOSED",
        "fit": {"degree": fitted["degree"], "n_control": fitted["n_control"],
                "stiffness": fitted["stiffness"],
                "normal": _round_vec(frame["n"]),
                "origin_mm": [round(float(x), 4) for x in frame["origin"]]},
        "final": fitted["final"], "judged": fitted["judged"],
        "within_tol": fitted["within_tol"],
        "within_tol_raw": fitted["within_tol_raw"],
        **extra,
        "_pts": pts, "_fmask": fmask, "_vidx": vidx,
        "_jres": fitted["judged_residual"], "_frame": frame,
    }


def assign_freeform(mesh, verts, faces, farea, normals, area_lab, areas, *,
                    nf: float, tol: float, min_patch: float,
                    stiffness: float = SPLINE_STIFFNESS_PROPOSED,
                    split: bool = True, label_dist: float | None = None,
                    flat_lim: float | None = None, directions=None,
                    table: str = "metric", seed: int = 0) -> dict:
    """Fit a stiff spline to every chart of 'other' and append it to `areas`.

    Faces that get a spline are labelled with the new area id. Faces left
    over stay -1 (still uncovered). Stiffness is the same for every patch.
    With `split`, a chart that misses is split into flats, rounds and
    smaller stiff patches (see SPLIT_*) instead.
    """
    adj = np.asarray(mesh.face_adjacency)
    C = np.asarray(mesh.triangles_center, float)
    cap = texture_limit(nf)
    if label_dist is None:
        label_dist = max(LABEL_NOISE_FACTOR * nf, tol)
    # The split keeps its own random stream (same seed as before), so what
    # it finds is not shifted by this first pass.
    rng = np.random.default_rng(seed)
    rng_pre = np.random.default_rng(seed + 1)
    # Fillets between the fitted flats, and partial rounds on the part's
    # axes, come before any spline: a true round is the simpler surface.
    partial_meta = None
    if split and PARTIAL_BEFORE_CHARTS:
        def accept(fm, a):
            area_lab[fm] = a["id"]
            areas.append(a)
        partial_meta = _partial_pass(verts, faces, C, normals, farea, adj, area_lab < 0,
                                     area_lab, areas, nf=nf, tol=tol, cap=cap,
                                     label_dist=label_dist, min_patch=min_patch,
                                     directions=list(directions or []), table=table,
                                     rng=rng_pre, accept=accept)
    other = area_lab < 0
    charts, leftover = freeform_charts(other, adj, normals, farea, min_patch)
    deg = spline_degree(stiffness)
    could_not = 0.0
    missed = []
    for members in charts:
        fmask, vidx, pts, fitted = _fit_chart(members, verts, faces, farea, normals,
                                              stiffness=stiffness, tol=tol, cap=cap)
        if fitted is None:
            could_not += float(farea[fmask].sum())
            continue
        if split and not fitted["within_tol"]:
            missed.append((members, fitted))
            continue
        aid = len(areas)
        area_lab[fmask] = aid
        areas.append(_free_area(aid, fmask, farea, fitted, pts, vidx))

    split_meta = None
    if split and missed:
        split_meta = _split_missed(
            missed, verts, faces, C, normals, farea, adj, area_lab, areas,
            nf=nf, tol=tol, cap=cap, min_patch=min_patch, stiffness=stiffness,
            label_dist=label_dist,
            flat_lim=flat_lim if flat_lim is not None else flat_off_limit(nf, tol),
            directions=list(directions or []), table=table, rng=rng)
        could_not += split_meta.pop("_could_not")

    total = float(farea.sum())
    covered = float(farea[area_lab >= 0].sum())
    free = [a for a in areas if a["type"] == "freeform"]
    free_area = float(sum(a["area_mm2"] for a in free))
    worst = None
    if free:
        w = max(free, key=lambda a: a["judged"]["p95_mm"])
        worst = {"area": w["id"], "area_mm2": w["area_mm2"],
                 "within_tol": w["within_tol"],
                 "judged_p95_mm": w["judged"]["p95_mm"],
                 "p95_mm": w["final"]["p95_mm"]}
    return {
        "plan": "part 4, first measuring step: one spline per curved patch; "
                "a patch that misses is split into flats, rounds and smaller "
                "stiff patches. No trimming, no knitting, no joints yet.",
        "stiffness": {
            "value": float(stiffness),
            "status": "PROPOSED",
            "degree": deg,
            "n_control": (deg + 1) ** 2,
            "scale": ("0 is loosest (degree %d, %d control points), "
                      "1 is stiffest (degree %d, %d control points)"
                      % (SPLINE_DEGREE_LOOSE, (SPLINE_DEGREE_LOOSE + 1) ** 2,
                         SPLINE_DEGREE_STIFF, (SPLINE_DEGREE_STIFF + 1) ** 2)),
            "note": "The plan says the user sets patch stiffness, as a slider "
                    "or a range. This default is a proposal, not a decision.",
        },
        "tradeoff": (
            "The proposed stiffness is the stiff end: one quadratic fairing, "
            "the simple curved surface a machined part would have. The scan is "
            "never perfect. A looser patch would bend to follow texture and "
            "small waviness and more of the surface would pass, and that was "
            "not done. A patch that misses is split into the flats, rounds and "
            "simpler curves it really holds; what still misses keeps the stiff "
            "surface and is reported outside tolerance. Stiffness is not "
            "lowered to chase a pass."
        ),
        "chart_normal_deg": CHART_NORMAL_DEG,
        "chart_crease_deg": CHART_CREASE_DEG,
        "chart_rule": (
            "Connected 'other' faces are cut into charts whose normals stay "
            "within %.0f degrees of the seed, so each chart is a height field "
            "one quadratic can describe. An edge sharper than %.0f degrees is "
            "not crossed, so a crease is not bridged."
            % (CHART_NORMAL_DEG, CHART_CREASE_DEG)),
        "n_patches": len(free),
        "n_within_tol": int(sum(a["within_tol"] for a in free)),
        "patch_area_mm2": round(free_area, 2),
        "patch_area_frac": round(free_area / total, 4) if total else 0.0,
        "covered_area_frac": round(covered / total, 4) if total else 0.0,
        "uncovered_area_frac": round(1.0 - covered / total, 4) if total else 0.0,
        "uncovered_mm2": round(float(farea[area_lab < 0].sum()), 2),
        "leftover_below_min_patch_mm2": round(leftover, 2),
        "could_not_fit_mm2": round(could_not, 2),
        "worst_patch": worst,
        "split": split_meta,
        "partial_rounds_before_charts": partial_meta,
        "in_size_check": False,
    }


def _partial_pass(verts, faces, C, N, W, adj, pool, area_lab, areas, *, nf, tol, cap,
                  label_dist, min_patch, directions, table, rng, accept) -> dict:
    """Fillets, then partial rounds, out of `pool` (in place)."""
    got = []

    def acc(fm, a):
        got.append({"area": a["id"], "kind": a["kind"],
                    "diameter_mm": a["final"]["diameter_mm"],
                    "area_mm2": a["area_mm2"]})
        accept(fm, a)
    flog = find_fillets(verts, faces, C, N, W, adj, pool, area_lab, areas, nf=nf, tol=tol,
                        label_dist=label_dist, cap=cap, table=table, accept=acc)
    plog = find_partial_rounds(verts, faces, C, N, W, adj, pool, area_lab, areas,
                               axes=round_axes(directions, areas), nf=nf, tol=tol,
                               label_dist=label_dist, min_patch=min_patch, cap=cap,
                               table=table, rng=rng, accept=acc)
    return {"accepted": got,
            "fillets_tried": flog,
            "partial_rounds_tried": plog}


def _split_missed(missed, verts, faces, C, N, W, adj, area_lab, areas, *, nf, tol,
                  cap, min_patch, stiffness, label_dist, flat_lim, directions,
                  table, rng) -> dict:
    """Split every missed stiff patch into flats, rounds and stiff sub-patches."""
    nfc = len(W)
    pool = np.zeros(nfc, dtype=bool)
    patch_of = np.full(nfc, -1, dtype=np.int64)
    before = []
    for k, (members, fitted) in enumerate(missed):
        pool[members] = True
        patch_of[members] = k
        before.append({"patch": k, "area_mm2": round(float(W[members].sum()), 2),
                       "judged_p95_mm": fitted["judged"]["p95_mm"],
                       "flat": [], "round": [], "fillet": [], "curve": [], "blend": []})
    pool0 = pool.copy()
    pidx = np.flatnonzero(pool)
    Ns = N.copy()
    sm = local_mean(C[pidx], W[pidx], N[pidx], SPLIT_NORMAL_SMOOTH_MM)
    Ns[pidx] = sm / np.maximum(np.linalg.norm(sm, axis=1), 1e-12)[:, None]

    outside = []

    def from_patch(fm):
        sel = patch_of[fm] >= 0
        if not sel.any():
            return None
        k = np.bincount(patch_of[fm][sel], weights=W[fm][sel])
        return int(np.argmax(k))

    def finish(a, fm, kind, k, depth=0):
        a["split"] = {"from_missed_patch": k, "piece": kind, "depth": depth,
                      "in_size_check": False}
        area_lab[fm] = a["id"]
        areas.append(a)
        if k is None:
            outside.append(a["id"])
        else:
            before[k][kind].append(a["id"])

    # 1. flats
    for f in split_flats(verts, faces, C, N, Ns, W, adj, pool, label_dist=label_dist,
                         flat_lim=flat_lim, min_patch=min_patch,
                         directions=directions, tol=tol, rng=rng):
        fm, n, d = f["fmask"], f["n"], f["d"]
        vidx, wv, _ = _area_vertices(faces, W, fm)
        pts = verts[vidx]
        res = plane_residual(pts, n, d)
        pc = pass_check(pts, wv, res, tol=tol, cap=cap)
        st = _stats(res)
        a = {"id": len(areas), "type": "flat", "kind": "plane",
             "n_faces": int(fm.sum()), "area_mm2": round(float(W[fm].sum()), 2),
             "n_patches": len(_pieces(adj, fm)), "snaps": f["snaps"],
             "fit": {"normal": [round(float(x), 6) for x in n],
                     "offset_mm": round(float(d), 4), **st},
             "flat_check": {k: f["bend"][k] for k in ("bend_p95_mm", "radii_mm", "edge_share")},
             "final": {"normal": [round(float(x), 9) for x in n],
                       "offset_mm": round(float(d), 4), **st},
             "judged": pc["stats"], "within_tol": pc["stats"]["within_tol"],
             "within_tol_raw": bool(st["p95_mm"] <= tol),
             "_n": n, "_d": float(d), "_pts": pts, "_fmask": fm, "_vidx": vidx,
             "_jres": pc["residual"]}
        finish(a, fm, "flat", from_patch(fm))

    # 2. rounds
    axes = []
    for g in list(directions) + list(np.eye(3)):
        g = _unit(g)
        if all(abs(float(g @ x)) < 0.995 for x in axes):
            axes.append(g)
    for r in split_rounds(verts, faces, C, N, W, adj, pool, axes=axes,
                          label_dist=label_dist, nf=nf, min_patch=min_patch, rng=rng):
        fm, ax, p, rad = r["fmask"], r["a"], r["p"], r["r"]
        rel = C[fm] - p
        perp = rel - np.outer(rel @ ax, ax)
        uh = perp / np.maximum(np.linalg.norm(perp, axis=1), 1e-12)[:, None]
        outward = float(np.average(np.einsum("ij,ij->i", N[fm], uh), weights=W[fm]))
        kind = "boss" if outward > 0 else "hole"
        vidx, wv, _ = _area_vertices(faces, W, fm)
        pts = verts[vidx]
        snaps = []
        std = {"table": table, "nearest_mm": round(nearest_size(2 * rad, table), 4)}
        if kind == "hole":
            d_std = snap_hole(2 * rad, table, tol)
            if d_std is not None:
                snaps.append(f"diameter {2 * rad:.4f} -> {d_std:g} mm ({table}), "
                             f"moved {abs(d_std - 2 * rad) / 2:.4f} mm")
                rad = d_std / 2
                std = {"table": table, "diameter_mm": d_std}
        res = cyl_residual(pts, ax, p, rad)
        pc = pass_check(pts, wv, res, tol=tol, cap=cap, axis=ax, point=p)
        st = _stats(res)
        along = pts @ ax
        a = {"id": len(areas), "type": "round", "kind": kind,
             "n_faces": int(fm.sum()), "area_mm2": round(float(W[fm].sum()), 2),
             "n_patches": 1, "snaps": snaps, "standard_size": std,
             "round_check": r["evidence"],
             "fit": {"axis": [round(float(x), 6) for x in ax],
                     "point_mm": [round(float(x), 4) for x in p],
                     "diameter_mm": round(2 * rad, 4),
                     "length_mm": round(float(along.max() - along.min()), 3), **st},
             "final": {"axis": [round(float(x), 9) for x in ax],
                       "point_mm": [round(float(x), 4) for x in p],
                       "diameter_mm": round(2 * rad, 4), **st},
             "judged": pc["stats"], "within_tol": pc["stats"]["within_tol"],
             "within_tol_raw": bool(st["p95_mm"] <= tol),
             "_a": ax, "_p": p, "_r": rad, "_pts": pts, "_fmask": fm, "_vidx": vidx,
             "_jres": pc["residual"]}
        finish(a, fm, "round", from_patch(fm))

    # 2b. fillets between fitted flats (now including the flats just found)
    # and partial rounds, on the missed faces and on whatever else is still
    # uncovered (the thin strips along the flats)
    pool_ext = pool | (area_lab < 0)

    def accept(fm, a):
        finish(a, fm, "fillet" if a["kind"] == "fillet" else "round", from_patch(fm))
    partial_meta = _partial_pass(verts, faces, C, N, W, adj, pool_ext, area_lab, areas,
                                 nf=nf, tol=tol, cap=cap, label_dist=label_dist,
                                 min_patch=min_patch, directions=directions, table=table,
                                 rng=rng, accept=accept)

    # 2c. short rings capped by flats at both ends (and their cap flats)
    def accept_ring(fm, a):
        finish(a, fm, "flat" if a["type"] == "flat" else "round", from_patch(fm))
    ring_meta = find_capped_rings(verts, faces, C, N, W, adj, pool_ext, area_lab, areas,
                                  axes=round_axes(directions, areas), nf=nf, tol=tol,
                                  label_dist=label_dist, flat_lim=flat_lim, cap=cap,
                                  table=table, rng=np.random.default_rng(7),
                                  accept=accept_ring)
    guides = ring_meta.pop("_guides")

    # 2d. stud posts: rings refused only for their caps that are short closed
    # posts standing on a floor (STUD_*)
    stud_meta = find_stud_posts(verts, faces, C, N, W, adj, pool_ext, area_lab, areas,
                                guides=guides, nf=nf, tol=tol, label_dist=label_dist,
                                flat_lim=flat_lim, cap=cap, table=table, accept=accept_ring,
                                directions=directions)
    for g in guides:
        g.pop("fm", None)
        g.pop("entry", None)

    # 2e. clean blends between parallel flats at different heights (BLEND_*)
    def accept_blend(fm, a):
        finish(a, fm, "blend", from_patch(fm))
    blend_meta = find_level_blends(verts, faces, C, N, W, adj, pool_ext, area_lab, areas,
                                   nf=nf, tol=tol, label_dist=label_dist, cap=cap,
                                   table=table, accept=accept_blend)
    pool &= pool_ext

    # 3. curves: same charts, same stiff spline, halves only when they help
    # Re-charted inside each missed patch on its own, so what is left of one
    # patch is never joined to what is left of the next.
    charts, small = [], 0.0
    for k in range(len(missed)):
        ck, sk = freeform_charts(pool & (patch_of == k), adj, N, W, min_patch)
        charts += ck
        small += sk
    could_not = 0.0
    sub_min = SPLIT_SUB_MIN_FACTOR * min_patch
    for members in charts:
        got = split_curve(members, verts, faces, C, Ns, W, adj, N,
                          stiffness=stiffness, tol=tol, cap=cap, sub_min=sub_min,
                          guides=guides, guide_min=min_patch)
        if not got:
            could_not += float(W[members].sum())
            continue
        for mem, fm, vidx, pts, fitted, depth in got:
            a = _free_area(len(areas), fm, W, fitted, pts, vidx)
            finish(a, fm, "curve", from_patch(fm), depth)

    # Bits under the minimum patch left between pieces (the blend along a
    # flat's edge) join the neighbouring curve piece of the same patch when
    # that piece, refitted with the same stiffness, keeps its pass/miss and
    # misses by no more than before. Otherwise they stay uncovered.
    absorbed = 0.0
    by_id = {a["id"]: a for a in areas}
    for k in range(len(missed)):
        for bit in _pieces(adj, pool0 & (patch_of == k) & (area_lab < 0)):
            if float(W[bit].sum()) >= min_patch:
                continue
            nb = np.unique(area_lab[adj[np.isin(adj[:, 0], bit) | np.isin(adj[:, 1], bit)].ravel()])
            cands = [by_id[i] for i in nb if i >= 0 and i in by_id
                     and by_id[i].get("split", {}).get("piece") == "curve"
                     and by_id[i]["split"]["from_missed_patch"] == k]
            for a in sorted(cands, key=lambda a: -a["area_mm2"]):
                mem = np.flatnonzero(a["_fmask"] | np.isin(np.arange(nfc), bit))
                fm, vidx, pts, fitted = _fit_chart(mem, verts, faces, W, N, stiffness=stiffness,
                                                   tol=tol, cap=cap)
                if fitted is None or fitted["within_tol"] != a["within_tol"] \
                        or fitted["judged"]["p95_mm"] > a["judged"]["p95_mm"]:
                    continue
                b2 = _free_area(a["id"], fm, W, fitted, pts, vidx)
                b2["split"] = a["split"]
                areas[a["id"]] = b2
                by_id[a["id"]] = b2
                area_lab[fm] = a["id"]
                absorbed += float(W[bit].sum())
                break

    new = [a for a in areas if "split" in a]
    for b in before:
        b["uncovered_mm2"] = round(float(W[pool0 & (patch_of == b["patch"]) & (area_lab < 0)].sum()), 2)
        b["kept_whole"] = (not b["flat"] and not b["round"] and not b["fillet"]
                           and not b["blend"] and len(b["curve"]) == 1)
    return {
        "rule": ("a stiff patch that misses is split, simplest first: flats "
                 "(same flat check), then rounds (same round check), then the "
                 "same stiff spline on what is left, cut in two only when a half "
                 f"then passes and every half is at least {sub_min:.0f} mm2, at "
                 f"most {SPLIT_MAX_DEPTH} times. Stiffness, tolerance and the 95% "
                 "rule are unchanged; pieces are not in the size check."),
        "n_missed_patches": len(missed),
        "missed_area_mm2": round(float(W[pool0].sum()), 2),
        "n_pieces": {"flat": sum(a["type"] == "flat" for a in new),
                     "round": sum(a["type"] == "round" and a["kind"] != "fillet" for a in new),
                     "fillet": sum(a["kind"] == "fillet" for a in new),
                     "curve": sum(a["type"] == "freeform" for a in new),
                     "stud_post": sum(bool(a.get("stud_post")) for a in new),
                     "level_blend": sum(a["type"] == "blend" for a in new)},
        "n_pieces_within_tol": {
            "flat": sum(a["within_tol"] for a in new if a["type"] == "flat"),
            "round": sum(a["within_tol"] for a in new
                         if a["type"] == "round" and a["kind"] != "fillet"),
            "fillet": sum(a["within_tol"] for a in new if a["kind"] == "fillet"),
            "curve": sum(a["within_tol"] for a in new if a["type"] == "freeform")},
        "partial_rounds": partial_meta,
        "capped_rings": ring_meta,
        "stud_posts": stud_meta,
        "level_blends": blend_meta,
        "pieces_outside_missed_patches": outside,
        "piece_area_mm2": {
            t: round(float(sum(a["area_mm2"] for a in new if a["type"] == t)), 2)
            for t in ("flat", "round", "freeform")},
        "uncovered_after_split_mm2": round(float(W[pool0 & (area_lab < 0)].sum()), 2),
        "left_below_min_patch_mm2": round(small, 2),
        "small_bits_joined_mm2": round(absorbed, 2),
        "n_kept_whole": sum(b["kept_whole"] for b in before),
        "missed_patches": before,
        "_could_not": could_not,
    }

# == splitting a stiff patch that misses ======================================
# A chart that misses the tolerance with one stiff spline usually is not one
# curve. On the pedal adapter the worst ones each span several real features:
# a top face with a raised disc on it, rib feet and the floor of a pocket.
# Loosening the spline would make them pass by following the scan, which is
# refused (the user: the solid should look like a perfect machined part, not a
# perfect match to the scan). Instead each missed patch is split into what is
# really there, simplest surface first:
#
# 1. flats: a plane found in the missed faces (seeded from their smoothed
#    normals), then put through the SAME flat check as every other flat
#    (flat_off_faces, small_pieces, flat_bend, same limits), plus the
#    straight-and-edged test below so a curve is not faceted. Its direction is
#    made exactly parallel/square to the part's direction groups when that
#    moves it by no more than the tolerance.
# 2. rounds: a circle searched for along the part's directions, then put
#    through the SAME round check as the circle search (round_evidence /
#    round_check: 60% of the turn, rms within 3 x noise). Holes get the same
#    size snap.
# 3. curves: what is left is charted with the same chart rules and gets the
#    same stiff spline. A curve that still misses is cut in two (along its
#    bend, or across its long side) only when a half then passes or the
#    worse half misses by at most half as much, and every half is at least
#    SPLIT_SUB_MIN_FACTOR x the minimum patch;
#    at most SPLIT_MAX_DEPTH times. Otherwise the whole stiff patch is kept
#    and reported outside tolerance - the simpler surface wins.
#
# The stiffness, the 95% rule and the tolerance are never touched. Pieces
# found here are measured only; like the freeform patches they are not moved
# into the size-check model.
SPLIT_SEEDS = 240
SPLIT_MAX_FLATS = 80
SPLIT_MAX_ROUNDS = 8
SPLIT_SUB_MIN_FACTOR = 4.0
SPLIT_MAX_DEPTH = 2
SPLIT_NORMAL_SMOOTH_MM = 1.5
SPLIT_BEND_MIN_DEG = 10.0
# A cut in two is kept when a half then passes, or when the worse half misses
# by no more than SPLIT_HALF_GAIN of what the whole missed by (two real
# features, not texture). Otherwise the simpler whole patch stays.
SPLIT_HALF_GAIN = 0.5
SPLIT_ROUND_MAX_R_MM = 60.0
# A flat found inside a missed patch must also be STRAIGHT and END AT AN
# EDGE. A narrow strip of a gentle curve passes the flat check (its sagitta
# over its own width is under the limit) and would cut the curve into facets,
# which is not what a machined part looks like. So:
# * straight: its own best quadratic (from flat_bend) may not bow more than
#   the flat limit over SPLIT_FLAT_REACH_MM - smallest radius at least
#   reach^2 / (8 x limit), 68 mm on the pedal adapter;
# * edged: of the faces just outside it (within SPLIT_EDGE_RING_MM), at least
#   SPLIT_EDGE_SHARE by area turn more than SPLIT_EDGE_DEG away from it. A
#   strip of a curve runs on into the same curve; a real face ends somewhere.
SPLIT_FLAT_REACH_MM = 10.0
SPLIT_EDGE_RING_MM = 3.0
SPLIT_EDGE_DEG = 15.0
SPLIT_EDGE_SHARE = 0.25
SPLIT_FLAT_TRIES = 400


def _pieces(adj: np.ndarray, mask: np.ndarray) -> list[np.ndarray]:
    """Connected pieces of `mask`, each as an array of face indices."""
    nfc = len(mask)
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        return []
    both = mask[adj[:, 0]] & mask[adj[:, 1]] if len(adj) else np.zeros(0, bool)
    e = adj[both] if len(adj) else np.zeros((0, 2), int)
    g = coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nfc, nfc))
    _, comp = connected_components(g, directed=False)
    c = comp[idx]
    order = np.argsort(c, kind="stable")
    _, starts = np.unique(c[order], return_index=True)
    return [idx[order][s:t] for s, t in zip(starts, list(starts[1:]) + [len(idx)])]


def _largest_piece(adj, mask, W) -> np.ndarray:
    out = np.zeros(len(mask), dtype=bool)
    ps = _pieces(adj, mask)
    if ps:
        out[max(ps, key=lambda p: float(W[p].sum()))] = True
    return out


def _plane_of(verts, faces, fmask, hint) -> tuple[np.ndarray, float]:
    n, d, _ = refine_plane(verts[np.unique(faces[fmask])])
    if float(n @ hint) < 0:
        n, d = -n, -d
    return n, float(d)


def _snap_direction(pts, n, d, directions, tol) -> tuple[np.ndarray, float, str | None]:
    """Make a split flat's normal exactly one of the part's directions when
    that moves it by no more than the tolerance (same rule as snapping 1)."""
    cos_p = np.cos(np.radians(SNAP_ANGLE_DEG))
    for g in directions:
        g = _unit(g)
        dot = float(g @ n)
        if abs(dot) < cos_p:
            continue
        n_new = g if dot > 0 else -g
        d_new = float(np.mean(pts @ n_new))
        move = float(np.abs(plane_residual(pts, n_new, d_new)
                            - plane_residual(pts, n, d)).max())
        if move <= tol:
            return n_new, d_new, f"direction made exact (part direction), moved {move:.4f} mm"
        return n, d, None
    return n, d, None


def flat_edge_share(C, N, W, fm, n, ring_mm: float = SPLIT_EDGE_RING_MM,
                    edge_deg: float = SPLIT_EDGE_DEG) -> float:
    """Share (by area) of the faces just outside a flat that turn away from it.

    1.0 when nothing lies around it (an open edge of the scan)."""
    idx = np.flatnonzero(fm)
    if len(idx) == 0:
        return 0.0
    lo, hi = C[idx].min(axis=0) - ring_mm, C[idx].max(axis=0) + ring_mm
    cand = np.flatnonzero(~fm & np.all((C >= lo) & (C <= hi), axis=1))
    if len(cand) == 0:
        return 1.0
    dist, _ = cKDTree(C[idx]).query(C[cand], distance_upper_bound=ring_mm)
    ring = cand[np.isfinite(dist)]
    if len(ring) == 0:
        return 1.0
    turned = (N[ring] @ _unit(n)) < np.cos(np.radians(edge_deg))
    return float(W[ring][turned].sum() / W[ring].sum())


def split_flats(verts, faces, C, N, Ns, W, adj, pool, *, label_dist, flat_lim,
                min_patch, directions, tol, rng) -> list[dict]:
    """Flat faces inside missed patches, each passed by the flat check.

    Takes them out of `pool` (in place). Returns one dict per flat.
    """
    cos_t = float(np.cos(np.radians(LABEL_ANGLE_DEG)))
    seedable = pool.copy()
    found = []
    for _ in range(SPLIT_FLAT_TRIES):
        if len(found) >= SPLIT_MAX_FLATS:
            break
        cand = np.flatnonzero(seedable)
        if len(cand) == 0 or float(W[cand].sum()) < min_patch:
            break
        pidx = np.flatnonzero(pool)
        Cp, Np, Wp = C[pidx], N[pidx], W[pidx]
        k = min(SPLIT_SEEDS, len(cand))
        seeds = rng.choice(cand, size=k, replace=False, p=W[cand] / W[cand].sum())
        best = (-1.0, None)
        for s in range(0, k, 24):
            S = seeds[s:s + 24]
            nS = Ns[S]
            dS = np.einsum("ij,ij->i", C[S], nS)
            on = (np.abs(Cp @ nS.T - dS) <= label_dist) & (Np @ nS.T >= cos_t)
            score = Wp @ on
            j = int(np.argmax(score))
            if score[j] > best[0]:
                best = (float(score[j]), int(S[j]))
        seed = best[1]
        if seed is None or best[0] < min_patch:
            break
        n, d = Ns[seed], float(C[seed] @ Ns[seed])
        tried = np.zeros(len(pool), dtype=bool)
        tried[seed] = True
        fm = pool & (np.abs(C @ n - d) <= label_dist) & (N @ n >= cos_t)
        fm = _largest_piece(adj, fm, W)
        if float(W[fm].sum()) < min_patch:
            seedable &= ~tried
            continue
        n, d = _plane_of(verts, faces, fm, n)
        fm = pool & (np.abs(C @ n - d) <= label_dist) & (N @ n >= cos_t)
        fm = _largest_piece(adj, fm, W)
        tried |= fm
        if float(W[fm].sum()) < min_patch:
            seedable &= ~tried
            continue
        n, d = _plane_of(verts, faces, fm, n)
        for _ in range(FLAT_PASSES):
            off = flat_off_faces(verts, faces, C, N, W, fm, n, d, limit=flat_lim)
            off |= small_pieces(adj, fm & ~off, W, min_patch)
            if not off.any():
                break
            fm = fm & ~off
            if float(W[fm].sum()) < min_patch:
                break
            n, d = _plane_of(verts, faces, fm, n)
        area = float(W[fm].sum())
        if area < min_patch:
            seedable &= ~tried
            continue
        bend = flat_bend(verts, faces, W, fm, n)
        if bend["bend_p95_mm"] > flat_lim:
            seedable &= ~tried
            continue
        r_min = SPLIT_FLAT_REACH_MM ** 2 / (8.0 * flat_lim)
        radii = [r for r in (bend["radii_mm"] or []) if r is not None]
        if radii and min(radii) < r_min:
            seedable &= ~tried
            continue
        edge = flat_edge_share(C, N, W, fm, n)
        if edge < SPLIT_EDGE_SHARE:
            seedable &= ~tried
            continue
        bend["edge_share"] = round(edge, 3)
        pts = verts[np.unique(faces[fm])]
        n, d, snap = _snap_direction(pts, n, d, directions, tol)
        pool &= ~fm
        seedable &= ~(fm | tried)
        seedable &= pool
        found.append({"fmask": fm, "n": n, "d": d, "bend": bend,
                      "snaps": [snap] if snap else []})
    return found


def _circle3(p) -> tuple[float, float, float] | None:
    (ax, ay), (bx, by), (cx, cy) = p
    dd = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(dd) < 1e-9:
        return None
    a2, b2, c2 = ax * ax + ay * ay, bx * bx + by * by, cx * cx + cy * cy
    ux = (a2 * (by - cy) + b2 * (cy - ay) + c2 * (ay - by)) / dd
    uy = (a2 * (cx - bx) + b2 * (ax - cx) + c2 * (bx - ax)) / dd
    return ux, uy, float(np.hypot(ax - ux, ay - uy))


def split_rounds(verts, faces, C, N, W, adj, pool, *, axes, label_dist, nf,
                 min_patch, rng) -> list[dict]:
    """Holes and bosses inside missed patches, each passed by the round check.

    Takes them out of `pool` (in place)."""
    sin_t = float(np.sin(np.radians(LABEL_ANGLE_DEG)))
    cos_t = float(np.cos(np.radians(LABEL_ANGLE_DEG)))
    found = []
    for a in axes:
        a = _unit(a)
        u, v = _perp_basis(a)
        for _ in range(SPLIT_MAX_ROUNDS):
            wall = pool & (np.abs(N @ a) <= sin_t)
            widx = np.flatnonzero(wall)
            if len(widx) < 12 or float(W[widx].sum()) < min_patch:
                break
            xy = np.column_stack([C[widx] @ u, C[widx] @ v])
            nxy = np.column_stack([N[widx] @ u, N[widx] @ v])
            nxy /= np.maximum(np.linalg.norm(nxy, axis=1), 1e-12)[:, None]
            pw = W[widx] / W[widx].sum()
            best = (-1.0, None)
            for _ in range(SPLIT_SEEDS):
                tri = rng.choice(len(widx), 3, replace=False, p=pw)
                circ = _circle3(xy[tri])
                if circ is None:
                    continue
                cx, cy, r = circ
                if r < HOLE_MIN_D_MM / 2 or r > SPLIT_ROUND_MAX_R_MM:
                    continue
                rel = xy - (cx, cy)
                rad = np.maximum(np.linalg.norm(rel, axis=1), 1e-12)
                inl = (np.abs(rad - r) <= label_dist) & (
                    np.abs(np.einsum("ij,ij->i", nxy, rel / rad[:, None])) >= cos_t)
                sc = float(W[widx][inl].sum())
                if sc > best[0]:
                    best = (sc, (cx, cy, r))
            if best[1] is None or best[0] < min_patch:
                break
            cx, cy, r = best[1]
            p0 = cx * u + cy * v
            fm = np.zeros(len(pool), dtype=bool)
            rel = xy - (cx, cy)
            rad = np.maximum(np.linalg.norm(rel, axis=1), 1e-12)
            fm[widx[(np.abs(rad - r) <= label_dist) & (
                np.abs(np.einsum("ij,ij->i", nxy, rel / rad[:, None])) >= cos_t)]] = True
            fm = _largest_piece(adj, fm, W)
            if float(W[fm].sum()) < min_patch:
                break
            pts = verts[np.unique(faces[fm])]
            ax, p, r = fit_cylinder(pts, a, p0, r)
            rel3 = C - p
            perp = rel3 - np.outer(rel3 @ ax, ax)
            rad3 = np.linalg.norm(perp, axis=1)
            uh = perp / np.maximum(rad3, 1e-12)[:, None]
            fm = (pool & (np.abs(rad3 - r) <= label_dist) & (np.abs(N @ ax) <= sin_t)
                  & (np.abs(np.einsum("ij,ij->i", N, uh)) >= cos_t))
            fm = _largest_piece(adj, fm, W)
            if float(W[fm].sum()) < min_patch:
                break
            pts = verts[np.unique(faces[fm])]
            ax, p, r = fit_cylinder(pts, ax, p, r)
            ev = round_evidence(C, N, W, ax, p, r, band=np.inf, mask=fm)
            ev["rms_mm"] = round(float(np.sqrt(np.mean(cyl_residual(pts, ax, p, r) ** 2))), 5)
            why = round_check(ev, nf)
            if why is not None:
                break
            pool &= ~fm
            found.append({"fmask": fm, "a": ax, "p": p, "r": float(r), "evidence": ev})
    return found


# == partial rounds: fillets and part-bosses ==================================
# A machined part is full of rounds that are NOT 60% of a circle: the rounded
# edge between two faces (a fillet, usually a quarter turn) and the side of a
# boss or a pocket that runs into a flat or another face. The round check
# (ROUND_MIN_COVERAGE) turns all of those away, so on the pedal adapter the
# split found no rounds at all and the rounded edges along its new flats were
# left uncovered. They are accepted here, but only with evidence a short arc
# cannot fake:
#
# 1. Fillets. A strip between two fitted flats whose normals differ by
#    FILLET_MIN_DEG..FILLET_MAX_DEG becomes a cylinder TANGENT to both flats:
#    its axis is exactly the line the two flats meet in, its centre sits
#    exactly one radius from each flat, so the radius is the only thing
#    fitted. It must touch both flats, cover FILLET_MIN_ARC of the turn from
#    one flat to the other and fit within the round check's noise multiple
#    (ROUND_MAX_RMS_NOISE x noise rms); it is then judged by the 95% rule like
#    every area and reported outside tolerance if it misses. The radius is
#    snapped to a standard radius (FILLET_RADII_*) only when that moves the
#    surface by no more than the tolerance anywhere on the strip.
# 2. Partial rounds. An arc under 60% of the turn is a round when its axis is
#    exactly one of the part's directions or an existing round's axis (fixed,
#    not fitted), both ends of the arc stop at a fitted flat/round or a
#    crease (PARTIAL_END_SHARE of the faces just past each end), at least one
#    end along the axis does too (a top or a floor), it bows at least
#    PARTIAL_MIN_SAGITTA x the join distance (a strip of a flat or a gentle
#    curve does not), and it fits within the same noise multiple. The 95%
#    rule then judges it like any other area.
#
# A strip that merely looks curved - varying radius, wavy, a bowl - fails
# the constant-radius fit and stays for the stiff spline. Stiffness, the
# tolerance and the 95% rule are untouched. Like every split piece these are
# measured only, not moved into the size-check model.
FILLET_MIN_DEG = 20.0
FILLET_MAX_DEG = 160.0
FILLET_MIN_R_MM = 0.5
FILLET_MAX_R_MM = 20.0
FILLET_MIN_ARC = 0.5
# Of the surface in the corner between the two flats, along the strip's own
# length, at least this share must lie on the arc. A wavy strip crosses a
# constant-radius arc only in bands; a real rounded edge fills the corner.
FILLET_MIN_CORNER_SHARE = 0.7
FILLET_ARC_BINS = 8
FILLET_WEDGE_SLACK = 0.1
FILLET_MIN_MM2 = MIN_PATCH_MM2
PARTIAL_MIN_SAGITTA = 2.0
# An arc shorter than this cannot pin its radius against scan noise (a 15
# degree arc of a d200 "boss" bows 0.6 mm), and that is exactly how the old
# circle search made fake d84-d243 bosses out of cast curves. The radius
# limit is the split's own (SPLIT_ROUND_MAX_R_MM), checked after the fit.
PARTIAL_MIN_SPAN_DEG = 45.0
PARTIAL_END_SHARE = 0.5
PARTIAL_TRIES = 12
PARTIAL_SAMPLE_MM = 6.0
# Along the axis a real boss side stops at its top or at the floor - a turn
# of about 90 degrees. A band cut out of a wavy surface also turns away from
# the cylinder (30-45 degrees within a few mm on the wavy test strip), so
# the crease along the axis must turn at least this much. At least one end
# along the axis (its top or its floor) must stop like that; the other may
# run out through a blend (a foot fillet, draft) that is not fitted yet.
PARTIAL_AXIAL_CREASE_DEG = 60.0
# Fillets and partial rounds are looked for inside the split (the patches
# that miss, plus whatever is still uncovered). Looking for them on all of
# 'other' BEFORE any spline is the switch below; on the pedal adapter that
# took faces from stiff patches that already passed and cut the charts into
# more pieces under the minimum patch: 80 areas inside tolerance and 79.1%
# covered, against 86 and 79.8% with it off. Off, so passing patches are left
# as they were.
PARTIAL_BEFORE_CHARTS = False


def _radius_table(table: str) -> np.ndarray:
    """Standard fillet / edge radii (mm). Metric: 0.25 steps to 2, 0.5 to
    10, whole mm to 30. Inch: 1/64" to 1/4", 1/32" to 1/2", 1/16" to 1"."""
    if table == "inch":
        fr = set()
        for step, top in ((64, 0.25), (32, 0.5), (16, 1.0)):
            k = 1
            while k / step <= top + 1e-12:
                fr.add(round(k / step, 9))
                k += 1
        return np.array(sorted(f * INCH for f in fr))
    s = set(np.round(np.arange(0.25, 2.0 + 1e-9, 0.25), 3))
    s |= set(np.round(np.arange(2.5, 10.0 + 1e-9, 0.5), 3))
    s |= set(np.arange(11.0, 30.0 + 1e-9, 1.0))
    return np.array(sorted(float(x) for x in s))


def _fillet_frame(n1, d1, n2, d2):
    """Axis, a point on the meeting line, and q with n1.q = n2.q = 1."""
    a = _unit(np.cross(n1, n2))
    M = np.vstack([n1, n2])
    x0 = np.linalg.lstsq(M, np.array([d1, d2]), rcond=None)[0]
    q = np.linalg.pinv(M) @ np.ones(2)
    return a, x0, q


def _fillet_fit(P, w, a, x0, q, s, r0=None, band=None):
    """Radius of the cylinder tangent to both flats (centre x0 - s r q) that
    best fits P. Returns (r, centre). Without a start radius, the radius
    that puts the most area within `band` of the cylinder is the start."""
    def res(x):
        c = x0 - s * x[0] * q
        return np.sqrt(w) * cyl_residual(P, a, c, x[0])
    if r0 is None:
        grid = np.geomspace(FILLET_MIN_R_MM, FILLET_MAX_R_MM, 120)
        score = [float(w[np.abs(cyl_residual(P, a, x0 - s * g * q, g)) <= band].sum())
                 for g in grid]
        r0 = float(grid[int(np.argmax(score))])
    sol = least_squares(res, [r0], bounds=([FILLET_MIN_R_MM * 0.5], [FILLET_MAX_R_MM * 1.5]))
    r = float(sol.x[0])
    return r, x0 - s * r * q


def find_fillets(verts, faces, C, N, W, adj, pool, area_lab, areas, *, nf, tol,
                 label_dist, cap, table, accept) -> list[dict]:
    """Fillets between fitted flats, taken from `pool` (in place).

    `accept(fm, area_dict)` labels and stores each one. Returns a log of
    every flat pair tried (accepted or why not)."""
    flats = [a for a in areas if a["type"] == "flat"]
    log = []
    if len(flats) < 2 or not pool.any():
        return log
    cos_f = np.cos(np.radians(ROUND_FACING_DEG))
    sin_t = np.sin(np.radians(LABEL_ANGLE_DEG))
    ring = SPLIT_EDGE_RING_MM
    reach = FILLET_MAX_R_MM * np.pi / 2 + ring
    pidx = np.flatnonzero(pool)
    near = {}
    for f in flats:
        idx = np.flatnonzero(area_lab == f["id"])
        if len(idx) == 0:
            continue
        dist, _ = cKDTree(C[idx]).query(C[pidx], distance_upper_bound=reach)
        near[f["id"]] = dist
    ids = [f for f in flats if f["id"] in near]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            f1, f2 = ids[i], ids[j]
            n1, n2 = _unit(f1["_n"]), _unit(f2["_n"])
            ang = float(np.degrees(np.arccos(np.clip(n1 @ n2, -1, 1))))
            if not FILLET_MIN_DEG <= ang <= FILLET_MAX_DEG:
                continue
            both = (near[f1["id"]] <= reach) & (near[f2["id"]] <= reach) & pool[pidx]
            if float(W[pidx[both]].sum()) < FILLET_MIN_MM2:
                continue
            d1, d2 = float(f1["_d"]), float(f2["_d"])
            a, x0, q = _fillet_frame(n1, d1, n2, d2)
            ci = pidx[both]
            Nc = N[ci]
            g12 = float(n1 @ n2)
            G = np.array([[1.0, g12], [g12, 1.0]])
            ab = np.linalg.solve(G, np.vstack([Nc @ n1, Nc @ n2]))
            sl = FILLET_WEDGE_SLACK
            wedge = (ab[0] >= -sl) & (ab[1] >= -sl) & (np.abs(Nc @ a) <= sin_t)
            ci, dn1, dn2 = ci[wedge], near[f1["id"]][both][wedge], near[f2["id"]][both][wedge]
            if float(W[ci].sum()) < FILLET_MIN_MM2:
                continue
            entry = {"flats": [f1["id"], f2["id"]], "angle_deg": round(ang, 2),
                     "candidate_mm2": round(float(W[ci].sum()), 2)}
            best = None
            seen = []
            # The strip is what lies on the tangent arc AND is one piece from
            # one flat to the other; the radius is searched for the arc that
            # holds the most of that, then refitted.
            loc = np.full(len(W), -1, dtype=np.int64)
            loc[ci] = np.arange(len(ci))
            el = loc[adj[(loc[adj[:, 0]] >= 0) & (loc[adj[:, 1]] >= 0)]]
            g = coo_matrix((np.ones(len(el)), (el[:, 0], el[:, 1])),
                           shape=(len(ci), len(ci))).tocsr()
            t1, t2 = dn1 <= ring, dn2 <= ring
            Wc, Cc, Ncw = W[ci], C[ci], Nc[wedge]
            e2 = _unit(n2 - g12 * n1)
            th = np.radians(ang)

            def touching(s, r):
                c = x0 - s * r * q
                rel = Cc - c
                perp = rel - np.outer(rel @ a, a)
                rad = np.linalg.norm(perp, axis=1)
                uh = perp / np.maximum(rad, 1e-12)[:, None]
                # only between the two tangent lines: past them it is the
                # flat itself, which also lies near the arc there
                us = s * uh
                ph = np.arctan2(us @ e2, us @ n1)
                on = ((np.abs(rad - r) <= label_dist)
                      & (s * np.einsum("ij,ij->i", Ncw, uh) >= cos_f)
                      & (ph >= 0) & (ph <= th))
                out = np.zeros(len(ci), dtype=bool)
                idx = np.flatnonzero(on)
                if len(idx) == 0:
                    return out
                _, lab = connected_components(g[idx][:, idx], directed=False)
                h1 = np.bincount(lab, weights=t1[idx].astype(float)) > 0
                h2 = np.bincount(lab, weights=t2[idx].astype(float)) > 0
                out[idx[h1[lab] & h2[lab]]] = True
                return out

            grid = np.geomspace(FILLET_MIN_R_MM, FILLET_MAX_R_MM, 48)
            for s in (1.0, -1.0):
                score = [float(Wc[touching(s, rr)].sum()) for rr in grid]
                k = int(np.argmax(score))
                if score[k] < FILLET_MIN_MM2:
                    seen.append({"convex": bool(s > 0), "best_touching_mm2": round(score[k], 2)})
                    continue
                r = float(grid[k])
                keep = touching(s, r)
                for _ in range(2):
                    r2, _c = _fillet_fit(Cc[keep], Wc[keep], a, x0, q, s, r)
                    k2 = touching(s, r2)
                    if float(Wc[k2].sum()) < FILLET_MIN_MM2:
                        break
                    r, keep = r2, k2
                area = float(Wc[keep].sum())
                seen.append({"convex": bool(s > 0), "radius_mm": round(r, 3),
                             "touching_both_mm2": round(area, 2)})
                if best is None or area > best[0]:
                    kg = np.zeros(len(W), dtype=bool)
                    kg[ci[keep]] = True
                    best = (area, s, kg, r)
            if best is None:
                entry["why"] = "no strip on a tangent arc that touches both flats"
                entry["looked_at"] = seen
                log.append(entry)
                continue
            _, s, fm, r = best
            c0 = x0 - s * r * q
            fm = _trim_border(adj, fm, faces, verts, lambda P: cyl_residual(P, a, c0, r), tol)
            if float(W[fm].sum()) < FILLET_MIN_MM2:
                entry["why"] = "too little left once the border row is trimmed"
                log.append(entry)
                continue
            vidx, wv, _ = _area_vertices(faces, W, fm)
            pts = verts[vidx]
            r, c = _fillet_fit(pts, wv, a, x0, q, s, r)
            res = cyl_residual(pts, a, c, r)
            rms = float(np.sqrt(np.average(res ** 2, weights=wv)))
            # share of the turn from one flat to the other the strip covers
            rel = C[fm] - c
            perp = rel - np.outer(rel @ a, a)
            uh = s * perp / np.maximum(np.linalg.norm(perp, axis=1), 1e-12)[:, None]
            phi = np.arctan2(uh @ e2, uh @ n1)
            hist = np.histogram(np.clip(phi, 0, th), bins=FILLET_ARC_BINS, range=(0, th),
                                weights=W[fm])[0]
            cov = float(np.count_nonzero(hist > 0)) / FILLET_ARC_BINS
            # how much of the corner between the flats (over the strip's own
            # length) is on the arc - a strip that only crosses the arc here
            # and there is not a fillet
            sec = np.flatnonzero(pool | fm)
            rel = C[sec] - c
            along = rel @ a
            perp = rel - np.outer(along, a)
            rad = np.linalg.norm(perp, axis=1)
            uh_s = s * perp / np.maximum(rad, 1e-12)[:, None]
            ph = np.arctan2(uh_s @ e2, uh_s @ n1)
            al = C[fm] @ a
            insec = ((ph >= 0) & (ph <= th) & (along >= al.min() - (c @ a)) & (along <= al.max() - (c @ a))
                     & (np.abs(rad - r) <= max(0.5 * r, 3 * label_dist)))
            corner = fm.copy()
            corner[sec[insec]] = True
            share = float(W[fm].sum() / W[corner].sum())
            entry.update(radius_mm=round(r, 4), convex=bool(s > 0), area_mm2=round(float(W[fm].sum()), 2),
                         rms_mm=round(rms, 5), arc_coverage=round(cov, 3),
                         corner_share=round(share, 3))
            why = []
            if rms > ROUND_MAX_RMS_NOISE * nf:
                why.append(f"fit rms {rms:.3f} mm is over {ROUND_MAX_RMS_NOISE:g} x noise")
            if not FILLET_MIN_R_MM <= r <= FILLET_MAX_R_MM:
                why.append(f"radius {r:.2f} mm is outside {FILLET_MIN_R_MM:g}-"
                           f"{FILLET_MAX_R_MM:g} mm (the scan spacing cannot show less)")
            if cov < FILLET_MIN_ARC:
                why.append(f"covers {cov * 100:.0f}% of the turn between the flats "
                           f"(needs {FILLET_MIN_ARC * 100:.0f}%)")
            if share < FILLET_MIN_CORNER_SHARE:
                why.append(f"only {share * 100:.0f}% of the corner between the flats lies "
                           f"on the arc (needs {FILLET_MIN_CORNER_SHARE * 100:.0f}%)")
            snaps = []
            if not why:
                tab = _radius_table(table)
                r_std = float(tab[np.argmin(np.abs(tab - r))])
                c_std = x0 - s * r_std * q
                move = float(np.abs(cyl_residual(pts, a, c_std, r_std) - res).max())
                if move <= tol:
                    snaps.append(f"radius {r:.4f} -> {r_std:g} mm ({table}), moved {move:.4f} mm")
                    r, c = r_std, c_std
                    res = cyl_residual(pts, a, c, r)
                entry["standard_radius_mm"] = r_std
                entry["snap_move_mm"] = round(move, 4)
                pc = pass_check(pts, wv, res, tol=tol, cap=cap, axis=a, point=c)
                # Judged like every other area: a round that misses the 95%
                # rule is kept and reported outside tolerance, not dropped.
                entry["judged_p95_mm"] = pc["stats"]["p95_mm"]
            if why:
                entry["why"] = "; ".join(why)
                log.append(entry)
                continue
            c = _axis_foot(a, c, pts.mean(0))
            st = _stats(res)
            along = pts @ a
            area = {
                "id": len(areas), "type": "round", "kind": "fillet",
                "n_faces": int(fm.sum()), "area_mm2": round(float(W[fm].sum()), 2),
                "n_patches": len(_pieces(adj, fm)), "snaps": snaps,
                "standard_size": {"table": table, "radius_mm": r if snaps else None,
                                  "nearest_radius_mm": entry["standard_radius_mm"]},
                "fillet": {"between_flats": [f1["id"], f2["id"]],
                           "angle_between_deg": round(ang, 2),
                           "convex": bool(s > 0), "tangent_to_both": True,
                           "arc_coverage": round(cov, 3), "rms_mm": round(rms, 5),
                           "radius_mm": round(r, 4)},
                "fit": {"axis": [round(float(x), 6) for x in a],
                        "point_mm": [round(float(x), 4) for x in c],
                        "diameter_mm": round(2 * r, 4),
                        "length_mm": round(float(along.max() - along.min()), 3), **st},
                "final": {"axis": [round(float(x), 9) for x in a],
                          "point_mm": [round(float(x), 4) for x in c],
                          "diameter_mm": round(2 * r, 4), **st},
                "judged": pc["stats"], "within_tol": pc["stats"]["within_tol"],
                "within_tol_raw": bool(st["p95_mm"] <= tol),
                "_a": a, "_p": c, "_r": r, "_concave": bool(s < 0), "_pts": pts,
                "_fmask": fm, "_vidx": vidx, "_jres": pc["residual"]}
            entry["accepted_area"] = area["id"]
            log.append(entry)
            pool &= ~fm
            accept(fm, area)
    return log


def _interior(adj: np.ndarray, fm: np.ndarray, min_keep: int = 12) -> np.ndarray:
    """`fm` without its border row (faces next to a face outside it), unless
    that would leave fewer than `min_keep` faces."""
    if len(adj) == 0:
        return fm
    cut = fm[adj[:, 0]] != fm[adj[:, 1]]
    border = np.zeros(len(fm), dtype=bool)
    border[adj[cut].ravel()] = True
    inner = fm & ~border
    return inner if inner.sum() >= min_keep else fm


def _trim_border(adj, fm, faces, verts, resfn, tol: float) -> np.ndarray:
    """Drop border faces with a corner more than `tol` off the round - the
    crease blending into the next face, as edge_bands does for the main
    areas. One pass, border only, so no holes are punched inside."""
    if len(adj) == 0 or not fm.any():
        return fm
    cut = fm[adj[:, 0]] != fm[adj[:, 1]]
    border = np.zeros(len(fm), dtype=bool)
    border[adj[cut].ravel()] = True
    b = np.flatnonzero(fm & border)
    if len(b) == 0:
        return fm
    off = np.abs(resfn(verts[faces[b]].reshape(-1, 3))).reshape(-1, 3).max(axis=1) > tol
    out = fm.copy()
    out[b[off]] = False
    return out


def fit_circle_fixed_axis_robust(pts, a, p0, scale: float) -> tuple[np.ndarray, float]:
    """Fixed-axis circle fit that a few faces from the next surface cannot
    drag. On a short arc the radius and the centre trade off against each
    other, so a row of faces just past a crease moved a 60-degree R8 arc to
    R8.5 with a least-squares fit; a soft-L1 loss at `scale` keeps it at R8."""
    p, r = fit_circle_fixed_axis(pts, a, p0)
    u, v = _perp_basis(a)
    rel = pts - p
    x, y = rel @ u, rel @ v

    def res(q):
        return np.hypot(x - q[0], y - q[1]) - q[2]
    q = least_squares(res, [0.0, 0.0, r], loss="soft_l1", f_scale=max(scale, 1e-6)).x
    return p + q[0] * u + q[1] * v, float(abs(q[2]))


def _arc_span(theta: np.ndarray) -> tuple[float, float, float]:
    """(start, end, span) of the angles, going counter-clockwise, with the
    largest empty gap left out."""
    t = np.sort(np.mod(theta, 2 * np.pi))
    gaps = np.diff(np.concatenate([t, [t[0] + 2 * np.pi]]))
    k = int(np.argmax(gaps))
    start = t[(k + 1) % len(t)]
    end = t[k]
    return float(start), float(end), float(2 * np.pi - gaps[k])


def arc_ends_bounded(C, N, W, fm, a, p, r, side, fitted, *, ring=SPLIT_EDGE_RING_MM,
                     edge_deg=CHART_CREASE_DEG) -> list[float | None]:
    """For each end of an arc - both ends around the turn, then both ends
    along the axis - the share (by area) of the faces just past it that
    belong to a fitted flat/round (`fitted`) or turn more than `edge_deg`
    from where the cylinder would carry on (a crease: the same angle the
    charts refuse to cross). None when nothing lies past that end (an open
    edge of the scan), which does NOT count as bounded: nothing there
    shows where the round stops."""
    u, v = _perp_basis(a)
    rel = C - p
    along = rel @ a
    perp = rel - np.outer(along, a)
    rad = np.linalg.norm(perp, axis=1)
    uh = perp / np.maximum(rad, 1e-12)[:, None]
    th = np.arctan2(uh @ v, uh @ u)
    start, end, span = _arc_span(th[fm])
    lo, hi = float(along[fm].min()) - ring / 2, float(along[fm].max()) + ring / 2
    out = []
    reach = ring / max(r, 1e-6)
    for e, sgn in ((start, -1.0), (end, 1.0)):
        dlt = sgn * (np.mod(th - e + np.pi, 2 * np.pi) - np.pi)
        past = (~fm & (dlt > 0) & (dlt * r <= ring) & (np.abs(rad - r) <= ring)
                & (along >= lo) & (along <= hi))
        if not past.any():
            out.append(None)
            continue
        turned = np.einsum("ij,ij->i", N[past], side * uh[past]) < np.cos(np.radians(edge_deg))
        ok = fitted[past] | turned
        out.append(float(W[past][ok].sum() / W[past].sum()))
    # along the axis: a real boss side stops at a face (its top, the floor);
    # a band cut out of a wavy surface runs on into more of the same
    # (only faces right next to the arc, inside its own sweep, so the faces
    # beside it - already counted above - do not vouch for these ends)
    inside = np.mod(th - start, 2 * np.pi) <= span
    alo, ahi = float(along[fm].min()), float(along[fm].max())
    cand = np.flatnonzero(~fm & inside & (np.abs(rad - r) <= ring)
                          & (((along < alo) & (along >= alo - ring))
                             | ((along > ahi) & (along <= ahi + ring))))
    close = np.zeros(len(W), dtype=bool)
    if len(cand):
        dist, _ = cKDTree(C[fm]).query(C[cand], distance_upper_bound=ring)
        close[cand[np.isfinite(dist)]] = True
    for past_ax in ((along < alo), (along > ahi)):
        past = close & past_ax
        if not past.any():
            out.append(None)
            continue
        turned = (np.einsum("ij,ij->i", N[past], side * uh[past])
                  < np.cos(np.radians(max(edge_deg, PARTIAL_AXIAL_CREASE_DEG))))
        ok = fitted[past] | turned
        out.append(float(W[past][ok].sum() / W[past].sum()))
    return out


def find_partial_rounds(verts, faces, C, N, W, adj, pool, area_lab, areas, *, axes, nf,
                        tol, label_dist, min_patch, cap, table, rng, accept) -> list[dict]:
    """Rounds under 60% of the turn on fixed part axes, taken from `pool`."""
    sin_t = float(np.sin(np.radians(LABEL_ANGLE_DEG)))
    cos_t = float(np.cos(np.radians(LABEL_ANGLE_DEG)))
    log = []
    for a in axes:
        a = _unit(a)
        u, v = _perp_basis(a)
        tried = np.zeros(len(W), dtype=bool)
        for _ in range(PARTIAL_TRIES):
            wall = pool & ~tried & (np.abs(N @ a) <= sin_t)
            widx = np.flatnonzero(wall)
            if len(widx) < 12 or float(W[widx].sum()) < min_patch:
                break
            xy = np.column_stack([C[widx] @ u, C[widx] @ v])
            nxy = np.column_stack([N[widx] @ u, N[widx] @ v])
            nxy /= np.maximum(np.linalg.norm(nxy, axis=1), 1e-12)[:, None]
            tree = cKDTree(C[widx])
            pw = W[widx] / W[widx].sum()
            best = (-1.0, None)
            for sd in rng.choice(len(widx), size=min(SPLIT_SEEDS, len(widx)), replace=False, p=pw):
                nb = tree.query_ball_point(C[widx[sd]], PARTIAL_SAMPLE_MM)
                nb = [k for k in nb if k != sd]
                if len(nb) < 2:
                    continue
                two = rng.choice(nb, 2, replace=False)
                circ = _circle3(xy[[sd, two[0], two[1]]])
                if circ is None:
                    continue
                cx, cy, r = circ
                if r < HOLE_MIN_D_MM / 2 or r > SPLIT_ROUND_MAX_R_MM:
                    continue
                rel = xy - (cx, cy)
                rad = np.maximum(np.linalg.norm(rel, axis=1), 1e-12)
                inl = (np.abs(rad - r) <= label_dist) & (
                    np.abs(np.einsum("ij,ij->i", nxy, rel / rad[:, None])) >= cos_t)
                sc = float(W[widx][inl].sum())
                if sc > best[0]:
                    best = (sc, (cx, cy, r))
            if best[1] is None or best[0] < min_patch:
                break
            cx, cy, r = best[1]
            p = cx * u + cy * v
            fm = np.zeros(len(W), dtype=bool)
            for _k in range(3):
                rel3 = C - p
                perp = rel3 - np.outer(rel3 @ a, a)
                rad3 = np.linalg.norm(perp, axis=1)
                uh = perp / np.maximum(rad3, 1e-12)[:, None]
                fm = (wall & (np.abs(rad3 - r) <= label_dist)
                      & (np.abs(np.einsum("ij,ij->i", N, uh)) >= cos_t))
                fm = _largest_piece(adj, fm, W)
                if float(W[fm].sum()) < min_patch:
                    break
                # fitted on the faces inside the piece: its border row is
                # where the crease blends into the next face
                p, r = fit_circle_fixed_axis_robust(verts[np.unique(faces[_interior(adj, fm)])],
                                                    a, p, nf)
            if float(W[fm].sum()) >= min_patch:
                fm = _trim_border(adj, fm, faces, verts, lambda P: cyl_residual(P, a, p, r), tol)
            if float(W[fm].sum()) < min_patch:
                tried |= fm
                tried[widx[np.argmax(pw)]] = True
                continue
            vidx, wv, _ = _area_vertices(faces, W, fm)
            pts = verts[vidx]
            p = _axis_foot(a, p, pts.mean(0))
            res = cyl_residual(pts, a, p, r)
            rms = float(np.sqrt(np.average(res ** 2, weights=wv)))
            rel = C[fm] - p
            perp = rel - np.outer(rel @ a, a)
            uh = perp / np.maximum(np.linalg.norm(perp, axis=1), 1e-12)[:, None]
            outward = float(np.average(np.einsum("ij,ij->i", N[fm], uh), weights=W[fm]))
            side = 1.0 if outward > 0 else -1.0
            th = np.arctan2(uh @ v, uh @ u)
            _, _, span = _arc_span(th)
            cov = arc_coverage(C, W, fm, a, p)
            sag = r * (1 - np.cos(min(span, np.pi) / 2))
            fitted = np.zeros(len(W), dtype=bool)
            lab_ok = area_lab >= 0
            types = np.array([areas[i]["type"] for i in range(len(areas))] + ["none"])
            fitted[lab_ok] = np.isin(types[area_lab[lab_ok]], ("flat", "round"))
            ends = arc_ends_bounded(C, N, W, fm, a, p, r, side, fitted)
            entry = {"axis": [round(float(x), 4) for x in a], "diameter_mm": round(2 * r, 4),
                     "area_mm2": round(float(W[fm].sum()), 2), "coverage": round(cov, 4),
                     "span_deg": round(float(np.degrees(span)), 1),
                     "sagitta_mm": round(float(sag), 4), "rms_mm": round(rms, 5),
                     "end_share": [None if e is None else round(e, 3) for e in ends],
                     "side": "outward" if side > 0 else "inward"}
            why = []
            if rms > ROUND_MAX_RMS_NOISE * nf:
                why.append(f"fit rms {rms:.3f} mm is over {ROUND_MAX_RMS_NOISE:g} x noise")
            if span < np.radians(PARTIAL_MIN_SPAN_DEG):
                why.append(f"spans {np.degrees(span):.0f} deg of the turn "
                           f"(needs {PARTIAL_MIN_SPAN_DEG:g})")
            if r > SPLIT_ROUND_MAX_R_MM:
                why.append(f"radius {r:.1f} mm is over {SPLIT_ROUND_MAX_R_MM:g} mm")
            if sag < PARTIAL_MIN_SAGITTA * label_dist:
                why.append(f"bows only {sag:.3f} mm (needs {PARTIAL_MIN_SAGITTA:g} x "
                           f"{label_dist:.3f} mm)")
            def bounded(e):
                return e is not None and e >= PARTIAL_END_SHARE
            if cov < ROUND_MIN_COVERAGE:
                if not (bounded(ends[0]) and bounded(ends[1])):
                    why.append("an end of the arc runs on into unfitted surface, "
                               "not a fitted face or a crease")
                if not (bounded(ends[2]) or bounded(ends[3])):
                    why.append("neither end along the axis stops at a fitted face "
                               "or a crease (no top, no floor)")
            kind = "boss" if side > 0 else "hole"
            snaps = []
            std = {"table": table, "nearest_mm": round(nearest_size(2 * r, table), 4)}
            pc = None
            if not why:
                if kind == "hole":
                    d_std = snap_hole(2 * r, table, tol)
                    if d_std is not None:
                        snaps.append(f"diameter {2 * r:.4f} -> {d_std:g} mm ({table}), "
                                     f"moved {abs(d_std - 2 * r) / 2:.4f} mm")
                        r = d_std / 2
                        std = {"table": table, "diameter_mm": d_std}
                        res = cyl_residual(pts, a, p, r)
                pc = pass_check(pts, wv, res, tol=tol, cap=cap, axis=a, point=p)
                # Judged like every other area: a round that misses the 95%
                # rule is kept and reported outside tolerance, not dropped.
                entry["judged_p95_mm"] = pc["stats"]["p95_mm"]
            if why:
                entry["why"] = "; ".join(why)
                log.append(entry)
                tried |= fm
                continue
            st = _stats(res)
            along = pts @ a
            area = {
                "id": len(areas), "type": "round", "kind": kind,
                "n_faces": int(fm.sum()), "area_mm2": round(float(W[fm].sum()), 2),
                "n_patches": 1, "snaps": snaps, "standard_size": std,
                "partial": cov < ROUND_MIN_COVERAGE,
                "round_check": {"coverage": round(cov, 4), "rms_mm": round(rms, 5),
                                "span_deg": entry["span_deg"], "sagitta_mm": entry["sagitta_mm"],
                                "end_share": entry["end_share"], "axis_fixed": True},
                "fit": {"axis": [round(float(x), 6) for x in a],
                        "point_mm": [round(float(x), 4) for x in p],
                        "diameter_mm": round(2 * r, 4),
                        "length_mm": round(float(along.max() - along.min()), 3), **st},
                "final": {"axis": [round(float(x), 9) for x in a],
                          "point_mm": [round(float(x), 4) for x in p],
                          "diameter_mm": round(2 * r, 4), **st},
                "judged": pc["stats"], "within_tol": pc["stats"]["within_tol"],
                "within_tol_raw": bool(st["p95_mm"] <= tol),
                "_a": a, "_p": p, "_r": r, "_pts": pts, "_fmask": fm, "_vidx": vidx,
                "_jres": pc["residual"]}
            entry["accepted_area"] = area["id"]
            log.append(entry)
            pool &= ~fm
            accept(fm, area)
    return log


def round_axes(directions, areas) -> list[np.ndarray]:
    """Part directions, the frame axes and every existing round's axis, once each."""
    out: list[np.ndarray] = []
    cand = list(directions) + [a["_a"] for a in areas if a["type"] == "round"] + list(np.eye(3))
    for g in cand:
        g = _unit(g)
        if all(abs(float(g @ x)) < 0.995 for x in out):
            out.append(g)
    return out


def _bisections(members, C, Ns, W) -> list[list[np.ndarray]]:
    """Ways to cut a chart in two: along its bend, then across its long side."""
    out = []
    w = W[members]
    nrm = Ns[members]
    mu = np.average(nrm, axis=0, weights=w)
    X = nrm - mu
    cov = (X * w[:, None]).T @ X / float(w.sum())
    ev, evec = np.linalg.eigh(cov)
    if np.sqrt(max(ev[-1], 0.0)) >= np.sin(np.radians(SPLIT_BEND_MIN_DEG)) / 2:
        s = X @ evec[:, -1]
        out.append(s > _wpercentile(s, w, 50))
    P = C[members] - np.average(C[members], axis=0, weights=w)
    cov = (P * w[:, None]).T @ P / float(w.sum())
    _, evec = np.linalg.eigh(cov)
    s = P @ evec[:, -1]
    out.append(s > _wpercentile(s, w, 50))
    return [[members[m], members[~m]] for m in out]


def _merge_crumbs(halves, adj, W, sub_min) -> list[np.ndarray]:
    """Connected pieces of a cut, with crumbs under `sub_min` (noise along the
    cut line) handed to the bigger piece they touch most."""
    nfc = len(W)
    lab = np.full(nfc, -1, dtype=np.int64)
    pieces = []
    for h in halves:
        m = np.zeros(nfc, dtype=bool)
        m[h] = True
        pieces += _pieces(adj, m)
    for i, p in enumerate(pieces):
        lab[p] = i
    inside = (lab[adj[:, 0]] >= 0) & (lab[adj[:, 1]] >= 0) & (lab[adj[:, 0]] != lab[adj[:, 1]])
    e = adj[inside]
    for _ in range(len(pieces)):
        area = np.bincount(lab[lab >= 0], weights=W[lab >= 0], minlength=len(pieces))
        small = [i for i in range(len(pieces)) if 0 < area[i] < sub_min]
        if not small:
            break
        changed = False
        for i in sorted(small, key=lambda i: area[i]):
            a, b = lab[e[:, 0]], lab[e[:, 1]]
            nb = np.concatenate([b[a == i], a[b == i]])
            nb = nb[(nb != i) & (area[nb] >= area[i])]
            if len(nb) == 0:
                continue
            j = int(np.bincount(nb).argmax())
            lab[lab == i] = j
            area[j] += area[i]
            area[i] = 0
            changed = True
        if not changed:
            break
    return [np.flatnonzero(lab == i) for i in np.unique(lab[lab >= 0])]


def _fit_chart(members, verts, faces, W, normals, *, stiffness, tol, cap):
    fmask = np.zeros(len(W), dtype=bool)
    fmask[members] = True
    vidx, wv, _ = _area_vertices(faces, W, fmask)
    pts = verts[vidx]
    hint = np.average(normals[members], axis=0, weights=W[members])
    hint = None if float(np.linalg.norm(hint)) < 0.2 else hint / np.linalg.norm(hint)
    fitted = fit_spline_patch(pts, wv, stiffness=stiffness, normal_hint=hint,
                              tol=tol, cap=cap)
    return fmask, vidx, pts, fitted


def split_curve(members, verts, faces, C, Ns, W, adj, normals, *, stiffness, tol,
                cap, sub_min, depth=0, fitted=None, guides=None,
                guide_min: float | None = None) -> list[tuple]:
    """A stiff patch, cut in two only while that makes a half pass.

    `guides` are ring axes (find_capped_rings): a cut around one of them is
    tried too, and its pieces need only `guide_min` mm2 (the minimum patch),
    since the cut follows a real round feature rather than the middle of the
    patch. Same stiff spline, same 95% rule, same helps test.

    Returns (members, fmask, vidx, pts, fitted, depth) per piece kept."""
    fm, vidx, pts, fit0 = _fit_chart(members, verts, faces, W, normals,
                                     stiffness=stiffness, tol=tol, cap=cap)
    if fit0 is None:
        return []
    whole = [(members, fm, vidx, pts, fit0, depth)]
    gmin_ = sub_min if guide_min is None else guide_min
    if fit0["within_tol"] or depth >= SPLIT_MAX_DEPTH \
            or float(W[members].sum()) < 2 * min(sub_min, gmin_):
        return whole
    best = None
    gmin = sub_min if guide_min is None else guide_min
    cuts = [(h, sub_min) for h in _bisections(members, C, Ns, W)]
    cuts += [(h, gmin) for h in _guide_cuts(members, C, guides)]
    for halves, pmin in cuts:
        pieces = _merge_crumbs(halves, adj, W, pmin)
        if len(pieces) < 2 or any(float(W[p].sum()) < pmin for p in pieces):
            continue
        fits = [_fit_chart(p, verts, faces, W, normals, stiffness=stiffness,
                           tol=tol, cap=cap) for p in pieces]
        if any(f[3] is None for f in fits):
            continue
        ok = sum(float(W[p].sum()) for p, f in zip(pieces, fits) if f[3]["within_tol"])
        worst = max(f[3]["judged"]["p95_mm"] for f in fits)
        helps = ok > 0 or worst <= SPLIT_HALF_GAIN * fit0["judged"]["p95_mm"]
        if helps and (best is None or (ok, -worst) > best[0]):
            best = ((ok, -worst), pieces, fits)
    if best is None:
        return whole
    out = []
    for p, f in zip(best[1], best[2]):
        if f[3]["within_tol"]:
            out.append((p, f[0], f[1], f[2], f[3], depth + 1))
        else:
            out += split_curve(p, verts, faces, C, Ns, W, adj, normals,
                               stiffness=stiffness, tol=tol, cap=cap,
                               sub_min=sub_min, depth=depth + 1, guides=guides,
                               guide_min=guide_min)
    return out


def _worst_pair(areas: list[dict]) -> tuple[dict | None, dict | None]:
    """Raw-p95 worst area, and the worst area by the smoothed pass check."""
    worst = worst_j = None
    for a in areas:
        raw, judged = a["final"], a["judged"]
        item = {"area": a["id"], "type": a["type"], "kind": a["kind"],
                "p95_mm": raw["p95_mm"], "max_mm": raw["max_mm"],
                "rms_mm": raw["rms_mm"], "judged_p95_mm": judged["p95_mm"]}
        jitem = {"area": a["id"], "type": a["type"], "kind": a["kind"],
                 "judged_p95_mm": judged["p95_mm"], "p95_mm": raw["p95_mm"],
                 "max_mm": raw["max_mm"], "rms_mm": raw["rms_mm"]}
        if worst is None or item["p95_mm"] > worst["p95_mm"]:
            worst = item
        if worst_j is None or jitem["judged_p95_mm"] > worst_j["judged_p95_mm"]:
            worst_j = jitem
    return worst, worst_j


# == the stage ================================================================

def choose_tolerance(extents, nf: float, tol: float | None) -> dict:
    longest = float(max(extents))
    small = longest <= SMALL_PART_MM
    band = BAND_SMALL if small else BAND_LARGE
    band_name = (f"small machined part ({band[0]}-{band[1]} mm)" if small
                 else f"large object ({band[0]}-{band[1]} mm)")
    if tol is not None:
        return {"value_mm": float(tol), "band": band_name, "band_mm": list(band),
                "set_by": "user",
                "in_band": bool(band[0] <= tol <= band[1]),
                "reason": "given on the command line"}
    val = float(np.clip(TOL_NOISE_FACTOR * nf, *band))
    return {"value_mm": round(val, 4), "band": band_name, "band_mm": list(band),
            "set_by": "default",
            "in_band": True,
            "reason": (f"longest side {longest:.1f} mm -> {band_name}; "
                       f"{TOL_NOISE_FACTOR:g} x measured noise "
                       f"{nf:.4f} mm, clamped to the band")}


def _group_directions(ents: list[dict]) -> list[dict]:
    """Cluster nearly parallel directions, then make the clusters exact.

    Heaviest cluster first. Each cluster's direction becomes exactly a frame
    axis when it is that close to one (the frame was built from these same
    faces), otherwise it is made exactly square to every earlier cluster it
    is nearly square to.
    """
    cos_p = np.cos(np.radians(SNAP_ANGLE_DEG))
    sin_q = np.sin(np.radians(SNAP_ANGLE_DEG))
    groups: list[dict] = []
    for e in sorted(ents, key=lambda e: -e["w"]):
        for g in groups:
            c = _unit(g["vec"])
            dot = float(e["dir"] @ c)
            if abs(dot) >= cos_p:
                s = 1.0 if dot > 0 else -1.0
                g["vec"] = g["vec"] + s * e["w"] * e["dir"]
                g["members"].append(e["id"])
                break
        else:
            groups.append({"vec": e["w"] * e["dir"], "members": [e["id"]]})
    groups.sort(key=lambda g: -np.linalg.norm(g["vec"]))

    fixed: list[np.ndarray] = []
    for gi, g in enumerate(groups):
        d = _unit(g["vec"])
        near = [f for f in fixed if abs(float(d @ f)) <= sin_q]
        rel = []
        for e in np.eye(3):
            if abs(float(d @ e)) >= cos_p and all(abs(float(e @ f)) < 1e-12 for f in near):
                d = e * np.sign(float(d @ e))
                rel.append(f"exactly on the {'XYZ'[int(np.argmax(np.abs(e)))]} axis")
                break
        else:
            if near:
                Q, _ = np.linalg.qr(np.array(near).T)
                d2 = d - Q @ (Q.T @ d)
                if np.linalg.norm(d2) > 1e-6:
                    d = _unit(d2)
        if near:
            rel.append(f"square to {len(near)} other direction group(s)")
        if len(g["members"]) > 1:
            rel.append(f"parallel across {len(g['members'])} areas")
        g["dir"], g["relation"], g["index"] = d, rel, gi
        fixed.append(d)
    return groups


def run_fit(mesh_path: Path, frame_path: Path, out_dir: Path, *,
            tol: float | None = None, units: str = "auto",
            preview: bool = True) -> dict:
    """Fit, snap and report. Writes the report even when the size check stops."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "30_fit.json"

    frame = Frame.load(frame_path)
    R = frame.R
    rigid_err = float(np.abs(R @ R.T - np.eye(3)).max())
    if rigid_err > 1e-6 or np.linalg.det(R) < 0:
        raise ValueError(f"frame rotation is not rigid (error {rigid_err:.2e}); "
                         "refusing - the scan must never be rescaled")

    src = trimesh.load(mesh_path, force="mesh", process=False)
    verts = frame.to_canonical(np.asarray(src.vertices, float))
    mesh = trimesh.Trimesh(vertices=verts, faces=np.asarray(src.faces), process=False)
    if mesh.is_watertight and mesh.volume < 0:
        mesh.invert()

    planes, cyls, nf, from_holes, rejected_rounds, noise_info = _detect(mesh)
    ext = mesh.bounds[1] - mesh.bounds[0]
    tinfo = choose_tolerance(ext, nf, tol)
    T = tinfo["value_mm"]

    total_area = float(mesh.area)
    min_patch = max(MIN_PATCH_MM2, MIN_PATCH_FRAC * total_area)
    label_dist = max(LABEL_NOISE_FACTOR * nf, T)
    # A hole's wall scatters more than a flat face (the hole finder measured
    # 0.13-0.21 mm rms on the pedal adapter's holes against 0.09 mm face
    # noise), so each hole from the hole finder joins faces within
    # LABEL_NOISE_FACTOR x its OWN measured rms when that is wider. With the
    # face-noise join distance alone (0.28 mm) the d5.1 and d5.8 walls fell
    # just under the minimum patch and both holes were lost. Faces must still
    # face the hole's axis, and the area is still judged against the
    # tolerance at the 95th percentile.
    hole_dist = {len(planes) + j: max(label_dist, LABEL_NOISE_FACTOR * float(c.rms))
                 for j, c in enumerate(cyls) if from_holes[j]}
    lab, patches = label_faces(mesh, planes, cyls, label_dist=label_dist,
                               min_patch=min_patch, own_dist=hole_dist)

    # ---- per-area least-squares fits ------------------------------------
    prims = [("plane", p) for p in planes] + [("cyl", c) for c in cyls]
    faces = np.asarray(mesh.faces)
    N = face_normals_smoothed(mesh)
    C = np.asarray(mesh.triangles_center, float)
    farea = np.asarray(mesh.area_faces, float)
    rng = np.random.default_rng(0)
    areas: list[dict] = []
    remap = np.full(len(prims), -1)
    adj = np.asarray(mesh.face_adjacency)

    def fit_one(kind, g, fmask):
        pts = verts[np.unique(faces[fmask])]
        if kind == "plane":
            n, d, _ = refine_plane(pts)
            if float(n @ np.asarray(g.normal, float)) < 0:
                n, d = -n, -d
            return pts, {"n": n, "d": float(d)}, plane_residual(C, n, float(d))
        fp = pts if len(pts) <= FIT_POINT_CAP else pts[rng.choice(len(pts), FIT_POINT_CAP, replace=False)]
        ax, p, r = fit_cylinder(fp, g.axis, g.point, g.radius)
        return pts, {"a": ax, "p": p, "r": r}, cyl_residual(C, ax, p, r)

    trimmed_total = 0.0
    flat_lim = flat_off_limit(nf, T, floor=tinfo["band_mm"][0])
    flat_log: list[dict] = []
    flat_dropped_total = 0.0
    for i in sorted(patches, key=lambda i: -farea[lab == i].sum()):
        kind, g = prims[i]
        fmask = lab == i
        area0 = float(farea[fmask].sum())
        pts, prm, res_face = fit_one(kind, g, fmask)
        # Edge bands: faces along the border that belong to the next surface
        # (rounded edges, rib feet). Taken out and the area refitted, up to
        # EDGE_BAND_PASSES times; they go back to "other" and are reported.
        trimmed = np.zeros(len(fmask), dtype=bool)
        for _ in range(EDGE_BAND_PASSES):
            band = edge_bands(mesh, fmask, res_face, T, adj, pinhole_mm2=min_patch)
            if not band.any() or float(farea[fmask & ~band].sum()) < EDGE_BAND_KEEP_FRAC * area0:
                break
            fmask = fmask & ~band
            trimmed |= band
            pts, prm, res_face = fit_one(kind, g, fmask)
        lab[trimmed] = -1
        trimmed_total += float(farea[trimmed].sum())
        if kind == "plane":
            # Flat check (FLAT_*): faces whose surroundings are not on the
            # plane go to "other" and the plane is refitted; then the area
            # as a whole must not bend away from flat.
            dropped = np.zeros(len(fmask), dtype=bool)
            for _ in range(FLAT_PASSES):
                off = flat_off_faces(verts, faces, C, N, farea, fmask, prm["n"],
                                     prm["d"], limit=flat_lim)
                off |= small_pieces(adj, fmask & ~off, farea, min_patch)
                if not off.any():
                    break
                fmask = fmask & ~off
                dropped |= off
                if float(farea[fmask].sum()) < min_patch:
                    break
                pts, prm, res_face = fit_one(kind, g, fmask)
            lab[dropped] = -1
            kept_area = float(farea[fmask].sum())
            bend = (flat_bend(verts, faces, farea, fmask, prm["n"])
                    if kept_area >= min_patch
                    else {"bend_p95_mm": None, "radii_mm": None, "n_points": 0})
            why = None
            if kept_area < min_patch:
                why = (f"only {kept_area:.1f} mm2 of it sits on a plane "
                       f"(minimum patch {min_patch:.1f} mm2)")
            elif bend["bend_p95_mm"] > flat_lim:
                why = (f"it bends {bend['bend_p95_mm']:.3f} mm off flat (95% of the "
                       f"area; limit {flat_lim:.3f} mm)")
            if dropped.any() or why:
                flat_log.append({"normal": [round(float(x), 4) for x in prm["n"]],
                    "area_mm2_before": round(
                    float(farea[fmask | dropped].sum()), 2),
                    "dropped_mm2": round(float(farea[dropped].sum()), 2),
                    **bend, "rejected": why is not None, "why": why})
            flat_dropped_total += float(farea[dropped].sum())
            if why is not None:
                lab[fmask] = -1
                flat_dropped_total += kept_area
                continue
        a = {"id": len(areas), "n_faces": int(fmask.sum()),
             "area_mm2": round(float(farea[fmask].sum()), 2),
             "n_patches": patches[i], "_pts": pts, "_fmask": fmask, "snaps": []}
        if kind == "plane" and dropped.any():
            a["flat_check_dropped"] = {"faces": int(dropped.sum()),
                                       "area_mm2": round(float(farea[dropped].sum()), 2),
                                       "note": "faces whose surroundings sit off the plane "
                                               "or lean away from it - a curve, now 'other'"}
        if trimmed.any():
            a["edge_band_trimmed"] = {"faces": int(trimmed.sum()),
                                      "area_mm2": round(float(farea[trimmed].sum()), 2),
                                      "note": "border faces more than the tolerance off, "
                                              "on one side - the next surface, now 'other'"}
        if kind == "plane":
            n, d = prm["n"], prm["d"]
            a.update(type="flat", kind="plane", _n=n, _d=float(d))
            a["fit"] = {"normal": [round(float(x), 6) for x in n],
                        "offset_mm": round(float(d), 4),
                        **_stats(plane_residual(pts, n, d))}
        else:
            ax, p, r = prm["a"], prm["p"], prm["r"]
            # Round check on the area's own faces, against its own fit. The
            # hole finder's holes have passed it already; anything from the
            # circle search that fails goes back to "other".
            if not from_holes[i - len(planes)]:
                ev = round_evidence(C, N, farea, ax, p, r, band=np.inf, mask=fmask)
                ev["rms_mm"] = round(float(np.sqrt(np.mean(cyl_residual(pts, ax, p, r) ** 2))), 5)
                why = round_check(ev, nf)
                if why is not None:
                    lab[fmask | trimmed] = -1
                    trimmed_total -= float(farea[trimmed].sum())
                    rejected_rounds.append({
                        "stage": "area", "diameter_mm": round(2 * r, 3),
                        "axis": [round(float(x), 4) for x in ax],
                        "faces": int(fmask.sum()), **ev, "why": why})
                    continue
            rel = C[fmask] - p
            perp = rel - np.outer(rel @ ax, ax)
            uhat = perp / np.maximum(np.linalg.norm(perp, axis=1), 1e-12)[:, None]
            outward = float(np.average(np.einsum("ij,ij->i", N[fmask], uhat),
                                       weights=farea[fmask]))
            along = pts @ ax
            a.update(type="round", kind="boss" if outward > 0 else "hole",
                     _a=ax, _p=p, _r=r)
            a["fit"] = {"axis": [round(float(x), 6) for x in ax],
                        "point_mm": [round(float(x), 4) for x in p],
                        "diameter_mm": round(2 * r, 4),
                        "length_mm": round(float(along.max() - along.min()), 3),
                        **_stats(cyl_residual(pts, ax, p, r))}
        remap[i] = a["id"]
        areas.append(a)
    area_lab = np.where(lab >= 0, remap[np.maximum(lab, 0)], -1)

    # ---- snapping 1: parallel / square directions ------------------------
    ents = []
    for a in areas:
        dvec = a["_n"] if a["type"] == "flat" else a["_a"]
        ents.append({"id": a["id"], "dir": dvec, "w": a["area_mm2"]})
    groups = _group_directions(ents)
    by_id = {a["id"]: a for a in areas}
    dir_snapped, dir_rejected = 0, []
    group_out = []
    for g in groups:
        accepted = []
        for mid in g["members"]:
            a = by_id[mid]
            pts = a["_pts"]
            if a["type"] == "flat":
                n_new = g["dir"] if float(g["dir"] @ a["_n"]) > 0 else -g["dir"]
                if float(n_new @ a["_n"]) >= 1 - 1e-15:
                    accepted.append(mid)
                    continue
                d_new = float(np.mean(pts @ n_new))
                move = float(np.abs(plane_residual(pts, n_new, d_new)
                                    - plane_residual(pts, a["_n"], a["_d"])).max())
                if move <= T:
                    a["_n"], a["_d"] = n_new, d_new
                    a["snaps"].append(f"direction made exact ({'; '.join(g['relation']) or 'own'}),"
                                      f" moved {move:.4f} mm")
                    dir_snapped += 1
                    accepted.append(mid)
                else:
                    dir_rejected.append({"area": mid, "would_move_mm": round(move, 4)})
            else:
                a_new = g["dir"] if float(g["dir"] @ a["_a"]) > 0 else -g["dir"]
                if float(a_new @ a["_a"]) >= 1 - 1e-15:
                    accepted.append(mid)
                    continue
                p_new, r_new = fit_circle_fixed_axis(pts, a_new, a["_p"])
                move = float(np.abs(cyl_residual(pts, a_new, p_new, r_new)
                                    - cyl_residual(pts, a["_a"], a["_p"], a["_r"])).max())
                if move <= T:
                    a["_a"], a["_p"], a["_r"] = a_new, _axis_foot(a_new, p_new, pts.mean(0)), r_new
                    a["snaps"].append(f"axis made exact ({'; '.join(g['relation']) or 'own'}),"
                                      f" moved {move:.4f} mm")
                    dir_snapped += 1
                    accepted.append(mid)
                else:
                    dir_rejected.append({"area": mid, "would_move_mm": round(move, 4)})
        group_out.append({"direction": [round(float(x), 6) for x in g["dir"]],
                          "relation": g["relation"], "areas": g["members"],
                          "snapped": accepted})

    # ---- snapping 2: coaxial (concentric / collinear) round areas --------
    rounds = [a for a in areas if a["type"] == "round"]
    cos_p = np.cos(np.radians(SNAP_ANGLE_DEG))
    cand = max(COAX_CANDIDATE_MM, 5 * T)
    parent = list(range(len(rounds)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(rounds)):
        for j in range(i + 1, len(rounds)):
            ai, aj = rounds[i], rounds[j]
            if abs(float(ai["_a"] @ aj["_a"])) < cos_p:
                continue
            dp = aj["_p"] - ai["_p"]
            off = np.linalg.norm(dp - (dp @ ai["_a"]) * ai["_a"])
            if off <= cand:
                parent[find(i)] = find(j)
    clusters: dict[int, list] = {}
    for i in range(len(rounds)):
        clusters.setdefault(find(i), []).append(rounds[i])
    coax_out = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        ref = members[0]["_a"]
        w = np.array([m["area_mm2"] for m in members])
        avec = sum(wi * (m["_a"] if m["_a"] @ ref > 0 else -m["_a"])
                   for wi, m in zip(w, members))
        ax = _unit(avec)
        # weighted mean of the axis positions, in the plane square to the axis
        ps = np.array([m["_p"] - (m["_p"] @ ax) * ax for m in members])
        p = (w[:, None] * ps).sum(0) / w.sum()
        ok = []
        for m in members:
            pts = m["_pts"]
            a_new = ax if ax @ m["_a"] > 0 else -ax
            r_new = float(np.mean(np.linalg.norm(
                (pts - p) - np.outer((pts - p) @ a_new, a_new), axis=1)))
            move = float(np.abs(cyl_residual(pts, a_new, p, r_new)
                                - cyl_residual(pts, m["_a"], m["_p"], m["_r"])).max())
            m["_coax_try"] = (a_new, p, r_new, move)
            if move <= T:
                ok.append(m)
        if len(ok) >= 2:
            for m in ok:
                a_new, p0, r_new, move = m.pop("_coax_try")
                m["_a"], m["_p"], m["_r"] = a_new, _axis_foot(a_new, p0, m["_pts"].mean(0)), r_new
                m["snaps"].append(f"made exactly coaxial with areas "
                                  f"{[o['id'] for o in ok if o is not m]}, moved {move:.4f} mm")
        for m in members:
            m.pop("_coax_try", None)
        coax_out.append({"areas": [m["id"] for m in members],
                         "snapped": [m["id"] for m in ok] if len(ok) >= 2 else [],
                         "axis": [round(float(x), 6) for x in ax],
                         "point_mm": [round(float(x), 4) for x in p]})

    # ---- snapping 3: hole sizes to the chosen table ----------------------
    holes = [a for a in areas if a["kind"] == "hole"]
    guess, guess_why = guess_units([2 * a["_r"] for a in holes])
    if units not in ("auto", "metric", "inch"):
        raise ValueError(f"units must be auto, metric or inch, not {units!r}")
    table = guess if units == "auto" else units
    size_snaps = []
    for a in areas:
        if a["type"] != "round":
            continue
        d_now = 2 * a["_r"]
        if a["kind"] == "hole":
            d_std = snap_hole(d_now, table, T)
            if d_std is not None:
                move = abs(d_std - d_now) / 2
                a["_r"] = d_std / 2
                a["snaps"].append(f"diameter {d_now:.4f} -> {d_std:g} mm ({table}), "
                                  f"moved {move:.4f} mm")
                a["standard_size"] = {"table": table, "diameter_mm": d_std}
                size_snaps.append({"area": a["id"], "from_mm": round(d_now, 4),
                                   "to_mm": round(d_std, 4)})
            else:
                a["standard_size"] = {"table": table, "diameter_mm": None,
                                      "nearest_mm": round(nearest_size(d_now, table), 4),
                                      "why_not": "more than the tolerance away"}
        else:
            a["standard_size"] = {"table": table, "nearest_mm": round(nearest_size(d_now, table), 4),
                                  "note": "bosses are reported, not snapped"}

    # ---- final errors against the averaged scan --------------------------
    model_pts = verts.copy()
    worst = None
    worst_judged = None
    tex_cap = texture_limit(nf)
    for a in areas:
        pts = a["_pts"]
        vidx, wv, _ = _area_vertices(faces, farea, a["_fmask"])
        if a["type"] == "flat":
            res = plane_residual(pts, a["_n"], a["_d"])
            model_pts[vidx] = pts - np.outer(res, a["_n"])
            a["final"] = {"normal": [round(float(x), 9) for x in a["_n"]],
                          "offset_mm": round(a["_d"], 4), **_stats(res)}
        else:
            res = cyl_residual(pts, a["_a"], a["_p"], a["_r"])
            rel = pts - a["_p"]
            perp = rel - np.outer(rel @ a["_a"], a["_a"])
            uhat = perp / np.maximum(np.linalg.norm(perp, axis=1), 1e-12)[:, None]
            model_pts[vidx] = pts - res[:, None] * uhat
            a["final"] = {"axis": [round(float(x), 9) for x in a["_a"]],
                          "point_mm": [round(float(x), 4) for x in a["_p"]],
                          "diameter_mm": round(2 * a["_r"], 4), **_stats(res)}
        # Pass check (PASS_SMOOTH_*): the 95% rule on the texture-smoothed
        # copy of these distances. model_pts above are the fitted surface;
        # the smoothed copy goes nowhere but this comparison.
        pc = pass_check(pts, wv, res, tol=T, cap=tex_cap,
                        axis=a.get("_a"), point=a.get("_p"))
        a["_vidx"], a["_jres"] = vidx, pc["residual"]
        a["judged"] = pc["stats"]
        a["within_tol_raw"] = bool(a["final"]["p95_mm"] <= T)
        a["within_tol"] = a["judged"]["within_tol"]
        if worst is None or a["final"]["p95_mm"] > worst["p95_mm"]:
            worst = {"area": a["id"], "type": a["type"], "kind": a["kind"],
                     "p95_mm": a["final"]["p95_mm"], "max_mm": a["final"]["max_mm"],
                     "rms_mm": a["final"]["rms_mm"],
                     "judged_p95_mm": a["judged"]["p95_mm"]}
        if worst_judged is None or a["judged"]["p95_mm"] > worst_judged["judged_p95_mm"]:
            worst_judged = {"area": a["id"], "type": a["type"], "kind": a["kind"],
                            "judged_p95_mm": a["judged"]["p95_mm"],
                            "p95_mm": a["final"]["p95_mm"],
                            "max_mm": a["final"]["max_mm"],
                            "rms_mm": a["final"]["rms_mm"]}

    # Freeform (plan part 4): stiff splines on what flat and round left as
    # "other". Same 95% check. Not part of the size-check model. Stiffness
    # stays at the proposed stiff end even when a patch misses.
    # A patch that misses is split into the flats, rounds and simpler
    # stiff curves it really holds (SPLIT_*), never loosened.
    free_meta = assign_freeform(
        mesh, verts, faces, farea, N, area_lab, areas,
        nf=nf, tol=T, min_patch=min_patch, label_dist=label_dist,
        flat_lim=flat_lim, directions=[g["dir"] for g in groups], table=table)
    # Unfitted faces join the surface they continue (as fitted).
    scrap_meta = fold_scraps(verts, faces, C, N, farea, adj, area_lab, areas, tol=T,
                             cap=tex_cap, min_patch=min_patch, flat_lim=flat_lim)
    free_meta["covered_area_frac_after_scrap_fold"] = round(
        float(farea[area_lab >= 0].sum()) / total_area, 4)
    worst, worst_judged = _worst_pair(areas)

    # ---- parallel facing pairs: the part's measured thicknesses ----------
    pairs = []
    flats = [a for a in areas if a["type"] == "flat"]
    for i in range(len(flats)):
        for j in range(i + 1, len(flats)):
            ni, nj = flats[i]["_n"], flats[j]["_n"]
            if float(ni @ nj) <= -cos_p:
                dist = flats[i]["_d"] + flats[j]["_d"] if float(ni @ nj) <= -1 + 1e-12 \
                    else float(np.mean(flats[j]["_pts"] @ (-ni))) + flats[i]["_d"]
                pairs.append({"areas": [flats[i]["id"], flats[j]["id"]],
                              "distance_mm": round(abs(dist), 4),
                              "exactly_parallel": bool(float(ni @ nj) <= -1 + 1e-12)})
    pairs.sort(key=lambda p: -p["distance_mm"])

    # ---- outputs -------------------------------------------------------
    labels_path = out_dir / "30_labels.npy"
    np.save(labels_path, area_lab.astype(np.int32))
    png = out_dir / "30_areas.png"
    if preview:
        render_area_map(mesh, area_lab, areas, png, tol=T)

    other_area = float(farea[area_lab < 0].sum())
    n_flat = sum(a["type"] == "flat" for a in areas)
    n_round = sum(a["type"] == "round" for a in areas)
    n_free = sum(a["type"] == "freeform" for a in areas)
    snapped_areas = sum(bool(a["snaps"]) for a in areas)
    report = {
        "stage": "fit",
        "plan": "docs/SURFACE_FIT_PLAN.md parts 3 and 4 - fitting only, no trimming or knitting",
        "surface": str(mesh_path),
        "frame": str(frame_path),
        "measured_against": "averaged scan surface (stage 10 Poisson surface)",
        "scale_applied": 1.0,
        "scale_locked": True,
        "transform": "rigid rotation + translation from stage 20 only",
        "frame_rigid_error": rigid_err,
        "noise_floor_mm": round(nf, 5),
        "noise": noise_info,
        "tolerance": tinfo,
        "within_tol_rule": "an area is within tolerance when the 95th percentile "
                           "of |distance| from the averaged scan to its surface "
                           "is at most the tolerance; the distances compared are "
                           "smoothed over the area's own points to take out scan "
                           "texture (see pass_check)",
        "pass_check": {
            "rule": (f"each area's signed distances are averaged over its own "
                     f"points within {PASS_SMOOTH_MM:g} mm (holes and bosses: along "
                     f"the axis, {ROUND_ARC_SQUEEZE:g}x shorter around the turn, "
                     f"so a D or an oval is kept whole), never "
                     f"across into another area; a point the smoothing would move "
                     f"by more than {tex_cap:.3f} mm ({TEXTURE_NOISE_FACTOR:g} x "
                     f"noise) is a real feature and keeps "
                     f"its raw distance; then 95% of points must lie within the "
                     f"tolerance. Only this test sees the smoothed copy - fits, "
                     f"snaps, size check and model use the fitted surfaces."),
            "smooth_mm": PASS_SMOOTH_MM,
            "texture_limit_mm": round(tex_cap, 5),
            "fraction": 0.95,
        },
        "label_distance_mm": round(label_dist, 4),
        "hole_label_distance_mm": sorted(round(v, 4) for v in hole_dist.values()),
        "units": {"choice": units, "table": table, "guess": guess, "guess_detail": guess_why,
                  "note": "the unit setting only picks the hole-size table; "
                          "nothing is scaled"},
        "faces": {"total": int(len(faces)), "labelled": int((area_lab >= 0).sum()),
                  "other": int((area_lab < 0).sum()),
                  "other_area_frac": round(other_area / total_area, 4),
                  "edge_band_trimmed_mm2": round(trimmed_total, 2),
                  "flat_check_dropped_mm2": round(flat_dropped_total, 2)},
        "summary": {
            "n_areas": len(areas), "n_flat": int(n_flat), "n_round": int(n_round),
            "n_freeform": int(n_free),
            "n_blend": sum(a["type"] == "blend" for a in areas),
            "n_by_kind": {
                "flat": int(n_flat),
                "hole": sum(a["kind"] == "hole" for a in areas),
                "boss": sum(a["kind"] == "boss" for a in areas),
                "fillet": sum(a["kind"] == "fillet" for a in areas),
                "partial_round": sum(bool(a.get("partial")) for a in areas),
                "capped_ring": sum(bool(a.get("capped_ring")) for a in areas),
                "stud_post": sum(bool(a.get("stud_post")) for a in areas),
                "level_blend": sum(a["type"] == "blend" for a in areas),
                "curve": int(n_free)},
            "covered_area_frac": round(float(farea[area_lab >= 0].sum()) / total_area, 4),
            "uncovered_area_frac": round(other_area / total_area, 4),
            "n_holes": len(holes),
            "n_rounds_rejected": len(rejected_rounds),
            "n_flats_rejected": sum(1 for f in flat_log if f["rejected"]),
            "n_areas_snapped": int(snapped_areas),
            "n_direction_snaps": dir_snapped,
            "n_direction_snaps_refused": len(dir_rejected),
            "n_coaxial_groups": sum(1 for c in coax_out if c["snapped"]),
            "n_hole_sizes_snapped": len(size_snaps),
            "n_within_tol": int(sum(a["within_tol"] for a in areas)),
            "n_within_tol_raw": int(sum(a["within_tol_raw"] for a in areas)),
            "worst_area": worst,
            "worst_area_judged": worst_judged,
        },
        "round_check": {
            "rule": (f"a round from the circle search is kept only when the faces "
                     f"on it that face along its radius cover at least "
                     f"{ROUND_MIN_COVERAGE * 100:.0f}% of the turn and fit within "
                     f"{ROUND_MAX_RMS_NOISE:g} x noise "
                     f"({ROUND_MAX_RMS_NOISE * nf:.3f} mm); checked on each "
                     f"candidate and again on each area after its own fit. "
                     f"Holes pass the same test in the hole finder."),
            "rejected": rejected_rounds,
        },
        "flat_check": {
            "rule": (f"a face stays on a flat area only when the area's faces "
                     f"within {FLAT_SMOOTH_MM:g} mm of it sit within "
                     f"{flat_lim:.3f} mm of the plane on average "
                     f"({FLAT_OFF_NOISE_FACTOR:g} x noise, at least the low end "
                     f"of the tolerance range, never more than the "
                     f"tolerance) and lean less than {FLAT_MAX_TILT_DEG:g} deg off "
                     f"it; the area as a whole is a flat only when its best "
                     f"second-order surface bends no more than {flat_lim:.3f} mm "
                     f"off a plane over 95% of it. Everything else is 'other'."),
            "limit_mm": round(flat_lim, 5),
            "areas": flat_log,
        },
        "freeform": free_meta,
        "scrap_fold": scrap_meta,
        "snaps": {"direction_groups": group_out, "direction_refused": dir_rejected,
                  "coaxial": coax_out, "hole_sizes": size_snaps},
        "parallel_pairs": pairs,
        "areas": [{k: v for k, v in a.items() if not k.startswith("_")} for a in areas],
        "labels": str(labels_path),
        "preview": str(png) if preview else None,
    }

    me, se = slab_extents(verts, model_pts, band=T)
    stopped = None
    try:
        report["size_check"] = check_size(me, se, T)
        report["status"] = "OK"
    except SizeCheckError as exc:
        report["size_check"] = json.loads(str(exc))
        report["status"] = "STOPPED"
        stopped = report["size_check"]["message"]

    # Anything that did not turn out right gets pictures (the user's standing
    # request): the whole part as a deviation map, and a close-up per area.
    bad = [a for a in areas if not a["within_tol"]]
    report["review"] = []
    has_free = any(a["type"] == "freeform" for a in areas)
    if preview and (bad or stopped or has_free):
        report["review"] = render_review(mesh, faces, verts, areas, area_lab, bad,
                                         out_dir / "review", tol=T, stopped=stopped)
    if preview:
        n_in = int(sum(a["within_tol"] for a in areas))
        fv = fitted_vertices(verts, faces, areas, area_lab)
        report["shaded"] = [str(render_fitted_shaded(
            mesh, verts, faces, areas, area_lab, out_dir / "30_fitted_shaded.png",
            fitted=fv,
            title=(f"Fitted surfaces, shaded ({len(areas)} areas, {n_in} within "
                   f"{T} mm; {report['summary']['covered_area_frac'] * 100:.1f}% covered)")))]
        studs = [a for a in areas if a.get("stud_post")]
        if studs:
            st0 = max(studs, key=lambda a: a["area_mm2"])
            report["shaded"].append(str(render_fitted_shaded(
                mesh, verts, faces, areas, area_lab, out_dir / "30_fitted_closeup_stud.png",
                fitted=fv, focus=st0["_pts"].mean(0), focus_mm=9.0, focus_axis=st0["_a"],
                title=f"Close-up: stud post {st0['id']} "
                      f"(d{st0['final']['diameter_mm']:g} mm), fitted surfaces shaded")))
    report_path.write_text(json.dumps(report, indent=2))
    if stopped:
        raise SizeCheckError(stopped)
    report["report"] = str(report_path)
    return report


# == short capped rings =========================================================
# The partial-round finder wants an arc of at least min_patch (30 mm2 on the
# pedal adapter) whose faces face along the radius within LABEL_ANGLE_DEG. A
# short boss, a counterbore or a spot-face wall 1-2 mm tall is all turn and
# no length: its whole wall is under the minimum patch, and the smoothed
# normals on a wall that short lean toward its top and floor. Such a ring is
# accepted here, with evidence a short wavy band cannot fake:
#
# - its axis is FIXED to one of the part's directions or an existing round's
#   axis (round_axes), never fitted;
# - it goes most of the way round (CAPPED_RING_MIN_COVERAGE of the turn);
# - it fits a constant radius within the round check's noise multiple
#   (ROUND_MAX_RMS_NOISE x noise rms);
# - BOTH ends along the axis are capped by a flat square to the axis: of the
#   faces just past each end (within SPLIT_EDGE_RING_MM), at least
#   CAPPED_RING_CAP_SHARE by area is a fitted flat square to the axis or a
#   face within FLAT_MAX_TILT_DEG of square to it.
#
# An unfitted cap (the top of a short boss, the floor of a counterbore) is
# fitted as a flat with its normal exactly the ring's axis, through the same
# flat-off check as every flat, down to FILLET_MIN_MM2. The ring and its caps
# are judged by the 95% rule like every area and reported outside tolerance
# when they miss. Tolerance, stiffness and the 95% rule are untouched; like
# every split piece they are measured only, not moved into the size check.
#
# A ring that passes everything except the caps is not accepted. It is kept
# as a cut guide only: a stiff patch that misses may be cut in two around
# that axis (see split_curve), and each piece is then judged exactly like
# any other stiff patch.
CAPPED_RING_FACING_DEG = 35.0
CAPPED_RING_MIN_COVERAGE = 0.75
CAPPED_RING_MIN_MM2 = MIN_PATCH_MM2
CAPPED_RING_MIN_LEN_MM = 0.5
CAPPED_RING_CAP_SHARE = 0.5
CAPPED_RING_TRIES = 8
CAPPED_RING_GUIDE_STEPS_MM = (1.0, 2.0, 3.0, 4.0, 5.0)


def ring_caps(C, N, W, fm, a, p, r, fitted_square, *, ring=SPLIT_EDGE_RING_MM,
              tilt_deg=FLAT_MAX_TILT_DEG) -> list[dict]:
    """Both ends of a ring along its axis: what lies just past each end.

    For each end (low, high along `a`), the faces outside the ring within
    `ring` mm of it, past that end, and the share (by area) that is a flat
    square to the axis: a fitted one (`fitted_square`) or a face whose
    normal is within `tilt_deg` of the axis. share None: nothing there."""
    a = _unit(a)
    rel = C - p
    along = rel @ a
    alo, ahi = float(along[fm].min()), float(along[fm].max())
    cand = np.flatnonzero(~fm & (((along < alo) & (along >= alo - ring))
                                 | ((along > ahi) & (along <= ahi + ring))))
    close = np.zeros(len(W), dtype=bool)
    if len(cand) and fm.any():
        dist, _ = cKDTree(C[fm]).query(C[cand], distance_upper_bound=ring)
        close[cand[np.isfinite(dist)]] = True
    square = np.abs(N @ a) >= np.cos(np.radians(tilt_deg))
    out = []
    for past in (close & (along < alo), close & (along > ahi)):
        if not past.any():
            out.append({"share": None, "area_mm2": 0.0, "faces": past})
            continue
        ok = fitted_square[past] | square[past]
        out.append({"share": float(W[past][ok].sum() / W[past].sum()),
                    "area_mm2": float(W[past].sum()), "faces": past})
    return out


def _cap_flat(verts, faces, C, N, W, adj, pool, near, a, *, label_dist, flat_lim,
              tol, cap):
    """A flat square to `a` (normal exactly +-a) on the unfitted faces `near`
    the end of a ring, grown over `pool`. None when there is none."""
    a = _unit(a)
    seed = near & pool & (np.abs(N @ a) >= np.cos(np.radians(FLAT_MAX_TILT_DEG)))
    if float(W[seed].sum()) <= 0:
        return None
    n = a if float(np.average(N[seed] @ a, weights=W[seed])) > 0 else -a
    d = _wpercentile(C[seed] @ n, W[seed], 50)
    cos_t = float(np.cos(np.radians(LABEL_ANGLE_DEG)))
    fm = pool & (np.abs(C @ n - d) <= label_dist) & (N @ n >= cos_t)
    touch = np.zeros(len(W), dtype=bool)
    for piece in _pieces(adj, fm):
        if (seed[piece]).any():
            touch[piece] = True
    fm = touch
    for _ in range(FLAT_PASSES):
        if not fm.any():
            return None
        d = float(np.average(verts[np.unique(faces[fm])] @ n))
        off = flat_off_faces(verts, faces, C, N, W, fm, n, d, limit=flat_lim)
        off |= small_pieces(adj, fm & ~off, W, CAPPED_RING_MIN_MM2)
        if not off.any():
            break
        fm = fm & ~off
    if float(W[fm].sum()) < CAPPED_RING_MIN_MM2:
        return None
    vidx, wv, _ = _area_vertices(faces, W, fm)
    pts = verts[vidx]
    d = float(np.average(pts @ n, weights=wv))
    res = plane_residual(pts, n, d)
    pc = pass_check(pts, wv, res, tol=tol, cap=cap)
    st = _stats(res)
    return {"fmask": fm, "n": n, "d": d, "pts": pts, "vidx": vidx, "stats": st, "pc": pc}


def find_capped_rings(verts, faces, C, N, W, adj, pool, area_lab, areas, *, axes, nf,
                      tol, label_dist, flat_lim, cap, table, rng, accept) -> dict:
    """Short rings capped by flats at both ends, on fixed part axes, from `pool`.

    Accepted rings (and their new cap flats) go to `accept(fm, area)` and out
    of `pool`. Returns the log and the cut guides (convincing rings that are
    not capped)."""
    sin_f = float(np.sin(np.radians(CAPPED_RING_FACING_DEG)))
    cos_f = float(np.cos(np.radians(CAPPED_RING_FACING_DEG)))
    log, guides = [], []
    for a in axes:
        a = _unit(a)
        u, v = _perp_basis(a)
        tried = np.zeros(len(W), dtype=bool)
        for _ in range(CAPPED_RING_TRIES):
            wall = pool & ~tried & (np.abs(N @ a) <= sin_f)
            widx = np.flatnonzero(wall)
            if len(widx) < 12 or float(W[widx].sum()) < CAPPED_RING_MIN_MM2:
                break
            xy = np.column_stack([C[widx] @ u, C[widx] @ v])
            nxy = np.column_stack([N[widx] @ u, N[widx] @ v])
            nxy /= np.maximum(np.linalg.norm(nxy, axis=1), 1e-12)[:, None]
            tree = cKDTree(C[widx])
            pw = W[widx] / W[widx].sum()
            best = (-1.0, None, None)
            for sd in rng.choice(len(widx), size=min(SPLIT_SEEDS, len(widx)), replace=False, p=pw):
                nb = tree.query_ball_point(C[widx[sd]], PARTIAL_SAMPLE_MM)
                nb = [k for k in nb if k != sd]
                if len(nb) < 2:
                    continue
                two = rng.choice(nb, 2, replace=False)
                circ = _circle3(xy[[sd, two[0], two[1]]])
                if circ is None:
                    continue
                cx, cy, r = circ
                if r < HOLE_MIN_D_MM / 2 or r > SPLIT_ROUND_MAX_R_MM:
                    continue
                rel = xy - (cx, cy)
                rad = np.maximum(np.linalg.norm(rel, axis=1), 1e-12)
                inl = (np.abs(rad - r) <= label_dist) & (
                    np.abs(np.einsum("ij,ij->i", nxy, rel / rad[:, None])) >= cos_f)
                if not inl.any():
                    continue
                # a ring scores by how much of the turn it covers, not by area
                ang = np.arctan2(rel[inl, 1], rel[inl, 0])
                cov = np.count_nonzero(np.histogram(ang, bins=ROUND_BINS,
                                                    range=(-np.pi, np.pi))[0]) / ROUND_BINS
                sc = cov + 1e-3 * float(W[widx][inl].sum())
                if sc > best[0]:
                    best = (sc, (cx, cy, r), int(sd))
            if best[1] is None:
                break
            cx, cy, r = best[1]
            p = cx * u + cy * v
            fm = np.zeros(len(W), dtype=bool)
            for _k in range(3):
                rel3 = C - p
                perp = rel3 - np.outer(rel3 @ a, a)
                rad3 = np.linalg.norm(perp, axis=1)
                uh = perp / np.maximum(rad3, 1e-12)[:, None]
                fm = (wall & (np.abs(rad3 - r) <= label_dist)
                      & (np.abs(np.einsum("ij,ij->i", N, uh)) >= cos_f))
                fm = _largest_piece(adj, fm, W)
                if fm.sum() < 6:
                    break
                p, r = fit_circle_fixed_axis_robust(verts[np.unique(faces[fm])], a, p, nf)
            if fm.sum() < 6 or float(W[fm].sum()) < CAPPED_RING_MIN_MM2:
                tried[widx[best[2]]] = True
                tried |= fm
                continue
            vidx, wv, _ = _area_vertices(faces, W, fm)
            pts = verts[vidx]
            p = _axis_foot(a, p, pts.mean(0))
            res = cyl_residual(pts, a, p, r)
            rms = float(np.sqrt(np.average(res ** 2, weights=wv)))
            cov = arc_coverage(C, W, fm, a, p)
            rel = C[fm] - p
            perp = rel - np.outer(rel @ a, a)
            uh = perp / np.maximum(np.linalg.norm(perp, axis=1), 1e-12)[:, None]
            outward = float(np.average(np.einsum("ij,ij->i", N[fm], uh), weights=W[fm]))
            along = (pts - p) @ a
            length = float(along.max() - along.min())
            lab_ok = area_lab >= 0
            fsq = np.zeros(len(W), dtype=bool)
            for ar in areas:
                if ar["type"] == "flat" and abs(float(_unit(ar["_n"]) @ a)) >= np.cos(
                        np.radians(FLAT_MAX_TILT_DEG)):
                    fsq |= lab_ok & (area_lab == ar["id"])
            caps = ring_caps(C, N, W, fm, a, p, r, fsq)
            entry = {"axis": [round(float(x), 4) for x in a],
                     "point_mm": [round(float(x), 4) for x in p],
                     "diameter_mm": round(2 * r, 4),
                     "area_mm2": round(float(W[fm].sum()), 2), "coverage": round(cov, 4),
                     "length_mm": round(length, 3), "rms_mm": round(rms, 5),
                     "side": "outward" if outward > 0 else "inward",
                     "cap_share": [None if c["share"] is None else round(c["share"], 3)
                                   for c in caps]}
            ring_ok = []
            if rms > ROUND_MAX_RMS_NOISE * nf:
                ring_ok.append(f"fit rms {rms:.3f} mm is over {ROUND_MAX_RMS_NOISE:g} x noise")
            if cov < CAPPED_RING_MIN_COVERAGE:
                ring_ok.append(f"covers {cov * 100:.0f}% of the turn "
                               f"(needs {CAPPED_RING_MIN_COVERAGE * 100:.0f}%)")
            if length < CAPPED_RING_MIN_LEN_MM:
                ring_ok.append(f"only {length:.2f} mm long")
            why = list(ring_ok)
            for k, nm in ((0, "low"), (1, "high")):
                sh = caps[k]["share"]
                if sh is None or sh < CAPPED_RING_CAP_SHARE:
                    why.append(f"the {nm} end along the axis is not capped by a flat "
                               f"square to it ({0 if sh is None else sh * 100:.0f}% of "
                               f"the faces past it; needs {CAPPED_RING_CAP_SHARE * 100:.0f}%)")
            tried |= fm
            tried[widx[best[2]]] = True
            if not ring_ok:
                guides.append({"a": a, "p": p, "r": float(r), "accepted": not why,
                               "fm": fm, "outward": outward, "length": length,
                               "cov": round(cov, 4), "rms": rms, "entry": entry})
            if why:
                entry["why"] = "; ".join(why)
                entry["cut_guide"] = not ring_ok
                log.append(entry)
                continue
            kind = "boss" if outward > 0 else "hole"
            snaps = []
            std = {"table": table, "nearest_mm": round(nearest_size(2 * r, table), 4)}
            if kind == "hole":
                d_std = snap_hole(2 * r, table, tol)
                if d_std is not None:
                    snaps.append(f"diameter {2 * r:.4f} -> {d_std:g} mm ({table}), "
                                 f"moved {abs(d_std - 2 * r) / 2:.4f} mm")
                    r = d_std / 2
                    std = {"table": table, "diameter_mm": d_std}
                    res = cyl_residual(pts, a, p, r)
            pc = pass_check(pts, wv, res, tol=tol, cap=cap, axis=a, point=p)
            st = _stats(res)
            ring_area = {
                "id": len(areas), "type": "round", "kind": kind,
                "n_faces": int(fm.sum()), "area_mm2": round(float(W[fm].sum()), 2),
                "n_patches": 1, "snaps": snaps, "standard_size": std,
                "partial": False, "capped_ring": True,
                "round_check": {"coverage": round(cov, 4), "rms_mm": round(rms, 5),
                                "length_mm": round(length, 3),
                                "cap_share": entry["cap_share"], "axis_fixed": True},
                "fit": {"axis": [round(float(x), 6) for x in a],
                        "point_mm": [round(float(x), 4) for x in p],
                        "diameter_mm": round(2 * r, 4), "length_mm": round(length, 3), **st},
                "final": {"axis": [round(float(x), 9) for x in a],
                          "point_mm": [round(float(x), 4) for x in p],
                          "diameter_mm": round(2 * r, 4), **st},
                "judged": pc["stats"], "within_tol": pc["stats"]["within_tol"],
                "within_tol_raw": bool(st["p95_mm"] <= tol),
                "_a": a, "_p": p, "_r": r, "_pts": pts, "_fmask": fm, "_vidx": vidx,
                "_jres": pc["residual"]}
            entry["accepted_area"] = ring_area["id"]
            pool &= ~fm
            accept(fm, ring_area)
            entry["cap_flats"] = []
            for c in caps:
                cf = _cap_flat(verts, faces, C, N, W, adj, pool, c["faces"], a,
                               label_dist=label_dist, flat_lim=flat_lim, tol=tol, cap=cap)
                if cf is None:
                    continue
                cm = cf["fmask"]
                flat = {
                    "id": len(areas), "type": "flat", "kind": "plane",
                    "n_faces": int(cm.sum()), "area_mm2": round(float(W[cm].sum()), 2),
                    "n_patches": len(_pieces(adj, cm)),
                    "snaps": ["normal exactly the capped ring's axis"],
                    "ring_cap_of": ring_area["id"],
                    "fit": {"normal": [round(float(x), 6) for x in cf["n"]],
                            "offset_mm": round(cf["d"], 4), **cf["stats"]},
                    "final": {"normal": [round(float(x), 9) for x in cf["n"]],
                              "offset_mm": round(cf["d"], 4), **cf["stats"]},
                    "judged": cf["pc"]["stats"], "within_tol": cf["pc"]["stats"]["within_tol"],
                    "within_tol_raw": bool(cf["stats"]["p95_mm"] <= tol),
                    "_n": cf["n"], "_d": cf["d"], "_pts": cf["pts"], "_fmask": cm,
                    "_vidx": cf["vidx"], "_jres": cf["pc"]["residual"]}
                pool &= ~cm
                accept(cm, flat)
                entry["cap_flats"].append(flat["id"])
            log.append(entry)
    return {"tried": log,
            "guides": [{"axis": [round(float(x), 4) for x in g["a"]],
                        "point_mm": [round(float(x), 4) for x in g["p"]],
                        "diameter_mm": round(2 * g["r"], 4), "accepted": g["accepted"]}
                       for g in guides],
            "_guides": guides}


def _guide_cuts(members, C, guides) -> list[list[np.ndarray]]:
    """Ways to cut a chart in two around a ring's axis: the faces within
    r + k mm of the axis, and the rest (k in CAPPED_RING_GUIDE_STEPS_MM)."""
    out = []
    for g in guides or []:
        rel = C[members] - g["p"]
        perp = rel - np.outer(rel @ g["a"], g["a"])
        rad = np.linalg.norm(perp, axis=1)
        if not (rad <= g["r"] + max(CAPPED_RING_GUIDE_STEPS_MM)).any():
            continue
        for k in CAPPED_RING_GUIDE_STEPS_MM:
            m = rad <= g["r"] + k
            if m.any() and (~m).any():
                out.append([members[m], members[~m]])
    return out


# == stud posts =================================================================
# The pedal adapter has three small domed studs (about 8.5 mm wide, 2 mm tall,
# a dimple in the middle). Their side walls are convincing rings (fixed axis,
# 86-89% of the turn, rms about 2 x noise) but their ends are not flat
# squares: the top is a small flat with a rounded edge and a dimple, and the
# floor they stand on blends up into them, so only 16-41% of the faces past
# either end are square to the axis and the capped-ring rule (50%) refuses
# them. the user wants them as clean round posts. A ring that is refused ONLY
# for its caps is accepted as a stud post when, on top of everything a capped
# ring needs (fixed axis, coverage, rms, length):
#
# - it is outward (a boss), at most STUD_MAX_D_MM across and no longer than
#   STUD_MAX_LEN_FACTOR x its diameter - a short post, not a shaft;
# - one end is CLOSED: the faces inside its footprint past that end cover at
#   least STUD_TOP_COVER of the footprint (projected), face out along the
#   axis on average within STUD_TOP_FACING_DEG, sit within
#   STUD_TOP_SPREAD_FACTOR x radius along the axis, and are still unfitted;
# - the other end stands on a floor: of the faces just past it, at least
#   STUD_BASE_SHARE by area are within STUD_BASE_TILT_DEG of square to the
#   axis (rounded feet lean, so this is wider than the capped ring's 15 deg);
# - the closed end holds a flat square to the axis (same flat-off check as
#   every cap flat): the post's top. A dome or dimple is not fitted - faces
#   near the middle sitting more than the texture limit below the top are
#   reported as an ignored dimple and left uncovered, and the top goes
#   straight across.
#
# The post is a plain cylinder. Its diameter is snapped: studs on one axis
# whose diameters agree within STUD_SAME_D_TOL_FACTOR x tolerance share one
# diameter (their area-weighted mean), snapped to the STUD_D_STEP grid, when
# that moves no wall by more than the tolerance; otherwise each snaps on its
# own, or not at all. The top's height above a fitted floor flat is snapped to
# STUD_H_STEP the same way (the floor is the fitted flat facing the same way
# as the top with the most area within STUD_FLOOR_REACH_MM of the wall and at
# most the post's length + STUD_FLOOR_REACH_MM below the top). Both are then judged by the 95% rule and reported
# outside tolerance when they miss. Tolerance and stiffness are untouched.
STUD_MAX_D_MM = 16.0
STUD_MAX_LEN_FACTOR = 1.0
STUD_TOP_COVER = 0.6
STUD_TOP_FACING_DEG = 45.0
STUD_TOP_SPREAD_FACTOR = 0.6
STUD_TOP_UNFITTED = 0.8
STUD_BASE_TILT_DEG = 35.0
STUD_BASE_SHARE = 0.5
STUD_DIMPLE_R_FRAC = 0.6
STUD_FLOOR_REACH_MM = 6.0
STUD_SAME_D_TOL_FACTOR = 4.0
STUD_D_STEP = {"metric": 0.5, "inch": INCH / 32}
STUD_H_STEP = {"metric": 0.1, "inch": INCH / 128}


def _snap_step(x: float, step: float) -> float:
    return float(np.round(x / step) * step)


def stud_evidence(C, N, W, fm, pool, a, p, r, length, fitted_square) -> dict:
    """Closed-end and floor evidence for a short outward ring (see STUD_*).

    Returns {"why": [...], "top_sign": +-1, "top": mask, "base_share": x}."""
    a = _unit(a)
    rel = C - p
    along = rel @ a
    rad = np.linalg.norm(rel - np.outer(along, a), axis=1)
    alo, ahi = float(along[fm].min()), float(along[fm].max())
    mid = 0.5 * (alo + ahi)
    foot = (rad <= r) & ~fm
    best = None
    for sgn in (1.0, -1.0):
        beyond = (sgn * (along - mid) >= 0) & (sgn * (along - mid) <= 0.5 * length + r)
        top = foot & beyond
        if not top.any():
            continue
        proj = float((W[top] * np.abs(N[top] @ a)).sum())
        cover = proj / (np.pi * r * r)
        facing = float(np.average(N[top] @ (sgn * a), weights=W[top]))
        if best is None or cover * max(facing, 0) > best["score"]:
            best = {"score": cover * max(facing, 0), "sgn": sgn, "top": top,
                    "cover": cover, "facing": facing}
    out = {"why": [], "top_sign": None, "top": None, "base_share": None}
    if best is None:
        out["why"].append("nothing inside its footprint past either end")
        return out
    top, sgn = best["top"], best["sgn"]
    ta = along[top]
    spread = float(_wpercentile(ta, W[top], 95) - _wpercentile(ta, W[top], 5))
    unfitted = float(W[top & pool].sum() / W[top].sum())
    out.update(top_sign=sgn, top=top, top_cover=round(best["cover"], 3),
               top_facing_deg=round(float(np.degrees(np.arccos(np.clip(best["facing"], -1, 1)))), 1),
               top_spread_mm=round(spread, 3), top_unfitted=round(unfitted, 3))
    if best["cover"] < STUD_TOP_COVER:
        out["why"].append(f"its end covers {best['cover'] * 100:.0f}% of the footprint "
                          f"(needs {STUD_TOP_COVER * 100:.0f}%)")
    if best["facing"] < np.cos(np.radians(STUD_TOP_FACING_DEG)):
        out["why"].append(f"its end leans {out['top_facing_deg']:.0f} deg off the axis "
                          f"(at most {STUD_TOP_FACING_DEG:g})")
    if spread > STUD_TOP_SPREAD_FACTOR * r:
        out["why"].append(f"its end spreads {spread:.2f} mm along the axis "
                          f"(at most {STUD_TOP_SPREAD_FACTOR:g} x radius)")
    if unfitted < STUD_TOP_UNFITTED:
        out["why"].append("its end is already fitted as something else")
    caps = ring_caps(C, N, W, fm, a, p, r, fitted_square, tilt_deg=STUD_BASE_TILT_DEG)
    base = caps[0] if sgn > 0 else caps[1]
    out["base_share"] = None if base["share"] is None else round(base["share"], 3)
    out["base_faces"] = base["faces"]
    if base["share"] is None or base["share"] < STUD_BASE_SHARE:
        out["why"].append(f"it does not stand on a floor ({0 if base['share'] is None else base['share'] * 100:.0f}% "
                          f"of the faces past its foot are within {STUD_BASE_TILT_DEG:g} deg of square; "
                          f"needs {STUD_BASE_SHARE * 100:.0f}%)")
    return out


def find_stud_posts(verts, faces, C, N, W, adj, pool, area_lab, areas, *, guides, nf,
                    tol, label_dist, flat_lim, cap, table, accept, directions=()) -> dict:
    """Stud posts from rings the capped-ring rule refused only for their caps.

    Only rings whose axis is one of the part's main directions (`directions`
    and the frame axes, within SNAP_ANGLE_DEG) can be studs."""
    log, cands = [], []
    mains = [_unit(d) for d in list(directions) + list(np.eye(3))]
    cos_s = np.cos(np.radians(SNAP_ANGLE_DEG))
    lab_ok = area_lab >= 0
    # Rings stacked on one axis (a tapered or rounded wall is often found as
    # two short rings, one above the other) are one wall: their faces are
    # joined and the circle refitted on the same fixed axis.
    open_g = [g for g in guides if not g.get("accepted") and "fm" in g and g["outward"] > 0
              and any(abs(float(_unit(g["a"]) @ m)) >= cos_s for m in mains)]
    open_g.sort(key=lambda g: -float(W[g["fm"]].sum()))
    walls, used = [], set()
    for i, g in enumerate(open_g):
        if i in used:
            continue
        a = _unit(g["a"])
        grp = [g]
        for j in range(i + 1, len(open_g)):
            o = open_g[j]
            if j in used or abs(float(_unit(o["a"]) @ a)) < np.cos(np.radians(SNAP_ANGLE_DEG)):
                continue
            dp = o["p"] - g["p"]
            if np.linalg.norm(dp - (dp @ a) * a) <= max(COAX_CANDIDATE_MM, 0.25 * g["r"]) \
                    and abs(o["r"] - g["r"]) <= 0.25 * g["r"]:
                grp.append(o)
                used.add(j)
        if len(grp) == 1:
            walls.append(g)
            continue
        fm = np.zeros(len(W), dtype=bool)
        for o in grp:
            fm |= o["fm"]
        p, r = fit_circle_fixed_axis_robust(verts[np.unique(faces[fm])], a, g["p"], nf)
        vidx, wv, _ = _area_vertices(faces, W, fm)
        pts = verts[vidx]
        p = _axis_foot(a, p, pts.mean(0))
        res = cyl_residual(pts, a, p, r)
        along = (pts - p) @ a
        walls.append({"a": a, "p": p, "r": float(r), "fm": fm, "outward": 1.0,
                      "length": float(along.max() - along.min()),
                      "cov": round(arc_coverage(C, W, fm, a, p), 4),
                      "rms": float(np.sqrt(np.average(res ** 2, weights=wv))),
                      "joined_rings": len(grp), "_members": grp})
    for g in walls:
        a, p, r = _unit(g["a"]), g["p"], float(g["r"])
        fm = g["fm"] & pool
        entry = {"axis": [round(float(x), 4) for x in a],
                 "point_mm": [round(float(x), 4) for x in p],
                 "diameter_mm": round(2 * r, 4), "length_mm": round(g["length"], 3),
                 "rings_joined": g.get("joined_rings", 1)}
        why = []
        if g["rms"] > ROUND_MAX_RMS_NOISE * nf:
            why.append(f"joined wall fits rms {g['rms']:.3f} mm, over "
                       f"{ROUND_MAX_RMS_NOISE:g} x noise")
        if g["cov"] < CAPPED_RING_MIN_COVERAGE:
            why.append(f"covers {g['cov'] * 100:.0f}% of the turn")
        if g["outward"] <= 0:
            why.append("it is a hole, not a post")
        if 2 * r > STUD_MAX_D_MM:
            why.append(f"{2 * r:.1f} mm across (at most {STUD_MAX_D_MM:g})")
        if g["length"] > STUD_MAX_LEN_FACTOR * 2 * r:
            why.append(f"{g['length']:.1f} mm long, more than {STUD_MAX_LEN_FACTOR:g} x its diameter")
        if float(W[fm].sum()) < 0.9 * float(W[g["fm"]].sum()):
            why.append("its wall has been taken by another area")
        if any(float(W[fm & o["fm"]].sum()) > 0.3 * float(W[fm].sum()) for o in cands):
            why.append("its wall is the wall of a stud already found")
        if why:
            entry["why"] = "; ".join(why)
            log.append(entry)
            continue
        fsq = np.zeros(len(W), dtype=bool)
        for ar in areas:
            if ar["type"] == "flat" and abs(float(_unit(ar["_n"]) @ a)) >= np.cos(
                    np.radians(FLAT_MAX_TILT_DEG)):
                fsq |= lab_ok & (area_lab == ar["id"])
        ev = stud_evidence(C, N, W, fm, pool, a, p, r, g["length"], fsq)
        entry.update({k: v for k, v in ev.items()
                      if k not in ("why", "top", "base_faces", "top_sign")})
        if ev["why"]:
            entry["why"] = "; ".join(ev["why"])
            log.append(entry)
            continue
        sgn = ev["top_sign"]
        n_top = sgn * a
        rel = C - p
        rad = np.linalg.norm(rel - np.outer(rel @ a, a), axis=1)
        foot = rad <= r
        cf = _cap_flat(verts, faces, C, N, W, adj, pool & foot & ~fm, ev["top"], n_top,
                       label_dist=label_dist, flat_lim=flat_lim, tol=tol, cap=cap)
        if cf is None:
            entry["why"] = "no flat top square to the axis on its closed end"
            log.append(entry)
            continue
        # base floor: a fitted flat square to the axis just past the foot
        base_flat = None
        lev = C @ cf["n"]
        bf = ((rad > r) & (rad <= r + STUD_FLOOR_REACH_MM) & (lev < cf["d"] - tol)
              & (lev >= cf["d"] - g["length"] - STUD_FLOOR_REACH_MM))
        best_w = 0.0
        for ar in areas:
            if ar["type"] != "flat" or float(_unit(ar["_n"]) @ n_top) < cos_s:
                continue        # a floor faces the same way as the top
            wsum = float(W[bf & lab_ok & (area_lab == ar["id"])].sum())
            if wsum > best_w:
                best_w, base_flat = wsum, ar
        dimple = ev["top"] & pool & ~cf["fmask"] & (rad <= STUD_DIMPLE_R_FRAC * r) \
            & ((cf["d"] - C @ cf["n"]) > cap)
        cands.append({"g": g, "a": a, "p": p, "r": r, "fm": fm, "entry": entry,
                      "cf": cf, "base": base_flat, "dimple": dimple})
        log.append(entry)

    # one diameter for studs that are the same size, snapped to the grid
    step_d = STUD_D_STEP.get(table, STUD_D_STEP["metric"])
    done = set()
    for i, c in enumerate(cands):
        if i in done:
            continue
        grp = [j for j, o in enumerate(cands) if j not in done
               and abs(float(o["a"] @ c["a"])) >= np.cos(np.radians(SNAP_ANGLE_DEG))
               and abs(2 * o["r"] - 2 * c["r"]) <= STUD_SAME_D_TOL_FACTOR * tol]
        done.update(grp)
        w = np.array([float(W[cands[j]["fm"]].sum()) for j in grp])
        d_mean = float(np.average([2 * cands[j]["r"] for j in grp], weights=w))
        d_std = _snap_step(d_mean, step_d)
        shared = len(grp) > 1 and all(abs(d_std / 2 - cands[j]["r"]) <= tol for j in grp)
        for j in grp:
            o = cands[j]
            if shared:
                o["d_std"], o["d_how"] = d_std, f"shared by {len(grp)} studs"
            else:
                own = _snap_step(2 * o["r"], step_d)
                o["d_std"], o["d_how"] = (own, "own") if abs(own / 2 - o["r"]) <= tol else (None, None)

    found = []
    step_h = STUD_H_STEP.get(table, STUD_H_STEP["metric"])
    for c in cands:
        a, p, r, fm, cf, entry = c["a"], c["p"], c["r"], c["fm"], c["cf"], c["entry"]
        vidx, wv, _ = _area_vertices(faces, W, fm)
        pts = verts[vidx]
        snaps = []
        res0 = cyl_residual(pts, a, p, r)
        if c["d_std"] is not None:
            snaps.append(f"diameter {2 * r:.4f} -> {c['d_std']:g} mm ({c['d_how']}; "
                         f"{step_d:g} mm grid), moved {abs(c['d_std'] / 2 - r):.4f} mm")
            r = c["d_std"] / 2
        res = cyl_residual(pts, a, p, r)
        pc = pass_check(pts, wv, res, tol=tol, cap=cap, axis=a, point=p)
        st = _stats(res)
        along = (pts - p) @ a
        post = {
            "id": len(areas), "type": "round", "kind": "boss",
            "n_faces": int(fm.sum()), "area_mm2": round(float(W[fm].sum()), 2),
            "n_patches": 1, "snaps": snaps,
            "standard_size": {"table": table, "diameter_mm": c["d_std"],
                              "grid_mm": step_d},
            "partial": False, "capped_ring": False, "stud_post": True,
            "round_check": {"coverage": c["g"]["cov"], "rms_mm": round(c["g"]["rms"], 5),
                            "length_mm": round(float(along.max() - along.min()), 3),
                            "axis_fixed": True, "fit_rms_before_snap_mm":
                            round(float(np.sqrt(np.average(res0 ** 2, weights=wv))), 5)},
            "fit": {"axis": [round(float(x), 6) for x in a],
                    "point_mm": [round(float(x), 4) for x in p],
                    "diameter_mm": round(2 * r, 4),
                    "length_mm": round(float(along.max() - along.min()), 3), **st},
            "final": {"axis": [round(float(x), 9) for x in a],
                      "point_mm": [round(float(x), 4) for x in p],
                      "diameter_mm": round(2 * r, 4), **st},
            "judged": pc["stats"], "within_tol": pc["stats"]["within_tol"],
            "within_tol_raw": bool(st["p95_mm"] <= tol),
            "_a": a, "_p": p, "_r": r, "_pts": pts, "_fmask": fm, "_vidx": vidx,
            "_jres": pc["residual"]}
        pool &= ~fm
        accept(fm, post)
        c["g"]["accepted"] = True
        for o in c["g"].get("_members", []):
            o["accepted"] = True
        # the top
        n, d = cf["n"], cf["d"]
        tsnaps = ["normal exactly the stud's axis"]
        height = None
        if c["base"] is not None:
            b = c["base"]
            d_base = float(b["_d"]) if float(_unit(b["_n"]) @ n) > 0 else -float(b["_d"])
            h_now = d - d_base
            h_std = _snap_step(h_now, step_h)
            move = abs(h_std - h_now)
            height = {"floor_area": b["id"], "height_mm": round(h_now, 4)}
            if move <= tol and h_std > 0:
                tsnaps.append(f"height above floor {b['id']} {h_now:.4f} -> {h_std:g} mm "
                              f"({step_h:g} mm grid), moved {move:.4f} mm")
                d = d_base + h_std
                height["height_mm"] = round(h_std, 4)
                height["snapped"] = True
        tm = cf["fmask"]
        tres = plane_residual(cf["pts"], n, d)
        tpc = pass_check(cf["pts"], _area_vertices(faces, W, tm)[1], tres, tol=tol, cap=cap)
        tst = _stats(tres)
        top = {
            "id": len(areas), "type": "flat", "kind": "plane",
            "n_faces": int(tm.sum()), "area_mm2": round(float(W[tm].sum()), 2),
            "n_patches": len(_pieces(adj, tm)), "snaps": tsnaps,
            "stud_top_of": post["id"],
            "fit": {"normal": [round(float(x), 6) for x in n],
                    "offset_mm": round(d, 4), **tst},
            "final": {"normal": [round(float(x), 9) for x in n],
                      "offset_mm": round(d, 4), **tst},
            "judged": tpc["stats"], "within_tol": tpc["stats"]["within_tol"],
            "within_tol_raw": bool(tst["p95_mm"] <= tol),
            "_n": n, "_d": d, "_pts": cf["pts"], "_fmask": tm,
            "_vidx": cf["vidx"], "_jres": tpc["residual"]}
        pool &= ~tm
        accept(tm, top)
        dim = c["dimple"] & (area_lab < 0)
        depth = float((d - C[dim] @ n).max()) if dim.any() else 0.0
        post["stud"] = {"top_area": top["id"], "top": "flat",
                        "height_above_floor": height,
                        "dimple_ignored": {"area_mm2": round(float(W[dim].sum()), 2),
                                           "depth_mm": round(depth, 3),
                                           "note": "not fitted; the top goes straight "
                                                   "across and these faces stay uncovered"}}
        entry.update(accepted_area=post["id"], top_area=top["id"],
                     diameter_snapped_mm=c["d_std"], height=height,
                     dimple_mm2=round(float(W[dim].sum()), 2))
        found.append({"post": post["id"], "top": top["id"],
                      "diameter_mm": round(2 * r, 4), "height": height,
                      "centre_mm": [round(float(x), 2) for x in pts.mean(0)],
                      "within_tol": [post["within_tol"], top["within_tol"]]})
    return {"rule": ("a short outward ring on a part axis, refused only for its caps, "
                     "with a closed end inside its footprint and standing on a floor, "
                     "is a stud post: a plain cylinder with a snapped diameter and a "
                     "flat top square to the axis; a dimple is ignored, not fitted"),
            "found": found, "tried": log}


# == level blends ===============================================================
# Two fitted flats facing the same way at different heights are often joined
# by a short ramp or rounded step (the pedal adapter's ledges and pockets).
# Left to the stiff spline, such a band either misses or drags the spline off
# the flats beside it. Here the band is fitted as a clean blend: a surface
# swept straight along the step, whose cross-section goes from one level to
# the other, one of
#
#   chamfer  a straight ramp (angle snapped to BLEND_ANGLE_STEPS),
#   round    two equal tangent arcs (an ogee; radius snapped to the fillet
#            table), tangent to both flats,
#   smooth   a cubic tangent to both flats (width snapped to BLEND_WIDTH_STEP),
#
# whichever fits the band best (simplest first on a tie). A pair qualifies
# when the flats are parallel within SNAP_ANGLE_DEG, face the same way, and
# the step is between BLEND_MIN_STEP_FACTOR x tolerance and BLEND_MAX_STEP_MM.
# The band is the unfitted faces between the two heights, within reach of
# both flats, that lean between the flat and the step, connected from one
# flat to the other. A blend is kept when its fit rms is within the round
# check's noise multiple, its points cover at least BLEND_MIN_SPAN of the
# ramp's width and height, at least BLEND_MIN_RAMP_SHARE of the ramp (over
# the blend's own length) lies on it, and it is at least FILLET_MIN_MM2. It is then
# judged by the 95% rule like every area. Snaps move nothing by more than the
# tolerance. Not in the size check.
BLEND_MIN_STEP_FACTOR = 3.0
BLEND_MAX_STEP_MM = 15.0
BLEND_REACH_MM = 6.0
BLEND_MIN_SPAN = 0.6
BLEND_MIN_RAMP_SHARE = FILLET_MIN_CORNER_SHARE
BLEND_ANGLE_STEPS = (5.0, 1.0)
BLEND_WIDTH_STEP = 0.5
BLEND_PROFILES = ("chamfer", "round", "smooth")
BLEND_MAX_TRIES = 400


def _blend_f(u, prof):
    u = np.clip(u, 0.0, 1.0)
    if prof == "smooth":
        return u * u * (3 - 2 * u)
    if prof == "round":
        # two equal tangent arcs from (0,0) to (1,1) in units of width / height;
        # evaluated on the real geometry in blend_curve
        return u
    return u


def blend_curve(bl: dict, n_samples: int = 400) -> np.ndarray:
    """(x, s) samples of a blend cross-section, flats extended either side."""
    x0, w, h, sA, prof = bl["x0"], bl["w"], bl["h"], bl["sA"], bl["profile"]
    aw = abs(w)
    ext = max(aw, 2.0) + BLEND_REACH_MM
    if prof == "round":
        R = bl["R"]
        # first arc: centre at (0, R) in (lateral, height) with tangent flat at 0
        phi = np.arccos(np.clip(1 - h / (2 * R), -1, 1)) if h > 0 else 0.0
        t = np.linspace(0, phi, n_samples // 2)
        xa, sa = R * np.sin(t), R * (1 - np.cos(t))
        xb, sb = aw - xa[::-1], h - sa[::-1]
        xs, ss = np.concatenate([xa, xb]), np.concatenate([sa, sb])
    else:
        u = np.linspace(0, 1, n_samples)
        xs, ss = u * aw, h * _blend_f(u, prof)
    xs = np.concatenate([np.linspace(-ext, 0, 60)[:-1], xs, aw + np.linspace(0, ext, 60)[1:]])
    ss = np.concatenate([np.zeros(59), ss, np.full(59, h)])
    sign = 1.0 if w >= 0 else -1.0
    return np.column_stack([x0 + sign * xs, sA + ss])


def blend_residual(P, bl: dict) -> np.ndarray:
    """Signed distance from points to a blend (positive on the flats' normal side)."""
    P = np.asarray(P, float)
    xy = np.column_stack([P @ bl["t"], P @ bl["n"]])
    cur = blend_curve(bl, 2000)
    foot = _polyline_foot(cur, xy)
    d = xy - foot
    dist = np.linalg.norm(d, axis=1)
    # sign: the side of the curve the level normal points to is positive
    return np.where(d[:, 1] >= 0, dist, -dist)


def _polyline_foot(cur: np.ndarray, xy: np.ndarray) -> np.ndarray:
    """Nearest point on a 2-D polyline (exact, on the two segments either
    side of the nearest vertex)."""
    _, k = cKDTree(cur).query(xy)
    best = cur[k].copy()
    bd = np.linalg.norm(xy - best, axis=1)
    for k0, k1 in ((k - 1, k), (k, k + 1)):
        ok = (k0 >= 0) & (k1 < len(cur))
        a0, a1 = cur[np.clip(k0, 0, len(cur) - 1)], cur[np.clip(k1, 0, len(cur) - 1)]
        seg = a1 - a0
        L2 = np.maximum((seg * seg).sum(1), 1e-18)
        u = np.clip(((xy - a0) * seg).sum(1) / L2, 0, 1)
        q = a0 + seg * u[:, None]
        dq = np.linalg.norm(xy - q, axis=1)
        better = ok & (dq < bd)
        best[better], bd[better] = q[better], dq[better]
    return best


def _blend_from(prof, x0, w, h, sA, n, t, R=None):
    bl = {"profile": prof, "x0": float(x0), "w": float(w), "h": float(h),
          "sA": float(sA), "n": n, "t": t}
    if prof == "round":
        bl["R"] = float(R if R is not None else (w * w + h * h) / (4 * h))
        bl["w"] = float(np.sign(w) * np.sqrt(max(4 * h * bl["R"] - h * h, 1e-12)))
    return bl


def _fit_blend(P, wts, prof, n, t, sA, h, x0, w):
    def res(x):
        if prof == "round":
            R = max(x[1], h / 4 + 1e-6)
            bl = _blend_from(prof, x[0], np.sign(w) * np.sqrt(4 * h * R - h * h), h, sA, n, t, R)
        else:
            if abs(x[1]) < 0.05:
                x = np.array([x[0], np.sign(x[1] or 1) * 0.05])
            bl = _blend_from(prof, x[0], x[1], h, sA, n, t)
        return np.sqrt(wts) * blend_residual(P, bl)
    if prof == "round":
        R0 = max((w * w + h * h) / (4 * h), h / 4 + 0.05)
        sol = least_squares(res, [x0, R0], loss="soft_l1", f_scale=0.2,
                            bounds=([-np.inf, h / 4 + 1e-3], [np.inf, FILLET_MAX_R_MM * 3]))
        return _blend_from(prof, sol.x[0], w, h, sA, n, t, sol.x[1])
    sol = least_squares(res, [x0, w], loss="soft_l1", f_scale=0.2)
    return _blend_from(prof, sol.x[0], sol.x[1], h, sA, n, t)


def _snap_blend(bl, P, table, tol):
    """Snap a blend's angle / radius / width when that moves it by <= tol."""
    base = blend_residual(P, bl)
    tries = []
    h = bl["h"]
    if bl["profile"] == "chamfer":
        ang = float(np.degrees(np.arctan2(h, abs(bl["w"]))))
        for stp in BLEND_ANGLE_STEPS:
            a_std = _snap_step(ang, stp)
            if 0 < a_std < 90:
                w_std = np.sign(bl["w"]) * h / np.tan(np.radians(a_std))
                # keep the ramp centred where it was
                x0 = bl["x0"] + (bl["w"] - w_std) / 2
                tries.append((_blend_from("chamfer", x0, w_std, h, bl["sA"], bl["n"], bl["t"]),
                              f"angle {ang:.2f} -> {a_std:g} deg"))
    elif bl["profile"] == "round":
        tab = _radius_table(table)
        tab = tab[tab > h / 4]
        if len(tab):
            r_std = float(tab[np.argmin(np.abs(tab - bl["R"]))])
            nb = _blend_from("round", 0.0, bl["w"], h, bl["sA"], bl["n"], bl["t"], r_std)
            nb["x0"] = bl["x0"] + (bl["w"] - nb["w"]) / 2
            tries.append((nb, f"radius {bl['R']:.4f} -> {r_std:g} mm ({table})"))
    else:
        w_std = np.sign(bl["w"]) * max(_snap_step(abs(bl["w"]), BLEND_WIDTH_STEP), BLEND_WIDTH_STEP)
        x0 = bl["x0"] + (bl["w"] - w_std) / 2
        tries.append((_blend_from("smooth", x0, w_std, h, bl["sA"], bl["n"], bl["t"]),
                      f"width {abs(bl['w']):.4f} -> {abs(w_std):g} mm"))
    for nb, txt in tries:
        move = float(np.abs(blend_residual(P, nb) - base).max())
        if move <= tol:
            return nb, f"{txt}, moved {move:.4f} mm"
    return bl, None


def blend_size(bl) -> dict:
    out = {"profile": bl["profile"], "step_mm": round(bl["h"], 4),
           "width_mm": round(abs(bl["w"]), 4),
           "angle_deg": round(float(np.degrees(np.arctan2(bl["h"], abs(bl["w"])))), 2)}
    if bl["profile"] == "round":
        out["radius_mm"] = round(bl["R"], 4)
    return out


def find_level_blends(verts, faces, C, N, W, adj, pool, area_lab, areas, *, nf, tol,
                      label_dist, cap, table, accept) -> dict:
    """Blends between parallel fitted flats at different heights, from `pool`."""
    # a stud's top or a ring's cap is joined to its floor by a wall, not a blend
    flats = [a for a in areas if a["type"] == "flat"
             and "stud_top_of" not in a and "ring_cap_of" not in a]
    log, found = [], []
    if len(flats) < 2 or not pool.any():
        return {"found": found, "tried": log}
    cos_p = np.cos(np.radians(SNAP_ANGLE_DEG))
    pidx = np.flatnonzero(pool)
    near = {}
    for f in flats:
        idx = np.flatnonzero(area_lab == f["id"])
        if len(idx) == 0:
            continue
        dist, _ = cKDTree(C[idx]).query(C[pidx], distance_upper_bound=BLEND_REACH_MM)
        near[f["id"]] = dist
    ids = [f for f in flats if f["id"] in near]
    pairs = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            fA, fB = ids[i], ids[j]
            nA, nB = _unit(fA["_n"]), _unit(fB["_n"])
            if float(nA @ nB) < cos_p:
                continue
            sA = float(fA["_d"])
            sB = float(np.average(fB["_pts"] @ nA))
            h = sB - sA
            if not BLEND_MIN_STEP_FACTOR * tol <= abs(h) <= BLEND_MAX_STEP_MM:
                continue
            both = (near[fA["id"]] <= BLEND_REACH_MM) & (near[fB["id"]] <= BLEND_REACH_MM)
            if float(W[pidx[both]].sum()) < FILLET_MIN_MM2:
                continue
            pairs.append((float(W[pidx[both]].sum()), fA, fB, nA, sA, sB))
    pairs.sort(key=lambda t: -t[0])
    for _, fA, fB, n, sA, sB in pairs[:BLEND_MAX_TRIES]:
        if sB < sA:     # A is always the lower level along n
            fA, fB, sA, sB = fB, fA, sB, sA
        h = sB - sA
        dA = near[fA["id"]]
        dB = near[fB["id"]]
        pmask = pool[pidx]
        s = C[pidx] @ n
        nn = N[pidx] @ n
        band = (pmask & (dA <= BLEND_REACH_MM) & (dB <= BLEND_REACH_MM)
                & (s >= sA - label_dist) & (s <= sB + label_dist) & (nn > 0.05))
        ci = pidx[band]
        entry = {"flats": [fA["id"], fB["id"]], "step_mm": round(h, 4),
                 "candidate_mm2": round(float(W[ci].sum()), 2)}
        if float(W[ci].sum()) < FILLET_MIN_MM2:
            entry["why"] = "too little unfitted surface between the two levels"
            log.append(entry)
            continue
        # keep the pieces of the band that touch both flats
        ring = SPLIT_EDGE_RING_MM
        tA, tB = dA[band] <= ring, dB[band] <= ring
        loc = np.full(len(W), -1, dtype=np.int64)
        loc[ci] = np.arange(len(ci))
        el = loc[adj[(loc[adj[:, 0]] >= 0) & (loc[adj[:, 1]] >= 0)]]
        g = coo_matrix((np.ones(len(el)), (el[:, 0], el[:, 1])), shape=(len(ci), len(ci))).tocsr()
        _, cl = connected_components(g, directed=False)
        hA = np.bincount(cl, weights=tA.astype(float)) > 0
        hB = np.bincount(cl, weights=tB.astype(float)) > 0
        keep = hA[cl] & hB[cl]
        ci = ci[keep]
        if float(W[ci].sum()) < FILLET_MIN_MM2:
            entry["why"] = "no unfitted band that runs from one level to the other"
            log.append(entry)
            continue
        # direction across the step: the in-plane lean of the band's faces
        Nin = N[ci] - np.outer(N[ci] @ n, n)
        tvec = np.average(Nin, axis=0, weights=W[ci])
        if np.linalg.norm(tvec) < 1e-6:
            entry["why"] = "the band does not lean one way"
            log.append(entry)
            continue
        t = _unit(tvec)
        # the ramp rises from A to B going against the lean of its normals
        x = C[ci] @ t
        ss = C[ci] @ n
        u = np.clip((ss - sA) / h, 0, 1)
        # start: x where u ~ 0.5, width from the spread of x against u
        mid = np.abs(u - 0.5) < 0.25
        if mid.sum() < 3:
            mid = np.ones(len(ci), dtype=bool)
        xm = float(np.average(x[mid], weights=W[ci][mid]))
        slope = np.polyfit(u, x, 1)[0] if np.ptp(u) > 0.1 else -h
        w0 = float(slope) if abs(slope) > 0.1 else -max(h, 0.5)
        x00 = xm - 0.5 * w0
        vidx, wv, _ = _area_vertices(faces, W, np.isin(np.arange(len(W)), ci))
        P = verts[vidx]
        best = None
        tried = []
        for prof in BLEND_PROFILES:
            try:
                bl = _fit_blend(P, wv, prof, n, t, sA, h, x00, w0)
            except (ValueError, FloatingPointError):
                continue
            # the faces on this blend
            dc = np.abs(blend_residual(C[ci], bl))
            on = ci[dc <= label_dist]
            if float(W[on].sum()) < FILLET_MIN_MM2:
                tried.append({"profile": prof, "on_mm2": round(float(W[on].sum()), 2)})
                continue
            v2, w2, _ = _area_vertices(faces, W, np.isin(np.arange(len(W)), on))
            bl = _fit_blend(verts[v2], w2, prof, n, t, sA, h, bl["x0"], bl["w"])
            r2 = blend_residual(verts[v2], bl)
            rms = float(np.sqrt(np.average(r2 ** 2, weights=w2)))
            tried.append({"profile": prof, **blend_size(bl), "rms_mm": round(rms, 5),
                          "on_mm2": round(float(W[on].sum()), 2)})
            if best is None or rms < best[0] - 0.1 * nf:
                best = (rms, prof, bl)
        entry["profiles"] = tried
        if best is None:
            entry["why"] = "no profile holds enough of the band"
            log.append(entry)
            continue
        rms, prof, bl = best
        dc = np.abs(blend_residual(C[ci], bl))
        fm = np.zeros(len(W), dtype=bool)
        fm[ci[dc <= label_dist]] = True
        fm = _largest_piece(adj, fm, W)
        fm = _trim_border(adj, fm, faces, verts, lambda Q: blend_residual(Q, bl), tol)
        why = []
        if float(W[fm].sum()) < FILLET_MIN_MM2:
            why.append("too little left once the border row is trimmed")
        else:
            vidx, wv, _ = _area_vertices(faces, W, fm)
            pts = verts[vidx]
            res = blend_residual(pts, bl)
            rms = float(np.sqrt(np.average(res ** 2, weights=wv)))
            xs = pts @ t
            ssp = pts @ n
            lo_x, hi_x = min(bl["x0"], bl["x0"] + bl["w"]), max(bl["x0"], bl["x0"] + bl["w"])
            inside = (xs >= lo_x) & (xs <= hi_x)
            span_x = float(np.ptp(xs[inside]) / max(hi_x - lo_x, 1e-9)) if inside.sum() > 1 else 0.0
            span_s = float(np.ptp(ssp) / h)
            # how much of the ramp (over the blend's own length) is on it:
            # a band that only crosses the blend here and there is not one
            e_dir = _unit(np.cross(n, t))
            alf = C[fm] @ e_dir
            xc, ac = C[ci] @ t, C[ci] @ e_dir
            ramp = ((xc >= lo_x) & (xc <= hi_x) & (ac >= alf.min()) & (ac <= alf.max()))
            region = fm.copy()
            region[ci[ramp]] = True
            share = float(W[fm].sum() / W[region].sum())
            entry.update(chosen=prof, **blend_size(bl), rms_mm=round(rms, 5),
                         span_width=round(span_x, 3), span_height=round(span_s, 3),
                         ramp_share=round(share, 3), area_mm2=round(float(W[fm].sum()), 2))
            if share < BLEND_MIN_RAMP_SHARE:
                why.append(f"only {share * 100:.0f}% of the ramp lies on the blend "
                           f"(needs {BLEND_MIN_RAMP_SHARE * 100:.0f}%)")
            if rms > ROUND_MAX_RMS_NOISE * nf:
                why.append(f"fit rms {rms:.3f} mm is over {ROUND_MAX_RMS_NOISE:g} x noise")
            if span_x < BLEND_MIN_SPAN:
                why.append(f"covers {span_x * 100:.0f}% of the ramp's width "
                           f"(needs {BLEND_MIN_SPAN * 100:.0f}%)")
            if min(span_s, 1.0) < BLEND_MIN_SPAN:
                why.append(f"covers {min(span_s, 1) * 100:.0f}% of the step height "
                           f"(needs {BLEND_MIN_SPAN * 100:.0f}%)")
        if why:
            entry["why"] = "; ".join(why)
            log.append(entry)
            continue
        snaps = []
        bl2, txt = _snap_blend(bl, pts, table, tol)
        if txt:
            snaps.append(txt)
            bl = bl2
            res = blend_residual(pts, bl)
        pc = pass_check(pts, wv, res, tol=tol, cap=cap)
        st = _stats(res)
        e = _unit(np.cross(n, t))
        al = pts @ e
        size = blend_size(bl)
        area = {
            "id": len(areas), "type": "blend", "kind": "level_blend",
            "n_faces": int(fm.sum()), "area_mm2": round(float(W[fm].sum()), 2),
            "n_patches": len(_pieces(adj, fm)), "snaps": snaps,
            "blend": {"between_flats": [fA["id"], fB["id"]], **size,
                      "tangent_to_both": prof != "chamfer",
                      "length_mm": round(float(np.ptp(al)), 3),
                      "level_normal": [round(float(x), 6) for x in n],
                      "across": [round(float(x), 6) for x in t],
                      "along": [round(float(x), 6) for x in e]},
            "fit": {**size, **st}, "final": {**size, **st},
            "judged": pc["stats"], "within_tol": pc["stats"]["within_tol"],
            "within_tol_raw": bool(st["p95_mm"] <= tol),
            "_blend": bl, "_pts": pts, "_fmask": fm, "_vidx": vidx,
            "_jres": pc["residual"]}
        entry["accepted_area"] = area["id"]
        log.append(entry)
        pool &= ~fm
        accept(fm, area)
        found.append({"area": area["id"], "between_flats": [fA["id"], fB["id"]], **size,
                      "length_mm": area["blend"]["length_mm"],
                      "area_mm2": area["area_mm2"], "within_tol": area["within_tol"]})
        pidx = np.flatnonzero(pool)
        near = {k: v for k, v in ((f["id"], cKDTree(C[np.flatnonzero(area_lab == f["id"])])
                                   .query(C[pidx], distance_upper_bound=BLEND_REACH_MM)[0])
                                  for f in ids)}
    return {"rule": ("parallel fitted flats facing the same way at different heights, "
                     "joined by an unfitted band: the band is fitted as a straight-swept "
                     "chamfer, ogee round or smooth tangent blend (best fit), with the "
                     "angle, radius or width snapped"),
            "found": found, "tried": log}


# == folding small scraps into the surface they continue ======================
# After all fitting, about a fifth of the pedal adapter is still 'other'. Very
# little of it is one big unexplained region: it is crumbs - the strip a
# flat's edge band gave up, a crumb left between two split pieces, and the
# chart leftovers under the minimum patch (5,436 mm2 of them before the split)
# that touch one another and so never count as small on their own. Many of
# those faces are simply more of the surface next to them. A face joins a
# neighbouring fitted area when, against that area's surface AS FITTED (not
# refitted - the flat stays exactly as straight, the round exactly as round):
#
# - every corner of the face lies within the TOLERANCE of that surface (not
#   the wider join distance: the edge-band trim took off faces more than the
#   tolerance off, and they stay off),
# - its normal agrees with the nearest face of that area within
#   LABEL_ANGLE_DEG,
# - it is connected to that area through faces that also qualify,
# - on a flat, it also passes the same flat-off check (FLAT_*) on the grown
#   area, so faces the flat check sent to 'other' as the start of a curve
#   are not taken back.
#
# The area is then judged again by the 95% rule with the new faces. The fold
# is kept only when an area that passed still passes and an area that missed
# does not miss by more than before; otherwise it is undone piece by piece,
# keeping the pieces that do no harm. Faces that continue no neighbour stay
# uncovered and are reported. Folded faces are measured only, never moved
# into the size-check model.


def surface_residual(a: dict, P: np.ndarray) -> np.ndarray:
    """Signed distance from points to an area's fitted surface."""
    if a["type"] == "flat":
        return plane_residual(P, a["_n"], a["_d"])
    if a["type"] == "round":
        return cyl_residual(P, a["_a"], a["_p"], a["_r"])
    if a["type"] == "blend":
        return blend_residual(P, a["_blend"])
    return spline_distance(P, a["_frame"])


def _rejudge(a, verts, faces, W, fm, *, tol, cap) -> dict:
    vidx, wv, _ = _area_vertices(faces, W, fm)
    pts = verts[vidx]
    res = surface_residual(a, pts)
    if a["type"] == "round":
        pc = pass_check(pts, wv, res, tol=tol, cap=cap, axis=a["_a"], point=a["_p"])
    else:
        pc = pass_check(pts, wv, res, tol=tol, cap=cap)
    return {"fmask": fm, "vidx": vidx, "pts": pts, "res": res, "pc": pc}


def _fold_ok(a, new) -> bool:
    j = new["pc"]["stats"]
    if a["within_tol"]:
        return bool(j["within_tol"])
    return j["p95_mm"] <= a["judged"]["p95_mm"] + 1e-9


def _apply_fold(a, new, W, added, tol):
    st = _stats(new["res"])
    fm = new["fmask"]
    a["_fmask"], a["_vidx"], a["_pts"] = fm, new["vidx"], new["pts"]
    a["_jres"] = new["pc"]["residual"]
    a["n_faces"] = int(fm.sum())
    a["area_mm2"] = round(float(W[fm].sum()), 2)
    keep = {k: v for k, v in a["final"].items() if k not in st}
    a["final"] = {**keep, **st}
    a["judged"] = new["pc"]["stats"]
    a["within_tol"] = a["judged"]["within_tol"]
    a["within_tol_raw"] = bool(st["p95_mm"] <= tol)
    prev = a.get("scraps_folded", {"faces": 0, "area_mm2": 0.0})
    a["scraps_folded"] = {"faces": prev["faces"] + int(added.sum()),
                          "area_mm2": round(prev["area_mm2"] + float(W[added].sum()), 2),
                          "note": "unfitted faces that continue this surface as "
                                  "fitted (not refitted)"}


def fold_scraps(verts, faces, C, N, W, adj, area_lab, areas, *, tol, cap, min_patch,
                flat_lim=None) -> dict:
    """Fold unfitted faces into the fitted area they continue (in place)."""
    nfc = len(W)
    by_id = {a["id"]: a for a in areas}
    other0 = area_lab < 0
    pieces0 = _pieces(adj, other0)
    small0 = [s for s in pieces0 if float(W[s].sum()) < min_patch]
    small_mask0 = np.zeros(nfc, dtype=bool)
    for s_ in small0:
        small_mask0[s_] = True
    cos_t = float(np.cos(np.radians(LABEL_ANGLE_DEG)))
    if flat_lim is None:
        flat_lim = tol
    trees = {}
    folded_by_area: dict[int, float] = {}
    refused = 0
    for _round in range(3):
        other = area_lab < 0
        if not other.any():
            break
        e = adj[other[adj[:, 0]] ^ other[adj[:, 1]]]
        e = np.where(other[e[:, 0]][:, None], e, e[:, ::-1])    # (unfitted, fitted)
        nb = area_lab[e[:, 1]]
        ids, cnt = np.unique(nb, return_counts=True)
        changed = False
        # biggest shared border first: a face goes to the surface it hugs most
        for aid in ids[np.argsort(-cnt, kind="stable")].tolist():
            a = by_id.get(int(aid))
            if a is None or "_fmask" not in a:
                continue
            free = area_lab < 0
            touch = np.unique(e[(nb == aid) & free[e[:, 0]], 0])
            if len(touch) == 0:
                continue
            # the unfitted faces near this area (connected region around it)
            region = np.zeros(nfc, dtype=bool)
            seedm = np.zeros(nfc, dtype=bool)
            seedm[touch] = True
            for piece in _pieces(adj, free):
                if seedm[piece].any():
                    region[piece] = True
            ci = np.flatnonzero(region)
            dv = np.abs(surface_residual(a, verts[faces[ci]].reshape(-1, 3))).reshape(-1, 3).max(axis=1)
            ok = dv <= tol
            if aid not in trees:
                af = np.flatnonzero(a["_fmask"])
                trees[aid] = (cKDTree(C[af]), af)
            tr, af = trees[aid]
            _, nn = tr.query(C[ci])
            ok &= np.einsum("ij,ij->i", N[ci], N[af[nn]]) >= cos_t
            good = np.zeros(nfc, dtype=bool)
            good[ci[ok]] = True
            grown = np.zeros(nfc, dtype=bool)
            for piece in _pieces(adj, good):
                if seedm[piece].any():
                    grown[piece] = True
            if not grown.any():
                continue
            if a["type"] == "flat":
                for _ in range(FLAT_PASSES):
                    off = flat_off_faces(verts, faces, C, N, W, a["_fmask"] | grown,
                                         a["_n"], a["_d"], limit=flat_lim) & grown
                    if not off.any():
                        break
                    grown &= ~off
                    keep = np.zeros(nfc, dtype=bool)
                    for piece in _pieces(adj, grown):
                        if seedm[piece].any():
                            keep[piece] = True
                    grown = keep
                if not grown.any():
                    continue
            new = _rejudge(a, verts, faces, W, a["_fmask"] | grown, tol=tol, cap=cap)
            if not _fold_ok(a, new):
                # piece by piece, biggest first, keeping those that do no harm
                new = None
                acc = np.zeros(nfc, dtype=bool)
                for piece in sorted(_pieces(adj, grown), key=lambda q: -float(W[q].sum())):
                    add = np.zeros(nfc, dtype=bool)
                    add[piece] = True
                    trial = _rejudge(a, verts, faces, W, a["_fmask"] | acc | add,
                                     tol=tol, cap=cap)
                    if _fold_ok(a, trial):
                        acc |= add
                        new = trial
                    else:
                        refused += 1
                grown = acc
                if new is None:
                    continue
            _apply_fold(a, new, W, grown, tol)
            area_lab[grown] = a["id"]
            trees.pop(aid, None)
            folded_by_area[int(aid)] = folded_by_area.get(int(aid), 0.0) + float(W[grown].sum())
            changed = True
        if not changed:
            break
    left = area_lab < 0
    left_pieces = _pieces(adj, left)
    left_small = [s_ for s_ in left_pieces if float(W[s_].sum()) < min_patch]
    biggest = sorted(left_pieces, key=lambda q: -float(W[q].sum()))[:10]
    folded_small = float(W[small_mask0 & (area_lab >= 0)].sum())
    return {
        "rule": ("an unfitted face joins the fitted area next to it when every "
                 f"corner lies within the tolerance ({tol:.4f} mm) of that area's "
                 f"surface as fitted, its normal is within {LABEL_ANGLE_DEG:g} deg "
                 "of the area's nearest face, it connects to the area through such "
                 "faces and, on a flat, it passes the flat-off check on the grown "
                 "area; kept only when an area that passed still passes and one "
                 "that missed misses by no more than before. Surfaces are not "
                 "refitted. Not in the size check."),
        "uncovered_before_mm2": round(float(W[other0].sum()), 2),
        "small_scraps_before_mm2": round(float(W[small_mask0].sum()), 2),
        "n_small_scraps_before": len(small0),
        "folded_mm2": round(float(sum(folded_by_area.values())), 2),
        "folded_from_small_scraps_mm2": round(folded_small, 2),
        "folded_by_area": {str(k): round(v, 2) for k, v in
                           sorted(folded_by_area.items(), key=lambda t: -t[1])},
        "pieces_refused_as_harmful": refused,
        "uncovered_after_mm2": round(float(W[left].sum()), 2),
        "small_scraps_after_mm2": round(float(sum(W[q].sum() for q in left_small)), 2),
        "n_small_scraps_after": len(left_small),
        "left_biggest": [{"area_mm2": round(float(W[q].sum()), 2),
                          "centre_mm": [round(float(x), 2) for x in
                                        np.average(C[q], axis=0, weights=W[q])]}
                         for q in biggest],
        "in_size_check": False,
    }


# == review pictures ==========================================================

REVIEW_MAX_CLOSEUPS = 40


def face_deviation(mesh, area_lab, areas, judged: bool = False) -> np.ndarray:
    """Signed distance of each face centre from its area's final surface.

    Positive = the averaged scan sits outside the fitted surface. NaN for
    "other" faces, which have no fitted surface to deviate from yet. With
    `judged`, each face shows the mean of its corners' judged distances -
    the texture-smoothed values the pass rule compares.
    """
    C = np.asarray(mesh.triangles_center, float)
    F = np.asarray(mesh.faces)
    dev = np.full(len(C), np.nan)
    for a in areas:
        m = area_lab == a["id"]
        if judged and "_jres" in a:
            dv = np.full(len(mesh.vertices), np.nan)
            dv[a["_vidx"]] = a["_jres"]
            r = dv[F[m]].mean(axis=1)
            dev[m] = -r if (a["kind"] == "hole" or a.get("_concave")) else r
            continue
        if a["type"] == "flat":
            dev[m] = plane_residual(C[m], a["_n"], a["_d"])
        elif a["type"] == "freeform":
            dev[m] = spline_distance(C[m], a["_frame"])
        elif a["type"] == "blend":
            dev[m] = blend_residual(C[m], a["_blend"])
        else:
            r = cyl_residual(C[m], a["_a"], a["_p"], a["_r"])
            dev[m] = -r if (a["kind"] == "hole" or a.get("_concave")) else r
    return dev


def render_review(mesh, faces, verts, areas, area_lab, bad, review_dir: Path, *,
                  tol: float, stopped: str | None) -> list[str]:
    from ..review import deviation_colours, render_closeup, render_views

    review_dir.mkdir(parents=True, exist_ok=True)
    for old in review_dir.glob("30_*.png"):
        old.unlink()        # pictures from an earlier fit of this run
    dev = face_deviation(mesh, area_lab, areas, judged=True)
    limit = 3 * tol
    rgb = deviation_colours(dev, limit)
    paths = []
    sub = (f"{len(bad)} of {len(areas)} areas outside {tol} mm (95% of points); "
           f"grey = still uncovered")
    if stopped:
        sub = "SIZE CHECK STOPPED THE RUN: " + stopped
    paths.append(render_views(
        mesh, rgb, review_dir / "30_deviation_overview.png",
        title="Fit deviation: averaged scan (texture smoothed) vs fitted surfaces",
        subtitle=sub, limit=limit,
        cbar_label="smoothed scan minus fitted surface (mm)"))
    for a in sorted(bad, key=lambda a: -a.get("judged", a["final"])["p95_mm"])[:REVIEW_MAX_CLOSEUPS]:
        m = area_lab == a["id"]
        local = np.tile(np.array([0.85, 0.85, 0.85]), (len(dev), 1))
        local[m] = rgb[m]
        size = (f"d{a['final']['diameter_mm']:.3f} mm" if a["type"] == "round"
                else f"{a['area_mm2']:.0f} mm2")
        f = a["final"]
        jp = a.get("judged", f)["p95_mm"]
        paths.append(render_closeup(
            mesh, local, m,
            review_dir / f"30_area_{a['id']:02d}_{a['kind']}.png",
            title=f"Area {a['id']} ({a['kind']}, {size}) outside tolerance",
            subtitle=(f"smoothed p95 {jp:.3f} (raw {f['p95_mm']:.3f})  max "
                      f"{f['max_mm']:.3f}  rms {f['rms_mm']:.3f} mm  vs tol {tol} mm; "
                      f"light grey = rest of the part"),
            limit=limit, cbar_label="smoothed scan minus fitted surface (mm)"))
    if len(bad) > REVIEW_MAX_CLOSEUPS:
        paths.append(f"(close-ups limited to the worst {REVIEW_MAX_CLOSEUPS} "
                     f"of {len(bad)} areas; all are in the overview)")
    patches = [a for a in areas if a.get("type") == "freeform"]
    if patches:
        a = max(patches, key=lambda a: a["judged"]["p95_mm"])
        m = area_lab == a["id"]
        local = np.tile(np.array([0.85, 0.85, 0.85]), (len(dev), 1))
        local[m] = rgb[m]
        f = a["final"]
        jp = a["judged"]["p95_mm"]
        flag = "within" if a["within_tol"] else "outside"
        paths.append(render_closeup(
            mesh, local, m,
            review_dir / "30_worst_patch.png",
            title=(f"Worst freeform patch {a['id']} ({a['area_mm2']:.0f} mm2) "
                   f"{flag} tolerance"),
            subtitle=(f"stiff spline, smoothed p95 {jp:.3f} (raw {f['p95_mm']:.3f})  "
                      f"max {f['max_mm']:.3f}  rms {f['rms_mm']:.3f} mm  vs tol {tol} mm; "
                      f"light grey = rest of the part"),
            limit=limit, cbar_label="smoothed scan minus fitted surface (mm)"))
    return [str(p) for p in paths]


# == shaded picture of the fitted surfaces =====================================
# the user judges the result by eye. This picture shows the fitted surfaces
# themselves, not the scan and not a heat map: every scan vertex is moved onto
# its area's fitted surface (flats come out dead flat, rounds dead round) and
# the result is shaded like a solid. Faces still uncovered keep the scan's
# shape and are tinted, so the gaps are visible. Measuring only - nothing
# here feeds the fit, the snaps or the size check.

def fitted_vertices(verts, faces, areas, area_lab) -> np.ndarray:
    """Scan vertices moved onto their area's fitted surface (others kept)."""
    out = np.asarray(verts, float).copy()
    for a in sorted(areas, key=lambda a: a["area_mm2"]):
        fm = area_lab == a["id"]
        if not fm.any():
            continue
        vi = np.unique(faces[fm])
        P = verts[vi]
        if a["type"] == "flat":
            out[vi] = P - np.outer(plane_residual(P, a["_n"], a["_d"]), a["_n"])
        elif a["type"] == "round":
            rel = P - a["_p"]
            perp = rel - np.outer(rel @ a["_a"], a["_a"])
            uh = perp / np.maximum(np.linalg.norm(perp, axis=1), 1e-12)[:, None]
            out[vi] = P - cyl_residual(P, a["_a"], a["_p"], a["_r"])[:, None] * uh
        elif a["type"] == "blend":
            bl = a["_blend"]
            xy = np.column_stack([P @ bl["t"], P @ bl["n"]])
            ft = _polyline_foot(blend_curve(bl, 2000), xy)
            out[vi] = P + np.outer(ft[:, 0] - xy[:, 0], bl["t"]) + np.outer(ft[:, 1] - xy[:, 1], bl["n"])
        elif "_frame" in a:
            fr = a["_frame"]
            # straight down the chart normal onto the spline
            res = spline_distance(P, fr)
            out[vi] = P - np.outer(res, fr["n"])
    return out


def render_fitted_shaded(mesh, verts, faces, areas, area_lab, out_path: Path, *,
                         title: str, focus=None, focus_mm: float = 14.0,
                         focus_axis=None, focus_depth_mm: float = 4.0,
                         fitted=None) -> Path:
    """Four shaded views of the fitted surfaces; with `focus` (a point), a
    close-up of the part within `focus_mm` of it (with `focus_axis`, within
    `focus_mm` of that axis and `focus_depth_mm` of the point along it, so
    walls behind a small feature do not hide it)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    from ..preview import RENDER_FACE_BUDGET

    fv = fitted_vertices(verts, faces, areas, area_lab) if fitted is None else fitted
    m = trimesh.Trimesh(vertices=fv, faces=faces, process=False)
    lab = area_lab
    if focus is not None:
        rel = np.asarray(m.triangles_center) - np.asarray(focus)
        if focus_axis is None:
            keep = np.linalg.norm(rel, axis=1) <= focus_mm
        else:
            ax_ = _unit(focus_axis)
            al_ = rel @ ax_
            keep = ((np.linalg.norm(rel - np.outer(al_, ax_), axis=1) <= focus_mm)
                    & (np.abs(al_) <= focus_depth_mm))
        m = trimesh.Trimesh(vertices=fv, faces=faces[keep], process=False)
        lab = area_lab[keep]
    elif len(m.faces) > 4 * RENDER_FACE_BUDGET:
        try:
            m2 = m.simplify_quadric_decimation(face_count=4 * RENDER_FACE_BUDGET)
            _, idx = cKDTree(np.asarray(m.triangles_center)).query(np.asarray(m2.triangles_center))
            lab, m = area_lab[idx], m2
        except Exception:       # no decimator available: draw every face
            pass
    tris = np.asarray(m.triangles, float)
    nrm = np.asarray(m.face_normals, float)
    base = np.where((lab >= 0)[:, None], np.array([0.78, 0.80, 0.84]),
                    np.array([0.93, 0.62, 0.38]))
    tc = tris.reshape(-1, 3)
    lo_b, hi_b = tc.min(0), tc.max(0)
    c = (lo_b + hi_b) / 2 if focus is None else np.asarray(focus, float)
    span = float((hi_b - lo_b).max()) * 0.58 if focus is None else focus_mm * 0.75
    views = []
    for name, R in (
            ("Front (-Y)", np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)),
            ("Top (-Z)", np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], float)),
            ("Bottom (+Z)", np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], float)),
            ("Iso", None)):
        if R is None:
            az, el = np.radians(-50), np.radians(30 if focus is None else -35)
            Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
            Rx = np.array([[1, 0, 0], [0, np.cos(el - np.pi / 2), -np.sin(el - np.pi / 2)],
                           [0, np.sin(el - np.pi / 2), np.cos(el - np.pi / 2)]])
            R = Rx @ Rz
        views.append((name, R))
    fig, axes = plt.subplots(2, 2, figsize=(14, 13))
    light = _unit([0.35, 0.45, 0.82])
    for ax, (name, R) in zip(axes.ravel(), views):
        T = (tris - c) @ R.T
        nv = nrm @ R.T
        # painter's order (far first); the scan's normals are not trusted for
        # culling, so the side facing the viewer is lit either way
        order = np.argsort(T[:, :, 2].mean(axis=1))
        facing = np.where(nv[:, 2:3] < 0, -nv, nv)
        inten = 0.22 + 0.78 * np.clip(facing @ light, 0, 1)
        col = base * inten[:, None]
        ax.add_collection(PolyCollection(T[order][:, :, :2], facecolors=col[order],
                                         edgecolors="none", antialiased=False))
        ax.set_xlim(-span, span)
        ax.set_ylim(-span, span)
        ax.set_aspect("equal")
        ax.set_title(name, fontsize=10)
        ax.axis("off")
    fig.suptitle(title, fontsize=12, weight="bold")
    fig.text(0.5, 0.01, "grey = fitted surfaces (flats, rounds, blends, stiff curves); "
             "orange = still uncovered scan", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    return out_path


# == area map image ===========================================================

def render_area_map(mesh, area_lab, areas, out_path: Path, *, tol: float) -> Path:
    """Three orthographic views, each face coloured by its area, other grey."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Patch

    from ..preview import RENDER_FACE_BUDGET, VIEWS

    m = mesh
    lab = area_lab
    if len(m.faces) > RENDER_FACE_BUDGET:
        m = mesh.simplify_quadric_decimation(face_count=RENDER_FACE_BUDGET)
        tree = cKDTree(np.asarray(mesh.triangles_center))
        _, idx = tree.query(np.asarray(m.triangles_center))
        lab = area_lab[idx]

    cmap = plt.get_cmap("tab20")
    base = np.array([[0.72, 0.72, 0.72]] * len(lab))
    for a in areas:
        base[lab == a["id"]] = cmap(a["id"] % 20)[:3]

    tris = np.asarray(m.triangles, float)
    normals = np.asarray(m.face_normals, float)
    light = _unit([0.3, 0.4, 0.87])
    inten = 0.45 + 0.55 * np.clip(np.abs(normals @ light), 0, 1)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.6))
    lo, hi = m.bounds
    span = float((hi - lo).max()) * 0.6
    centre = (lo + hi) / 2
    for ax, (name, (i, j), _) in zip(axes, VIEWS):
        depth = tris[:, :, 3 - i - j].mean(axis=1)
        order = np.argsort(depth)
        ax.add_collection(PolyCollection(
            tris[order][:, :, [i, j]], facecolors=base[order] * inten[order][:, None],
            edgecolors="none", antialiased=False))
        ax.set_xlim(centre[i] - span, centre[i] + span)
        ax.set_ylim(centre[j] - span, centre[j] + span)
        ax.set_aspect("equal")
        ax.set_title(name, fontsize=9, family="monospace")
        ax.set_xlabel(f"{'XYZ'[i]} (mm)", fontsize=8)
        ax.set_ylabel(f"{'XYZ'[j]} (mm)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, lw=0.3, alpha=0.35)

    handles = []
    for a in areas[:20]:
        size = (f"d{a['final']['diameter_mm']:.2f}" if a["type"] == "round"
                else f"{a['area_mm2']:.0f}mm2")
        flag = "" if a["within_tol"] else " *"
        handles.append(Patch(color=cmap(a["id"] % 20)[:3],
                             label=f"{a['id']}: {a['kind']} {size}{flag}"))
    if len(areas) > 20:
        handles.append(Patch(color="white", label=f"... {len(areas) - 20} more (colours repeat)"))
    handles.append(Patch(color=(0.72, 0.72, 0.72), label="other"))
    fig.legend(handles=handles, loc="lower center", ncol=min(8, len(handles)),
               fontsize=7, frameon=False)
    n_flat = sum(a["type"] == "flat" for a in areas)
    n_round = sum(a["type"] == "round" for a in areas)
    n_free = sum(a["type"] == "freeform" for a in areas)
    fig.suptitle(f"Area map: {n_flat} flat, {n_round} round, {n_free} freeform, "
                 f"{(area_lab < 0).mean() * 100:.0f}% of faces still uncovered   "
                 f"(* = outside {tol} mm)", fontsize=11, weight="bold")
    fig.tight_layout(rect=(0, 0.12, 1, 0.94))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mesh", type=Path, help="averaged scan surface (10_clean.ply)")
    ap.add_argument("frame", type=Path, help="20_frame.json")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--tol", type=float, default=None)
    ap.add_argument("--units", choices=["auto", "metric", "inch"], default="auto")
    a = ap.parse_args()
    try:
        rep = run_fit(a.mesh, a.frame, a.out_dir, tol=a.tol, units=a.units)
    except SizeCheckError as exc:
        sys.stderr.write(f"SIZE CHECK FAILED: {exc}\n")
        sys.stderr.flush()
        sys.exit(3)
    emit({"report": rep["report"], "preview": rep["preview"],
          "labels": rep["labels"], "status": rep["status"],
          "tolerance": rep["tolerance"], "units": rep["units"],
          "summary": rep["summary"], "size_check": rep["size_check"],
          "review": rep["review"]})


if __name__ == "__main__":
    main()
