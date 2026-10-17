"""Measure analytic primitives from a scan.

This is the accuracy backbone of Fairsolid. The AI stages propose topology
and design intent; everything dimensional is measured here, from the full
density scan, by least squares over thousands of samples.

Why not pure RANSAC for planes: a triangulated scan already carries face
normals, and mechanical parts have few distinct normal directions. Grouping
faces by normal and then by offset finds planar regions far more reliably
than random sampling, and gives every region enough support for a stable
least-squares fit. RANSAC is reserved for cylinders, where there is no such
shortcut.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import trimesh
from scipy.spatial import cKDTree


@dataclass
class Plane:
    normal: list          # unit normal, outward
    offset: float         # signed distance from origin: n . x = offset
    area: float           # total area of supporting faces, mm^2
    n_faces: int
    rms: float            # least-squares residual, mm

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Cylinder:
    axis: list
    point: list           # a point on the axis
    radius: float
    n_points: int
    rms: float

    def as_dict(self) -> dict:
        return asdict(self)


def refine_plane(pts: np.ndarray) -> tuple[np.ndarray, float, float]:
    """Total-least-squares plane through pts. Returns (normal, offset, rms).

    SVD rather than a normal-equations fit: scan points are noisy in all
    three axes, so minimising perpendicular distance is the correct
    objective, not vertical distance.
    """
    centroid = pts.mean(axis=0)
    centred = pts - centroid
    # Smallest right-singular vector is the direction of least variance.
    _, _, vh = np.linalg.svd(centred, full_matrices=False)
    normal = vh[-1]
    normal = normal / np.linalg.norm(normal)
    offset = float(np.dot(normal, centroid))
    rms = float(np.sqrt(np.mean((centred @ normal) ** 2)))
    return normal, offset, rms


def extract_planes(
    mesh: trimesh.Trimesh,
    *,
    thresh: float = 0.4,
    min_area_frac: float = 0.01,
    n_samples: int = 120_000,
    max_planes: int = 24,
    seed: int = 0,
) -> list[Plane]:
    """Find planar regions by RANSAC on point-to-plane DISTANCE.

    Normals are deliberately not the clustering signal. At realistic scan
    resolution (0.35 mm spacing, 0.04 mm sensor noise) face-normal error runs
    to a median of 8 deg and a p90 of 20 deg, which shreds any normal-space
    clustering. Point positions stay accurate to ~0.17 mm over the same data,
    so distance is the signal with headroom and normals are demoted to a
    consistency check.

    thresh          mm; inlier band half-width. Set from measured scan noise,
                    roughly 2-3x the p95 point error.
    min_area_frac   stop once a plane supports less than this share of samples
    """
    rng = np.random.default_rng(seed)
    pts = sample_surface(mesh, n_samples, seed=seed)

    # Nearest face normal per sample, used only to reject a plane that
    # happens to slice through the solid rather than lie on its skin.
    face_normals = np.asarray(mesh.face_normals, dtype=float)
    face_tree = cKDTree(np.asarray(mesh.triangles_center, dtype=float))

    total_area = float(mesh.area)
    remaining = np.ones(len(pts), dtype=bool)
    min_support = max(64, int(len(pts) * min_area_frac))
    planes: list[Plane] = []

    for _ in range(max_planes):
        idx_pool = np.flatnonzero(remaining)
        if idx_pool.size < min_support:
            break
        pool = pts[idx_pool]

        best_normal, best_offset, best_count = None, 0.0, 0
        n_iter = 400
        for _ in range(n_iter):
            tri = pool[rng.integers(0, len(pool), 3)]
            v1, v2 = tri[1] - tri[0], tri[2] - tri[0]
            nrm = np.cross(v1, v2)
            norm_len = np.linalg.norm(nrm)
            if norm_len < 1e-9:
                continue
            nrm = nrm / norm_len
            off = float(np.dot(nrm, tri[0]))
            count = int(np.count_nonzero(np.abs(pool @ nrm - off) <= thresh))
            if count > best_count:
                best_normal, best_offset, best_count = nrm, off, count

        if best_normal is None or best_count < min_support:
            break

        # Refine: alternate least-squares fit and inlier re-collection so the
        # plane settles on the true surface instead of the random seed triple.
        normal, offset = best_normal, best_offset
        for _ in range(6):
            inl = np.abs(pool @ normal - offset) <= thresh
            if inl.sum() < 3:
                break
            normal, offset, rms = refine_plane(pool[inl])
        inl = np.abs(pool @ normal - offset) <= thresh
        if inl.sum() < min_support:
            remaining[idx_pool[np.abs(pool @ normal - offset) <= thresh]] = False
            continue
        normal, offset, rms = refine_plane(pool[inl])

        # Orient outward. A least-squares plane has an arbitrary normal
        # sign; the mesh's own face normals are too noisy to trust
        # individually but their MEAN over a region is reliable, because the
        # per-face error is zero-mean.
        sel = pool[inl]
        probe = sel[rng.integers(0, len(sel), min(512, len(sel)))]
        _, near = face_tree.query(probe)
        mean_face_n = face_normals[near].mean(axis=0)
        if np.dot(normal, mean_face_n) < 0:
            normal, offset = -normal, -offset

        area = total_area * (inl.sum() / len(pts))
        planes.append(Plane(
            normal=normal.tolist(), offset=float(offset), area=area,
            n_faces=int(inl.sum()), rms=float(rms),
        ))
        remaining[idx_pool[inl]] = False

    planes.sort(key=lambda p: -p.area)
    return planes


def refine_cylinder(pts: np.ndarray, axis: np.ndarray,
                    point: np.ndarray) -> tuple[float, float]:
    """Least-squares radius for a fixed axis. Returns (radius, rms)."""
    axis = axis / np.linalg.norm(axis)
    rel = pts - point
    perp = rel - np.outer(rel @ axis, axis)
    dists = np.linalg.norm(perp, axis=1)
    radius = float(dists.mean())
    rms = float(np.sqrt(np.mean((dists - radius) ** 2)))
    return radius, rms


def sample_surface(mesh: trimesh.Trimesh, n: int, seed: int = 0) -> np.ndarray:
    """Area-weighted surface samples - the input every fit expects."""
    pts, _ = trimesh.sample.sample_surface(mesh, n, seed=seed)
    return np.asarray(pts, dtype=float)


def extract_cylinders(
    mesh: trimesh.Trimesh,
    axes: list[np.ndarray],
    *,
    thresh: float = 0.4,
    min_points: int = 300,
    n_samples: int = 120_000,
    max_per_axis: int = 28,
    max_rms: float | None = None,
    seed: int = 0,
) -> list[Cylinder]:
    """Find bores and bosses by looking for circles along known axes.

    Generic 3D cylinder RANSAC is slow and unstable on scan data. Mechanical
    parts make it unnecessary: holes and bosses are almost always drilled
    along one of the part's principal directions, and stage 20 has already
    measured those from the planes. Projecting onto the plane perpendicular
    to a candidate axis turns cylinder-fitting into 2D circle-fitting, which
    is both faster and far better conditioned.

    max_rms rejects phantoms. Viewed end-on, the two long edges of a plate
    fit a circle of roughly the plate thickness, and that false cylinder is
    otherwise indistinguishable by size or arc coverage. It is distinguishable
    by residual: a real bore fits to the scan's noise floor (~0.02 mm here)
    while a phantom sits an order of magnitude worse (~0.18 mm). Leave it None
    and the caller should pass the noise floor measured from the plane fits.
    """
    if max_rms is None:
        max_rms = float("inf")
    rng = np.random.default_rng(seed)
    pts = sample_surface(mesh, n_samples, seed=seed)
    normals = _sample_normals(mesh, pts)
    found: list[Cylinder] = []

    for axis in axes:
        axis = np.asarray(axis, dtype=float)
        axis = axis / np.linalg.norm(axis)

        # A point lies on a cylinder about `axis` only if its surface normal
        # is perpendicular to that axis. This one test removes every planar
        # face and every hole belonging to a different axis.
        perpendicular = np.abs(normals @ axis) < 0.25
        if perpendicular.sum() < min_points:
            continue

        # Build a 2D basis perpendicular to the axis and project.
        u = np.cross(axis, [1.0, 0.0, 0.0])
        if np.linalg.norm(u) < 1e-6:
            u = np.cross(axis, [0.0, 1.0, 0.0])
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)

        sel = pts[perpendicular]
        proj = np.column_stack([sel @ u, sel @ v])
        remaining = np.ones(len(proj), dtype=bool)

        for _ in range(max_per_axis):
            pool_idx = np.flatnonzero(remaining)
            if pool_idx.size < min_points:
                break
            pool = proj[pool_idx]

            best, best_count = None, 0
            for _ in range(300):
                tri = pool[rng.integers(0, len(pool), 3)]
                circ = _circle_through(tri)
                if circ is None:
                    continue
                cx, cy, r = circ
                if r < 0.5 or r > 0.5 * np.ptp(pool, axis=0).max():
                    continue
                d = np.abs(np.hypot(pool[:, 0] - cx, pool[:, 1] - cy) - r)
                count = int(np.count_nonzero(d <= thresh))
                if count > best_count:
                    best, best_count = circ, count

            if best is None or best_count < min_points:
                break
            # Note: rejected candidates still consume a slot, so max_per_axis
            # must be generous. At 12 the four corner holes on the test part
            # were never reached - phantoms ate the budget first.

            cx, cy, r = best
            for _ in range(5):
                d = np.abs(np.hypot(pool[:, 0] - cx, pool[:, 1] - cy) - r)
                inl = d <= thresh
                if inl.sum() < 3:
                    break
                cx, cy, r = _fit_circle(pool[inl])
            d = np.abs(np.hypot(pool[:, 0] - cx, pool[:, 1] - cy) - r)
            inl = d <= thresh
            if inl.sum() < min_points:
                remaining[pool_idx[inl]] = False
                continue

            # Require the arc to be reasonably complete, or a shallow fillet
            # reads as a giant phantom bore.
            ang = np.arctan2(pool[inl][:, 1] - cy, pool[inl][:, 0] - cx)
            coverage = np.count_nonzero(
                np.histogram(ang, bins=36, range=(-np.pi, np.pi))[0] > 0
            ) / 36.0

            if coverage >= 0.55 and float(np.sqrt(np.mean(d[inl] ** 2))) <= max_rms:
                centre3d = cx * u + cy * v
                rms = float(np.sqrt(np.mean((d[inl] - 0.0) ** 2)))
                found.append(Cylinder(
                    axis=axis.tolist(), point=centre3d.tolist(),
                    radius=float(r), n_points=int(inl.sum()), rms=rms,
                ))
            remaining[pool_idx[inl]] = False

    found.sort(key=lambda c: -c.n_points)
    return found


def _sample_normals(mesh: trimesh.Trimesh, pts: np.ndarray) -> np.ndarray:
    """Face normal of the triangle nearest each sample point."""
    tree = cKDTree(np.asarray(mesh.triangles_center, dtype=float))
    _, idx = tree.query(pts)
    return np.asarray(mesh.face_normals, dtype=float)[idx]


def _circle_through(tri: np.ndarray):
    """Circumcircle of three 2D points, or None if they are collinear."""
    (x1, y1), (x2, y2), (x3, y3) = tri
    d = 2.0 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-12:
        return None
    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1)
          + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3)
          + (x3**2 + y3**2) * (x2 - x1)) / d
    return ux, uy, float(np.hypot(x1 - ux, y1 - uy))


def _fit_circle(p: np.ndarray):
    """Algebraic (Kasa) least-squares circle - linear, so no convergence risk."""
    x, y = p[:, 0], p[:, 1]
    A = np.column_stack([x, y, np.ones(len(x))])
    b = x**2 + y**2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    r = float(np.sqrt(sol[2] + cx**2 + cy**2))
    return cx, cy, r


def noise_floor(planes: list[Plane]) -> float:
    """Estimate scan noise (mm) from plane-fit residuals.

    Planes are the most over-determined fit available - thousands of points
    on a surface with two degrees of freedom - so their residual is the
    cleanest estimate of sensor noise the scan can give us. Everything else
    downstream is thresholded against it rather than against a magic number.

    Only well-supported planes count. A plane's residual is sensor noise plus
    form error, and small marginal regions are dominated by the latter; taking
    the median over every plane found (including junk) inflated the estimate
    by 6x in testing. The 25th percentile over the larger half is close to
    pure noise.
    """
    if not planes:
        return 0.1
    ranked = sorted(planes, key=lambda p: -p.area)
    major = ranked[: max(3, len(ranked) // 2)]
    return float(np.percentile([p.rms for p in major], 25))


# Share of a plane's band points that must sit in the middle quarter of the
# band (|d| <= band/4) for the plane to count as a real face when measuring
# noise. Points spread evenly across the band - a chord across a curve - put
# 25% there; a face whose noise sigma is half the band puts about 40%.
NOISE_CORE_MIN = 0.4
NOISE_TRIM_SIGMA = 3.0


def plane_noise(pts: np.ndarray, normal, offset: float, band: float,
                *, iters: int = 10) -> dict:
    """Robust noise of one plane, measured on the face, not on its band.

    `pts` are surface samples; those within `band` of the plane are the
    capture. Their plain rms is set by the band as much as by the scan: a
    0.4 mm band picks up rib feet, fillets and the next curve along with
    the face, and a chord across a curve fills the band evenly (rms about
    band/sqrt(3)). So: refit the plane, take a robust sigma (1.4826 x the
    median absolute deviation), keep only points within NOISE_TRIM_SIGMA
    sigma, refit, repeat until the kept set stops changing. `core` is the
    share of the band's points in its middle quarter - the test for a real
    face (NOISE_CORE_MIN).
    """
    n = np.asarray(normal, float)
    sel = pts[np.abs(pts @ n - offset) <= band]
    if len(sel) < 16:
        return {"sigma": float("nan"), "core": 0.0, "n": int(len(sel)), "kept": 0.0}
    n2, d2, _ = refine_plane(sel)
    r = sel @ n2 - d2
    core = float(np.mean(np.abs(r) <= band / 4))
    keep = np.ones(len(sel), dtype=bool)
    sigma = float("nan")
    for _ in range(iters):
        n2, d2, _ = refine_plane(sel[keep])
        r = sel @ n2 - d2
        med = float(np.median(r[keep]))
        sigma = 1.4826 * float(np.median(np.abs(r[keep] - med)))
        new = np.abs(r - med) <= NOISE_TRIM_SIGMA * sigma
        if new.sum() < 16 or (new == keep).all():
            break
        keep = new
    return {"sigma": sigma, "core": core, "n": int(len(sel)),
            "kept": float(keep.mean())}


def surface_noise(mesh: trimesh.Trimesh, planes: list[Plane], *, band: float,
                  n_samples: int = 120_000, seed: int = 0) -> tuple[float, dict]:
    """Scan noise (mm) measured on the clean flat faces.

    noise_floor() takes the plane-finder's own rms, which is the rms of
    everything inside its capture band. On a cast or busy part most
    "planes" RANSAC returns are chords across curves (pedal adapter: 17 of
    23), and even the real faces carry their neighbours' edges in the band,
    so the estimate came out at the band's level (0.179 mm against flat
    faces that fit to 0.06-0.09 mm rms). Here each plane gets a robust,
    trimmed sigma (plane_noise); chords are left out (core share below
    NOISE_CORE_MIN); and the estimate is the 25th percentile over the
    larger half of the real faces, as in noise_floor(). Falls back to
    noise_floor() when no plane qualifies.
    """
    pts = sample_surface(mesh, n_samples, seed=seed)
    rows = []
    for p in sorted(planes, key=lambda p: -p.area):
        ev = plane_noise(pts, p.normal, p.offset, band)
        rows.append({"area_mm2": round(float(p.area), 1),
                     "capture_rms_mm": round(float(p.rms), 5),
                     "sigma_mm": round(ev["sigma"], 5) if np.isfinite(ev["sigma"]) else None,
                     "core_share": round(ev["core"], 3),
                     "real_face": bool(ev["core"] >= NOISE_CORE_MIN and np.isfinite(ev["sigma"]))})
    real = [r for r in rows if r["real_face"]]
    old = noise_floor(planes)
    if not real:
        return old, {"method": "capture-band rms (no plane passed the face test)",
                     "capture_band_estimate_mm": round(old, 5), "planes": rows}
    major = real[: max(3, len(real) // 2)]
    nf = float(np.percentile([r["sigma_mm"] for r in major], 25))
    return nf, {
        "method": (f"robust sigma (median absolute deviation, trimmed at "
                   f"{NOISE_TRIM_SIGMA:g} sigma) of each real flat face; 25th "
                   f"percentile over the larger half of the {len(real)} real "
                   f"faces. A plane is a real face when at least "
                   f"{NOISE_CORE_MIN * 100:.0f}% of its {band:g} mm capture band "
                   f"sits in the band's middle quarter; the rest are chords "
                   f"across curves."),
        "capture_band_estimate_mm": round(old, 5),
        "n_planes": len(rows), "n_real_faces": len(real), "n_used": len(major),
        "planes": rows,
    }


def dedupe_cylinders(cyls: list[Cylinder], *, tol: float = 0.3) -> list[Cylinder]:
    """Merge cylinders that are the same physical feature found twice."""
    kept: list[Cylinder] = []
    for c in cyls:
        ax, pt = np.asarray(c.axis), np.asarray(c.point)
        for k in kept:
            kax, kpt = np.asarray(k.axis), np.asarray(k.point)
            if abs(float(np.dot(ax, kax))) < 0.99:
                continue
            if abs(c.radius - k.radius) > tol:
                continue
            delta = pt - kpt
            if np.linalg.norm(delta - np.dot(delta, kax) * kax) <= tol:
                break
        else:
            kept.append(c)
    return kept


def extract_holes(
    mesh: trimesh.Trimesh,
    axes: list[np.ndarray],
    *,
    normals: np.ndarray | None = None,
    exclude: np.ndarray | None = None,
    thresh: float = 0.4,
    r_min: float = 1.0,
    r_max: float = 60.0,
    min_area: float = 4.0,
    min_coverage: float = 0.6,
    max_rms: float | None = None,
    angle_deg: float = 30.0,
    max_per_axis: int = 40,
    max_rejects: int = 15,
    vote_cap: int = 20_000,
    seed: int = 0,
) -> list[Cylinder]:
    """Find bores and through-holes by normal-directed circle voting.

    extract_cylinders() samples three points from EVERY face square to an
    axis. On a real part that pool is tens of thousands of points, so the
    chance of drawing three from one small hole is about (hole share)^3 -
    on the pedal adapter a 6 mm through-hole is ~0.3% of the pool, one in
    37 million per draw. Small holes were simply never tried.

    Here every face votes instead. A hole's wall faces its own axis (the
    surface is oriented outward, i.e. into the empty hole), so a face at 2D
    position p with in-plane normal m votes for an axis at p + r m, for
    every candidate radius r. A real hole piles its whole wall into one
    cell at one radius; a flat wall smears its votes along a line. The best
    peak is refined by least squares on the faces that lie on that circle
    AND face its centre, then must cover min_coverage of the turn and fit
    to max_rms. Bosses (walls facing away) never vote, so this finds holes
    only; extract_cylinders keeps finding bosses.

    exclude     faces already explained by a flat face (they vote in lines
                and only add noise)
    normals     per-face normals; defaults to the mesh's face normals
    vote_cap    at most this many faces vote per round (an area-weighted
                random draw); the refit always uses every face
    max_rejects stop an axis after this many peaks in a row fail the checks
    """
    C = np.asarray(mesh.triangles_center, dtype=float)
    N = np.asarray(mesh.face_normals if normals is None else normals, dtype=float)
    W = np.asarray(mesh.area_faces, dtype=float)
    cos_in = np.cos(np.radians(angle_deg))
    sin_perp = np.sin(np.radians(angle_deg))
    rng = np.random.default_rng(seed)
    found: list[Cylinder] = []

    for axis in axes:
        a = np.asarray(axis, dtype=float)
        a = a / np.linalg.norm(a)
        helper = np.eye(3)[int(np.argmin(np.abs(a)))]
        u = np.cross(a, helper)
        u /= np.linalg.norm(u)
        v = np.cross(a, u)
        sel = np.abs(N @ a) < sin_perp
        if exclude is not None:
            sel &= ~exclude
        idx = np.flatnonzero(sel)
        if idx.size < 10:
            continue
        P = np.column_stack([C[idx] @ u, C[idx] @ v])
        M = np.column_stack([N[idx] @ u, N[idx] @ v])
        M /= np.maximum(np.linalg.norm(M, axis=1), 1e-12)[:, None]
        w = W[idx]
        alive = np.ones(len(idx), dtype=bool)
        lo, hi = P.min(axis=0), P.max(axis=0)
        top = min(r_max, 0.5 * float((hi - lo).max()))
        radii, r = [], r_min
        while r <= top:
            radii.append(r)
            r += max(0.25, 0.03 * r)

        def on_ring(c, r):
            d = P - c
            dist = np.linalg.norm(d, axis=1)
            facing = -np.einsum("ij,ij->i", d, M) / np.maximum(dist, 1e-12)
            facing_ok = alive & (facing >= cos_in)
            return d, dist, facing_ok & (np.abs(dist - r) <= thresh), facing_ok

        rejects = 0
        for _ in range(max_per_axis):
            if not alive.any() or rejects >= max_rejects:
                break
            best = None
            live = np.flatnonzero(alive)
            scale = 1.0
            if live.size > vote_cap:
                pw = w[live] / w[live].sum()
                scale = float(w[live].sum()) / vote_cap
                live = rng.choice(live, vote_cap, replace=True, p=pw)
            Pa, Ma = P[live], M[live]
            wa = np.full(len(live), scale) if scale != 1.0 else w[live]
            for r in radii:
                cell = max(0.5, 0.06 * r)
                base = lo - r - cell
                nb = np.ceil((hi - lo + 2 * r) / cell).astype(int) + 3
                ij = np.floor((Pa + r * Ma - base) / cell).astype(int)
                acc = np.bincount(ij[:, 0] * nb[1] + ij[:, 1], weights=wa,
                                  minlength=nb[0] * nb[1]).reshape(nb)
                s = acc[:-1, :-1] + acc[1:, :-1] + acc[:-1, 1:] + acc[1:, 1:]
                k = int(np.argmax(s))
                val = float(s.flat[k])
                # Support per unit circumference, so a big circle does not win
                # just by being long; floored at r = 2 mm so the smallest radii
                # (where every concave crease piles up) are not favoured.
                score = val / (2 * np.pi * max(r, 2.0))
                if best is None or score > best[0]:
                    ci, cj = np.unravel_index(k, s.shape)
                    best = (score, r, base + (np.array([ci, cj]) + 1.0) * cell, val, cell)
            if best is None or best[3] < min_area:
                break
            _, r0, c0, _, cell = best
            voters = alive & (np.linalg.norm(P + r0 * M - c0, axis=1) <= 1.5 * cell)
            c, r, ok = c0.copy(), r0, False
            for _ in range(6):
                _, _, inl, _ = on_ring(c, r)
                if inl.sum() < 6:
                    break
                cx, cy, r = _fit_circle_weighted(P[inl], w[inl])
                c, ok = np.array([cx, cy]), True
            good = False
            if ok:
                d, dist, inl, facing_ok = on_ring(c, r)
                if inl.sum() >= 6:
                    ang = np.arctan2(d[inl, 1], d[inl, 0])
                    cov = np.count_nonzero(np.histogram(
                        ang, bins=36, range=(-np.pi, np.pi))[0] > 0) / 36.0
                    res = dist[inl] - r
                    rms = float(np.sqrt(np.average(res ** 2, weights=w[inl])))
                    good = (float(w[inl].sum()) >= min_area and cov >= min_coverage
                            and r >= r_min and (max_rms is None or rms <= max_rms))
                    if good:
                        rejects = 0
                        found.append(Cylinder(
                            axis=a.tolist(), point=(c[0] * u + c[1] * v).tolist(),
                            radius=float(r), n_points=int(inl.sum()), rms=rms))
                        # take the whole wall out, not just the thresh band
                        voters |= facing_ok & (np.abs(dist - r) <= max(thresh, 0.1 * r))
                voters |= inl
            if not good:
                rejects += 1
            if not voters.any():
                break
            alive &= ~voters

    found.sort(key=lambda c: -c.n_points)
    return found


def _fit_circle_weighted(p: np.ndarray, w: np.ndarray):
    """Area-weighted Kasa circle (linear least squares)."""
    sw = np.sqrt(np.asarray(w, dtype=float))
    x, y = p[:, 0], p[:, 1]
    A = np.column_stack([x, y, np.ones(len(x))]) * sw[:, None]
    b = (x ** 2 + y ** 2) * sw
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    return cx, cy, float(np.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 1e-12)))
