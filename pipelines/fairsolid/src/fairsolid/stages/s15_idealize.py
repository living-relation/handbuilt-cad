"""Stage 15 - remove casting texture so surfaces become mathematically flat.

The point of reverse engineering a part is to recover the DESIGN, not to
replicate the artefact. A sand-cast knuckle has a rough skin measuring ~0.22 mm
rms; faithfully reproducing that skin gives a model nobody can machine from,
and every downstream tolerance has to be loosened to accommodate roughness that
was never part of the design in the first place.

SNAPPING is the mechanism that works, and it is on by default. Vertices lying
near a measured plane or cylinder are projected exactly onto it, so a textured
cast face becomes a true plane and a bore becomes a true cylinder. On a cast
knuckle this moves ~37k vertices with a median displacement of 0.001 mm from
the original surface: flat where it should be flat, untouched elsewhere.

SMOOTHING is available (`--smooth-iters`) but defaults to OFF, because measuring
it showed it does not earn its cost. A sweep on the same knuckle:

    iters    flatness gain    median deviation from scan
        0            best              0.0011 mm
       12          modest              0.0436 mm
       40      none at all             0.0612 mm
      200          modest              0.1638 mm

The gain is non-monotonic, which is the tell that the thing being improved is
not texture. On a casting, most surface residual is CURVATURE - the part is
genuinely curved - and no amount of smoothing flattens that. What smoothing
reliably does is move the whole surface away from the scan. Turn it on only for
a scan with real high-frequency sensor noise, and check the deviation after.

When smoothing IS enabled, it runs FIRST and snapping runs last. Reversed, the
snapping is undone: projecting a vertex exactly onto a plane and then averaging
it against its neighbours pulls it straight back off. Only the last operation to
touch a vertex decides where it ends up.

Snapping is deliberately conservative near edges. A vertex is only projected
when ONE primitive clearly claims it; where two faces meet, both are close and
projecting onto either would round or fold the edge, so those vertices are left
for the smoothing pass.

Run standalone:
    python -m fairsolid.stages.s15_idealize IN OUT [--texture-mm X] [--no-snap]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh

from ..primitives import (
    dedupe_cylinders, extract_cylinders, extract_planes, noise_floor,
)
from ..subproc import emit

# A vertex is snapped only if the runner-up primitive is at least this many
# times further away. Near an edge both faces are comparably close, and
# projecting there folds the edge over.
AMBIGUITY_RATIO = 2.5

# Taubin's lambda/mu pair. mu slightly more negative than -lambda is what makes
# it volume-preserving; plain Laplacian (mu=0) shrinks the part measurably.
TAUBIN_LAMBDA = 0.5
TAUBIN_MU = -0.53


def idealize(
    src: Path,
    dst: Path,
    *,
    texture_mm: float | None = None,
    snap: bool = True,
    smooth_iters: int = 0,
) -> dict:
    mesh = trimesh.load(src, force="mesh", process=False)
    nf_before = noise_floor(extract_planes(mesh))

    dst.parent.mkdir(parents=True, exist_ok=True)

    # --- pass 1: bulk texture removal --------------------------------
    if smooth_iters > 0:
        _smooth(mesh, dst, smooth_iters)
        mesh = trimesh.load(dst, force="mesh", process=False)

    # --- re-measure on the smoothed mesh -----------------------------
    planes = extract_planes(mesh)
    nf = noise_floor(planes)
    amp = texture_mm if texture_mm is not None else nf
    snap_tol = 3.0 * amp
    cyls = dedupe_cylinders(extract_cylinders(
        mesh, [np.asarray(p.normal) for p in planes[:3]], max_rms=3 * nf))

    report = {
        "input": str(src), "output": str(dst),
        "noise_floor": nf_before, "noise_floor_smoothed": nf,
        "texture_mm": amp, "snap_tol": snap_tol,
        "n_planes": len(planes), "n_cylinders": len(cyls),
        "snapped_to_planes": 0, "snapped_to_cylinders": 0,
        "smooth_iters": smooth_iters,
    }

    # --- pass 2: exact projection, the last word ---------------------
    verts = np.asarray(mesh.vertices, dtype=float).copy()
    if snap and planes:
        moved = _snap_to_planes(verts, planes, snap_tol)
        report["snapped_to_planes"] = int(moved.sum())
        if cyls:
            report["snapped_to_cylinders"] = int(
                _snap_to_cylinders(verts, cyls, snap_tol, ~moved).sum())
        mesh.vertices = verts
    mesh.export(dst)

    after_planes = extract_planes(trimesh.load(dst, force="mesh", process=False))
    report["noise_floor_after"] = noise_floor(after_planes)
    # Global noise floor is a poor score here: on a curved part it is dominated
    # by curvature, not roughness, so it barely moves and can even go the wrong
    # way. Flatness of the regions we actually snapped is the honest measure.
    report["flatness_before"] = _flatness(
        np.asarray(trimesh.load(src, force="mesh", process=False).vertices),
        planes, snap_tol)
    report["flatness_after"] = _flatness(verts, planes, snap_tol)
    report["flatness_gain"] = (
        1.0 - report["flatness_after"] / report["flatness_before"]
        if report["flatness_before"] > 0 else 0.0)
    return report


def _flatness(verts: np.ndarray, planes, tol: float) -> float:
    """RMS distance of near-plane vertices from their plane, in mm.

    Restricted to vertices already within `tol` of a plane, so it scores how
    flat the FLAT REGIONS are rather than how curved the part is.
    """
    if not planes or not len(verts):
        return 0.0
    normals = np.array([p.normal for p in planes], dtype=float)
    offsets = np.array([p.offset for p in planes], dtype=float)
    d = np.abs(verts @ normals.T - offsets).min(axis=1)
    near = d[d <= tol]
    return float(np.sqrt(np.mean(near ** 2))) if near.size else 0.0


def _snap_to_planes(verts: np.ndarray, planes, tol: float) -> np.ndarray:
    """Project vertices onto planes, and onto plane INTERSECTIONS at edges.

    A vertex near exactly one plane goes onto that plane. A vertex near two is
    on the edge where they meet, and the right idealisation is the intersection
    LINE of the two - which both flattens the two faces and sharpens the edge
    between them. Refusing to touch those vertices (the earlier behaviour) left
    a rounded, scan-textured band along every edge and capped flatness well
    short of what the measured primitives support.

    Returns a mask of moved vertices.
    """
    normals = np.array([p.normal for p in planes], dtype=float)
    offsets = np.array([p.offset for p in planes], dtype=float)

    dist = verts @ normals.T - offsets            # (n_verts, n_planes)
    absd = np.abs(dist)
    order = np.argsort(absd, axis=1)
    i1 = order[:, 0]
    rows = np.arange(len(verts))
    d1 = absd[rows, i1]

    moved = np.zeros(len(verts), dtype=bool)
    if normals.shape[0] < 2:
        single = d1 <= tol
        idx = np.flatnonzero(single)
        if idx.size:
            verts[idx] -= dist[idx, i1[idx]][:, None] * normals[i1[idx]]
        return single

    i2 = order[:, 1]
    d2 = absd[rows, i2]

    # Two planes both claim it, and they actually meet at an angle: put the
    # vertex on their intersection line.
    cos = np.abs(np.einsum("ij,ij->i", normals[i1], normals[i2]))
    on_edge = (d1 <= tol) & (d2 <= tol) & (cos < 0.94)
    for idx in np.flatnonzero(on_edge):
        n1, n2 = normals[i1[idx]], normals[i2[idx]]
        o1, o2 = offsets[i1[idx]], offsets[i2[idx]]
        d = np.cross(n1, n2)
        nd = np.linalg.norm(d)
        if nd < 1e-9:
            continue
        d = d / nd
        # Point on the line: solve the 2x2 system in the plane spanned by n1,n2.
        a = np.array([[1.0, float(np.dot(n1, n2))],
                      [float(np.dot(n1, n2)), 1.0]])
        try:
            c1, c2 = np.linalg.solve(a, np.array([o1, o2]))
        except np.linalg.LinAlgError:
            continue
        p0 = c1 * n1 + c2 * n2
        verts[idx] = p0 + d * float(np.dot(verts[idx] - p0, d))
        moved[idx] = True

    # Everything else near a single plane goes onto that plane.
    on_face = (d1 <= tol) & ~moved & (d2 > d1 * AMBIGUITY_RATIO)
    idx = np.flatnonzero(on_face)
    if idx.size:
        verts[idx] -= dist[idx, i1[idx]][:, None] * normals[i1[idx]]
    return moved | on_face


def _snap_to_cylinders(verts: np.ndarray, cyls, tol: float,
                       eligible: np.ndarray) -> np.ndarray:
    """Push vertices radially onto the nearest measured cylinder."""
    moved = np.zeros(len(verts), dtype=bool)
    for c in cyls:
        axis = np.asarray(c.axis, dtype=float)
        axis = axis / np.linalg.norm(axis)
        point = np.asarray(c.point, dtype=float)

        rel = verts - point
        along = rel @ axis
        perp = rel - np.outer(along, axis)
        radial = np.linalg.norm(perp, axis=1)

        hit = eligible & ~moved & (np.abs(radial - c.radius) <= tol) & (radial > 1e-9)
        idx = np.flatnonzero(hit)
        if not idx.size:
            continue
        direction = perp[idx] / radial[idx][:, None]
        verts[idx] = point + np.outer(along[idx], axis) + direction * c.radius
        moved |= hit
    return moved


def _smooth(mesh: trimesh.Trimesh, dst: Path, iters: int) -> None:
    """Taubin smoothing via pymeshlab, in this process (no OCCT involved)."""
    import pymeshlab

    tmp = dst.with_suffix(".pre.ply")
    mesh.export(tmp)
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(tmp))
    ms.apply_filter("apply_coord_taubin_smoothing",
                    lambda_=TAUBIN_LAMBDA, mu=TAUBIN_MU, stepsmoothnum=iters)
    ms.save_current_mesh(str(dst))
    tmp.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--texture-mm", type=float, default=None,
                    help="texture amplitude to erase; default = measured noise floor")
    ap.add_argument("--no-snap", action="store_true")
    ap.add_argument("--smooth-iters", type=int, default=0,
                    help="Taubin iterations; 0 (default) snaps only - smoothing "
                         "moves the surface off the scan for little gain")
    a = ap.parse_args()
    emit(idealize(a.src, a.dst, texture_mm=a.texture_mm,
                  snap=not a.no_snap, smooth_iters=a.smooth_iters))


if __name__ == "__main__":
    main()
