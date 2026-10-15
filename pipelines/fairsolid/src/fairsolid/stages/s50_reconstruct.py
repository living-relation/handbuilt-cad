"""Stage 50 - rebuild the scan as a parametric prismatic solid.

The deterministic answer to "make it parametric", with no ML involved.

Most mechanical parts are layered prisms: a stack of constant cross-sections
along one axis, with holes running through them. That structure is directly
recoverable from a scan, and recovering it turns a 20 MB triangle-soup STEP
into a ~50 KB solid built from real extrusions, arcs and circles - the thing
Fusion and SOLIDWORKS can actually edit.

Method:

  1. Slice the aligned mesh at closely spaced Z heights.
  2. Watch the cross-sectional area. A prismatic part holds it roughly
     constant, then steps. Those steps are the layer boundaries.
  3. Take one representative slice from the middle of each layer, where the
     section is furthest from the noise at a transition.
  4. Simplify each ring, and replace rings that are round with exact circles
     measured by stage 30 - a hole becomes cq.circle(r), not a 200-gon.
  5. Extrude each layer between its boundaries and union the stack.

Interior rings become holes for free: a slice polygon already carries them.

Run standalone:
    python -m fairsolid.stages.s50_reconstruct MESH FRAME OUT.step
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import Polygon

from ..geom import Frame
from ..primitives import (
    extract_planes, extract_cylinders, noise_floor, dedupe_cylinders, _fit_circle,
)
from ..subproc import emit

# Slices per millimetre when profiling cross-sectional area. Dense enough to
# localise a step to well under a millimetre, cheap enough to run in seconds.
SLICES_PER_MM = 2.0

# A layer boundary is declared where area changes by more than this fraction
# of the largest section. Below ~8% the Poisson bulge and occlusion noise
# start inventing spurious layers.
AREA_STEP_FRAC = 0.08

# Minimum layer thickness, mm. Thinner "layers" are transition artefacts.
MIN_LAYER_MM = 0.8

# Cross-section islands smaller than this (mm^2) are scan speckle, not features.
MIN_ISLAND_AREA = 4.0


def _section_polygons(mesh: trimesh.Trimesh, z: float) -> list[Polygon]:
    """Cross-section at height z as shapely polygons in WORLD XY.

    The explicit `to_2D` matters. Left to itself, Path3D.to_planar() picks its
    own arbitrary in-plane basis and returns the mapping as a second value; if
    that is discarded, the polygons come back in a local frame offset from
    world coordinates. On this part that put every ring a constant 1.3 mm from
    the cylinder axes stage 30 had measured - invisible to any size check,
    because a uniform translation preserves every dimension, but it left the
    bore off-centre from the origin the frame stage chose.

    Since the cut is always the Z=z plane, the correct mapping is simply a
    translation of -z along Z, which leaves X and Y untouched.
    """
    try:
        sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    except Exception:
        return []
    if sec is None:
        return []
    to_2D = np.eye(4)
    to_2D[2, 3] = -z
    try:
        planar, _ = sec.to_2D(to_2D=to_2D)
    except Exception:
        return []
    return [p for p in planar.polygons_full if p.area > 0]


def horizontal_plane_heights(planes, nf: float, tol_deg: float = 8.0,
                             max_rms_factor: float = 3.0,
                             min_area_frac: float = 0.01) -> list[float]:
    """Z heights of genuine planes facing along Z, in canonical space.

    The filter is load-bearing, not tidiness. RANSAC also fits planes to
    occlusion craters and Poisson artefacts; unfiltered, this returned heights
    like [0, 0.88, 1.24, 3.21, 6.93, 9.14, 11.98, 21.96] where only 0, 11.98
    and 21.96 are real. A layer boundary could then snap onto a crater and lift
    the whole part off the XY plane - intermittently, since which junk planes
    appear depends on RANSAC's sampling.

    Residual is the discriminator, not size. On this part the real boss top is
    3.38% of plane area and the worst artefact is 3.14%, so an area threshold
    cannot separate them. Normalised against the scan's own noise floor the two
    groups do not overlap at all: real faces land at 1.5-2.0x, artefacts at
    4.6-5.0x. A machined face fits to roughly sensor noise because that is what
    survives averaging; a plane pushed through a crater rim is fitting
    curvature, so its residual scales with the crater instead.

    This is the same self-calibrating test that removes phantom cylinders in
    `extract_cylinders` - one criterion, derived from the scan, no constants.
    """
    cos_tol = np.cos(np.deg2rad(tol_deg))
    total = sum(pl.area for pl in planes) or 1.0
    limit = max_rms_factor * nf
    heights = []
    for pl in planes:
        n = np.asarray(pl.normal, dtype=float)
        if (abs(float(n[2])) >= cos_tol and pl.rms <= limit
                and pl.area / total >= min_area_frac):
            # offset is along the plane normal; project onto +Z.
            heights.append(float(pl.offset / n[2]))
    return sorted(set(round(h, 4) for h in heights))


def snap_to_planes(z: float, heights: list[float], tol: float) -> tuple[float, bool]:
    """Move a layer boundary onto a measured plane when one is close."""
    if not heights:
        return z, False
    nearest = min(heights, key=lambda h: abs(h - z))
    if abs(nearest - z) <= tol:
        return nearest, True
    return z, False


def profile_layers(mesh: trimesh.Trimesh) -> list[dict]:
    """Find prismatic layers by watching cross-sectional area along Z."""
    zmin, zmax = float(mesh.bounds[0][2]), float(mesh.bounds[1][2])
    height = zmax - zmin
    n = max(12, int(height * SLICES_PER_MM))
    # Inset from the faces: a slice exactly on a face is numerically nasty.
    zs = np.linspace(zmin + height * 0.01, zmax - height * 0.01, n)

    areas = []
    for z in zs:
        polys = _section_polygons(mesh, float(z))
        areas.append(sum(p.area for p in polys))
    areas = np.asarray(areas, dtype=float)
    if areas.max() <= 0:
        raise ValueError("no valid cross-sections; is the mesh watertight?")

    # Split where area moves by more than the threshold between samples.
    rel = np.abs(np.diff(areas)) / areas.max()
    breaks = [0] + [i + 1 for i, r in enumerate(rel) if r > AREA_STEP_FRAC] + [len(zs)]

    layers: list[dict] = []
    for a, b in zip(breaks[:-1], breaks[1:]):
        if b - a < 2:
            continue
        z0, z1 = float(zs[a]), float(zs[b - 1])
        if z1 - z0 < MIN_LAYER_MM:
            continue
        layers.append({
            "z0": z0, "z1": z1,
            "z_mid": float((z0 + z1) / 2.0),
            "area": float(np.median(areas[a:b])),
        })

    if not layers:
        raise ValueError("no prismatic layers found - part may not be prismatic")

    # Snap the outer boundaries back to the true extents; the 1% inset above
    # would otherwise shrink the part by a fraction of a millimetre.
    layers[0]["z0"] = zmin
    layers[-1]["z1"] = zmax
    for lo, hi in zip(layers[:-1], layers[1:]):
        mid = (lo["z1"] + hi["z0"]) / 2.0
        lo["z1"] = hi["z0"] = mid
    return layers


def snap_layers(layers: list[dict], heights: list[float], tol: float) -> list[dict]:
    """Replace inferred layer boundaries with measured plane heights.

    The area profile is good at answering HOW MANY layers there are and
    roughly where; it is poor at answering exactly where, because near a step
    the section area changes gradually over the Poisson-rounded edge. On the
    test part this pulled the plate/boss boundary to 13.11 mm when the plane
    fit put it at 11.96 mm. Snapping fixes a ~1.2 mm error.
    """
    # The outermost faces are snapped too. They came from the bounding box,
    # which on this data sat 1.115 mm below the real base - the extrema are
    # exactly the values least worth trusting.
    for i, layer in enumerate(layers):
        for key in ("z0", "z1"):
            snapped, hit = snap_to_planes(layer[key], heights, tol)
            if hit:
                layer[key] = snapped
                if key == "z1" and i + 1 < len(layers):
                    layers[i + 1]["z0"] = snapped
                layer.setdefault("snapped", []).append(key)
        layer["z_mid"] = (layer["z0"] + layer["z1"]) / 2.0

    # The base is pinned, not snapped - but only when the part actually
    # starts at z=0. Stage 20 measured the base plane and DEFINED z=0 there,
    # so a bottom within `tol` of zero is zero by construction, and letting it
    # drift onto some other candidate height contradicts the frame. When the
    # measured material reaches further down than that, z=0 is not the bottom
    # of this part, and pinning would throw away everything below it.
    if layers and abs(layers[0]["z0"]) <= tol:
        layers[0]["z0"] = 0.0
        layers[0]["z_mid"] = (layers[0]["z0"] + layers[0]["z1"]) / 2.0
    return merge_thin_layers(layers)


def merge_thin_layers(layers: list[dict],
                      min_thickness: float = MIN_LAYER_MM) -> list[dict]:
    """Fold layers that snapping made thinner than `min_thickness`.

    Snapping moves boundaries independently, so two boundaries can land on
    the same plane (zero thickness) or cross (negative thickness). Such a
    layer is not geometry; handed to OCCT it is an extrusion by a zero or
    reversed vector, which raises BRepSweep_Translation or corrupts the heap
    outright. The layer's height range goes to its neighbour, so the stack
    stays contiguous and no material is dropped.
    """
    kept: list[dict] = []
    pending_z0: float | None = None
    for layer in layers:
        layer = dict(layer)
        if pending_z0 is not None:
            layer["z0"] = min(pending_z0, layer["z0"])
            pending_z0 = None
        if layer["z1"] - layer["z0"] >= min_thickness:
            kept.append(layer)
        elif kept:
            kept[-1]["z1"] = max(kept[-1]["z1"], layer["z1"])
        else:
            pending_z0 = min(layer["z0"], layer["z1"])
    for layer in kept:
        layer["z_mid"] = (layer["z0"] + layer["z1"]) / 2.0
    return kept


def _ring_is_circle(coords: np.ndarray, tol: float) -> tuple[float, float, float] | None:
    """Return (cx, cy, r) if a ring is round to within tol, else None."""
    c = coords.mean(axis=0)
    d = np.linalg.norm(coords - c, axis=1)
    r = float(d.mean())
    if r <= 0:
        return None
    if float(np.sqrt(np.mean((d - r) ** 2))) > tol:
        return None
    return float(c[0]), float(c[1]), r


def _match_cylinder(coords: np.ndarray, cyls: list, tol: float):
    """Identify a slice ring as a measured cylinder. Returns (cx, cy, r) or None.

    This replaces "does this ring look round?" with "is this ring one of the
    cylinders stage 30 already measured?", and the difference matters. A ring
    is a few hundred points from a single Z height, and on an occlusion-damaged
    hole it fails a roundness test even though the hole is perfectly round;
    judging it in isolation made circle-vs-polyline flip between runs. The
    stage-30 fit used thousands of points spanning the full bore depth, so the
    ring only has to say WHERE the feature is - the cylinder supplies WHAT it is.
    """
    if not cyls or len(coords) < 3:
        return None
    # Least-squares circle, NOT the mean of the vertices. Polygon.simplify()
    # drops points unevenly around a smooth arc, so the vertex centroid drifts
    # off the true centre - measured at up to 1.8 mm on this part, which is
    # far enough to miss every candidate cylinder.
    try:
        cx0, cy0, r_mean = _fit_circle(np.asarray(coords, dtype=float))
    except Exception:
        return None
    centre = np.array([cx0, cy0])
    if not np.isfinite(r_mean) or r_mean <= 0:
        return None

    best, best_err = None, np.inf
    for c in cyls:
        # Cylinder axis position in the slice plane (canonical Z-aligned).
        cx, cy = float(c.point[0]), float(c.point[1])
        offset = float(np.hypot(centre[0] - cx, centre[1] - cy))
        radius_err = abs(c.radius - r_mean)
        if offset > tol * 4 or radius_err > tol * 4:
            continue
        score = offset + radius_err
        if score < best_err:
            best, best_err = (cx, cy, float(c.radius)), score
    return best


def vertical_plane_lines(planes, tol_deg: float = 8.0) -> list[tuple]:
    """Measured planes parallel to Z, as 2D lines (nx, ny, d) with nx*x+ny*y=d.

    These are the counterpart of the cylinder list: for straight edges they
    are the authority on WHERE the boundary is, exactly as cylinders are for
    round ones.
    """
    sin_tol = np.sin(np.deg2rad(tol_deg))
    lines = []
    for pl in planes:
        n = np.asarray(pl.normal, dtype=float)
        if abs(float(n[2])) > sin_tol:
            continue
        h = float(np.hypot(n[0], n[1]))
        if h < 1e-9:
            continue
        lines.append((float(n[0] / h), float(n[1] / h), float(pl.offset / h),
                      float(pl.area)))
    return lines


def bridge_occlusions(coords: np.ndarray, lines: list[tuple], tol: float,
                      max_width: float) -> np.ndarray:
    """Cut across inward excursions that interrupt one measured plane.

    An occlusion crater in a silhouette looks like this: a run of vertices on
    measured plane A, then a detour inward where the scanner saw nothing, then
    more vertices back on plane A. Because the detour is genuinely absent from
    the scan, the default is to keep it - Fairsolid does not invent material.

    Enabling this replaces such a detour with the straight edge, on the
    argument that a boundary which measurably resumes on the same plane was
    never interrupted in the real part.

    The risk is real and is why this is off by default: a legitimate slot or
    notch cut into a straight edge has exactly the same signature. `max_width`
    is the guard - excursions wider than it are left alone.
    """
    if not lines or len(coords) < 5:
        return coords

    def label_of(pt):
        best, best_d = None, tol
        for i, (nx, ny, d, _a) in enumerate(lines):
            dist = abs(nx * pt[0] + ny * pt[1] - d)
            if dist < best_d:
                best, best_d = i, dist
        return best

    labels = [label_of(p) for p in coords]
    n = len(coords)
    keep = np.ones(n, dtype=bool)

    i = 0
    while i < n:
        if labels[i] is None:
            i += 1
            continue
        # Look ahead for the same plane resuming after a gap of unlabelled pts.
        j = i + 1
        while j < n and labels[j] is None:
            j += 1
        if j < n and labels[j] == labels[i] and j > i + 1:
            if float(np.linalg.norm(coords[j] - coords[i])) <= max_width:
                keep[i + 1:j] = False
        i = j if j > i else i + 1

    out = coords[keep]
    return out if len(out) >= 3 else coords


def snap_outline_to_planes(coords: np.ndarray, lines: list[tuple],
                           tol: float) -> np.ndarray:
    """Straighten an outline onto measured planes, bridging occlusion bites.

    Holes already snap to measured cylinders; without this, straight edges get
    no equivalent treatment and the outline keeps every scalloped crater the
    scanner left in the silhouette. Runs of consecutive vertices that belong to
    one measured plane are replaced by that plane's straight segment, so a bite
    within a run is bridged rather than reproduced.

    A vertex that matches no plane is left alone - genuinely curved or
    unmeasured boundary must survive untouched.
    """
    if not lines or len(coords) < 4:
        return coords

    labels = []
    for x, y in coords:
        best, best_d = None, tol
        for i, (nx, ny, d, _area) in enumerate(lines):
            dist = abs(nx * x + ny * y - d)
            if dist < best_d:
                best, best_d = i, dist
        labels.append(best)

    out: list[tuple[float, float]] = []
    n = len(coords)
    i = 0
    while i < n:
        lab = labels[i]
        j = i
        while j + 1 < n and labels[j + 1] == lab:
            j += 1
        if lab is None:
            out.extend(tuple(p) for p in coords[i:j + 1])
        else:
            nx, ny, d, _ = lines[lab]
            # Project the run's endpoints onto the measured line; the
            # in-between vertices carry only noise and occlusion damage.
            for pt in (coords[i], coords[j]):
                t = nx * pt[0] + ny * pt[1] - d
                out.append((float(pt[0] - t * nx), float(pt[1] - t * ny)))
        i = j + 1

    # Drop points that coincide after projection.
    cleaned = [out[0]]
    for p in out[1:]:
        if np.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > tol * 0.5:
            cleaned.append(p)
    return np.asarray(cleaned) if len(cleaned) >= 3 else coords


def reconstruct(
    mesh_path: Path,
    frame_path: Path,
    out_step: Path,
    *,
    simplify_tol: float | None = None,
    snap_outline: bool = True,
    bridge_occlusion_mm: float = 0.0,
) -> dict:
    import cadquery as cq

    frame = Frame.load(frame_path)
    raw = trimesh.load(mesh_path, force="mesh", process=False)

    mesh = raw.copy()
    mesh.vertices = frame.to_canonical(np.asarray(mesh.vertices, dtype=float))

    planes = extract_planes(mesh)
    nf = noise_floor(planes)
    cyls = dedupe_cylinders(extract_cylinders(
        mesh, [np.array([0.0, 0.0, 1.0])], max_rms=3 * nf))
    # Radii are what the reconstruction quotes, so record them for the report.
    measured_radii = sorted(round(c.radius, 4) for c in cyls)
    tol = simplify_tol if simplify_tol is not None else max(3.0 * nf, 0.08)

    vlines = vertical_plane_lines(planes) if snap_outline else []
    layers = profile_layers(mesh)
    heights = horizontal_plane_heights(planes, nf)
    # z=0 is authoritative: stage 20 measured the base plane and DEFINED the
    # origin there. Re-running RANSAC here on canonical coordinates finds a
    # slightly different base each time (it samples different points), and
    # letting that compete with the frame pulled the part up to 0.2 mm off the
    # XY plane at random. A committed decision from an earlier stage is not
    # something a later stage re-derives.
    if 0.0 not in heights:
        heights.append(0.0)
        heights.sort()
    # Tolerance generous enough to catch a boundary the area profile placed
    # a millimetre off, tight enough not to snap onto an unrelated face.
    layers = snap_layers(layers, heights, tol=2.0)
    result = None
    report: list[dict] = []

    for layer in layers:
        polys = _section_polygons(mesh, layer["z_mid"])
        if not polys:
            continue
        thickness = layer["z1"] - layer["z0"]
        if thickness <= 0:
            # merge_thin_layers guarantees this never happens. Checked anyway
            # because OCCT does not reliably raise on a degenerate extrusion -
            # it can corrupt the heap and kill the process with no traceback.
            raise ValueError(f"layer {layer} has non-positive thickness")
        layer_body = None
        outers: list[str] = []
        holes: list[str] = []

        # Every island, not just the biggest. A cross-section through a part
        # with separate arms or bosses is several disjoint polygons, and
        # keeping only the largest collapsed a 197 x 325 mm casting to
        # 27 x 37 mm - a structurally valid solid of the wrong object.
        for poly in sorted(polys, key=lambda p: -p.area):
            if poly.area < MIN_ISLAND_AREA:
                continue

            wp = cq.Workplane("XY", origin=(0, 0, layer["z0"]))
            outer = np.asarray(poly.exterior.simplify(tol).coords)[:-1]
            circ = _match_cylinder(outer, cyls, tol) or _ring_is_circle(outer, tol)
            if circ is None and vlines:
                # Straight edges get the same treatment the holes already get.
                if bridge_occlusion_mm > 0:
                    outer = bridge_occlusions(outer, vlines, tol * 12,
                                              bridge_occlusion_mm)
                outer = snap_outline_to_planes(outer, vlines, tol * 12)

            if circ is not None:
                cx, cy, r = circ
                body = wp.center(cx, cy).circle(r).extrude(thickness)
                outers.append(f"circle r={r:.4f}")
            elif len(outer) >= 3:
                body = wp.polyline([tuple(p) for p in outer]).close().extrude(thickness)
                outers.append(f"polyline {len(outer)} pts")
            else:
                continue

            for ring in poly.interiors:
                ring_pts = np.asarray(
                    Polygon(ring).exterior.simplify(tol).coords)[:-1]
                if len(ring_pts) < 3:
                    continue
                hc = (_match_cylinder(ring_pts, cyls, tol)
                      or _ring_is_circle(ring_pts, tol))
                hwp = cq.Workplane("XY", origin=(0, 0, layer["z0"] - 0.5))
                if hc is not None:
                    cx, cy, r = hc
                    cutter = hwp.center(cx, cy).circle(r).extrude(thickness + 1.0)
                    holes.append(f"circle r={r:.4f}")
                else:
                    cutter = (hwp.polyline([tuple(p) for p in ring_pts]).close()
                              .extrude(thickness + 1.0))
                    holes.append(f"polyline {len(ring_pts)} pts")
                body = body.cut(cutter)

            layer_body = body if layer_body is None else layer_body.union(body)

        if layer_body is None:
            continue

        report.append({
            "z0": round(layer["z0"], 4), "z1": round(layer["z1"], 4),
            "thickness": round(thickness, 4),
            "outer": outers[0] if len(outers) == 1 else f"{len(outers)} islands",
            "islands": outers,
            "holes": holes,
        })
        result = layer_body if result is None else result.union(layer_body)

    if result is None:
        raise ValueError("reconstruction produced no geometry")

    out_step.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(result, str(out_step))

    solid = result.val()
    bb = solid.BoundingBox()
    return {
        "step": str(out_step),
        "n_layers": len(report),
        "layers": report,
        "volume_mm3": float(solid.Volume()),
        "bbox_mm": [bb.xlen, bb.ylen, bb.zlen],
        "zmin": bb.zmin,
        "simplify_tol": tol,
        "plane_heights": heights,
        "measured_radii": measured_radii,
        "n_vertical_planes": len(vlines),
        "bridge_occlusion_mm": bridge_occlusion_mm,
        "noise_floor": nf,
        "bytes": out_step.stat().st_size if out_step.exists() else 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mesh", type=Path)
    ap.add_argument("frame", type=Path)
    ap.add_argument("out_step", type=Path)
    ap.add_argument("--simplify-tol", type=float, default=None)
    ap.add_argument("--no-snap-outline", action="store_true")
    ap.add_argument("--bridge-occlusion-mm", type=float, default=0.0,
                    help="cut across inward excursions up to this wide; 0 = off")
    a = ap.parse_args()
    emit(reconstruct(a.mesh, a.frame, a.out_step, simplify_tol=a.simplify_tol,
                     snap_outline=not a.no_snap_outline,
                     bridge_occlusion_mm=a.bridge_occlusion_mm))


if __name__ == "__main__":
    main()
