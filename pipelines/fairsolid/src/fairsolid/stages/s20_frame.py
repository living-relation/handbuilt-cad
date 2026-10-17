"""Stage 20 - decide where the part sits in space, and how big it is.

This is the stage that satisfies "properly oriented and scaled". A scan
arrives at an arbitrary pose, hundreds of millimetres from the origin, and
every AI reconstruction stage downstream will normalise it into a unit cube
and hand back dimensionless code. Stage 20 records the transform that makes
that reversible, and stage 80 applies the inverse.

Two separate jobs, deliberately kept apart:

  1. ALIGNMENT - rotate/translate the scan so its principal faces lie on the
     global planes and a meaningful feature sits at the origin. Chosen from
     measured planes, so it is repeatable across rescans of the same part.
  2. NORMALISATION - the centre/scale pair reproducing what CAD-Recode,
     cadrille and CADReasoner do internally, kept as data so it can be undone.

Which face is "the bottom" is a convention rather than a fact, so this stage
does not silently commit to one. It ranks several defensible frames, renders
each, and lets the caller choose - see `enumerate_frames`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh

from ..geom import Frame, normalisation_for, orthonormalise
from ..primitives import (
    Plane, extract_planes, extract_cylinders, noise_floor, dedupe_cylinders,
)
from ..subproc import emit


# Two axes closer than this are treated as the same direction: X is
# Gram-Schmidt'd against Z, so anything short of parallel is usable.
NEAR_PARALLEL = 0.97


def candidate_axes(planes: list[Plane], *, top_n: int = 8) -> list[dict]:
    """Rank plane normals as candidate CAD axes.

    A plane is a good axis candidate when it is large (well supported) and
    flat (low residual). Antiparallel pairs are merged, since the top and
    bottom of a plate define the same axis.
    """
    cands: list[dict] = []
    for p in planes[:top_n]:
        n = np.asarray(p.normal, dtype=float)
        for c in cands:
            if abs(float(np.dot(n, c["axis"]))) > 0.995:
                c["area"] += p.area
                c["members"].append(p)
                break
        else:
            cands.append({"axis": n, "area": p.area, "rms": p.rms, "members": [p]})
    cands.sort(key=lambda c: -c["area"])
    return cands


def cylinder_axes(cyls: list, *, top_n: int = 12) -> list[dict]:
    """Group cylinder axes into candidate CAD axes, best supported first.

    Plane normals are not the only datums that matter. A knuckle, hub, flange
    or pulley is dimensioned from a BORE axis, and on such parts no face is
    the natural +Z - the real scan that motivated this had four plane-derived
    orientations and not one of them put the hub bore on the Z axis.

    Support is summed over collinear cylinders, so a counterbored hole and its
    through-bore reinforce one axis instead of competing.
    """
    cands: list[dict] = []
    for c in sorted(cyls, key=lambda c: -c.n_points)[:top_n]:
        a = np.asarray(c.axis, dtype=float)
        for k in cands:
            if abs(float(np.dot(a, k["axis"]))) > 0.99:
                k["support"] += c.n_points
                k["members"].append(c)
                k["max_radius"] = max(k["max_radius"], c.radius)
                break
        else:
            cands.append({"axis": a, "support": c.n_points, "rms": c.rms,
                          "max_radius": c.radius, "members": [c]})
    cands.sort(key=lambda k: -k["support"])
    return cands


def enumerate_frames(
    planes: list[Plane],
    cands: list[dict],
    cyls: list,
    mesh: trimesh.Trimesh,
    *,
    limit: int = 6,
) -> list[dict]:
    """Build ranked, human-choosable frame options.

    Scoring favours a large, flat primary face: large means well supported by
    the scan, flat means low fit residual, and those are the two properties
    that make a datum trustworthy. The caller either takes option 0 or shows
    the rendered previews and asks a human.
    """
    if len(cands) < 2:
        raise ValueError(
            "need at least two independent plane directions to build a frame; "
            "the scan may be too incomplete or too organic"
        )

    centroid = np.asarray(mesh.centroid, dtype=float)
    best_area = max(c["area"] for c in cands)

    # Bore axes compete with face normals for +Z. Scored on supporting points
    # rather than area, normalised so the two kinds are comparable; the 0.9
    # factor is a mild tie-break toward a face when support is otherwise equal,
    # since a face also fixes the origin height.
    axis_cands = cylinder_axes(cyls)
    best_support = max((k["support"] for k in axis_cands), default=1)

    z_choices: list[dict] = []
    for i, c in enumerate(cands[:3]):
        z_choices.append({
            "axis": c["axis"], "kind": "plane", "idx": i,
            "score": (c["area"] / best_area) * (1.0 / (1.0 + 40.0 * c["rms"])),
            "area": c["area"], "rms": c["rms"],
            "why": f"face, area {c['area']:.0f}mm2",
            "members": c["members"],
        })
    for i, k in enumerate(axis_cands[:2]):
        z_choices.append({
            "axis": k["axis"], "kind": "cylinder", "idx": i,
            "score": 0.9 * (k["support"] / best_support)
                     * (1.0 / (1.0 + 40.0 * k["rms"])),
            "area": 0.0, "rms": k["rms"],
            "why": f"bore axis, d={2 * k['max_radius']:.1f}mm, "
                   f"{k['support']} pts over {len(k['members'])} cylinders",
            "members": [],
        })
    z_choices.sort(key=lambda z: -z["score"])

    options: list[dict] = []

    for zi, zc in enumerate(z_choices[:4]):
        for xi, xc in enumerate(cands[:3]):
            # X only has to be NOT PARALLEL to Z, not perpendicular to it -
            # orthonormalise() Gram-Schmidts X against Z on the very next line.
            # The old 0.2 threshold enforced a constraint the following code
            # already imposes, and on a curved housing whose detected faces are
            # all draft-angled within ~40 degrees of one another it rejected
            # every pair and returned an empty option list, which build() then
            # indexed into.
            if abs(float(np.dot(zc["axis"], xc["axis"]))) > NEAR_PARALLEL:
                continue

            z = np.asarray(zc["axis"], dtype=float)
            # Point +Z away from the bulk of the material so the part sits ON
            # the XY plane rather than hanging beneath it. A bore axis has no
            # "outward" side of its own, so orient it off the mesh centroid.
            if zc["members"]:
                base = max(zc["members"], key=lambda p: p.area)
                base_pt = np.asarray(base.normal, dtype=float) * base.offset
                if float(np.dot(centroid - base_pt, z)) < 0:
                    z = -z
            else:
                local = (np.asarray(mesh.vertices) - centroid) @ z
                if float(np.mean(local)) < 0:
                    z = -z

            R = orthonormalise(z, np.asarray(xc["axis"], dtype=float))
            origin, origin_note = _pick_origin(mesh, R, cyls, planes)

            score = zc["score"]
            options.append({
                "z_from": zi,
                "x_from": xi,
                "z_kind": zc["kind"],
                "z_why": zc["why"],
                "rotation": R,
                "origin": origin,
                "score": float(score),
                "z_area": zc["area"],
                "z_rms": zc["rms"],
                "x_area": xc["area"],
                "x_rms": xc["rms"],
                "origin_note": origin_note,
            })

    if not options:
        options.append(_pca_frame(mesh, cyls, planes))

    options.sort(key=lambda o: -o["score"])
    return options[:limit]


def _pca_frame(mesh: trimesh.Trimesh, cyls: list, planes: list) -> dict:
    """Last-resort frame from the mesh's own principal axes.

    Guarantees an answer. When a part has no two usable primitive directions -
    a curved housing, an organic shape, a badly occluded scan - PCA still gives
    an orthonormal basis aligned with the part's dominant extents, which meets
    the actual requirement: a primary plane normal to a major axis.
    """
    verts = np.asarray(mesh.vertices, dtype=float)
    centred = verts - verts.mean(axis=0)
    # Columns of V are the principal directions, largest variance first.
    _, _, vh = np.linalg.svd(centred[:: max(1, len(centred) // 50_000)],
                             full_matrices=False)
    z = vh[2]          # least variance -> the part's "flattest" direction
    x = vh[0]          # most variance
    R = orthonormalise(z, x)
    origin, note = _pick_origin(mesh, R, cyls, planes)
    return {
        "z_from": -1, "x_from": -1, "rotation": R, "origin": origin,
        "score": 0.01, "z_area": 0.0, "z_rms": 0.0,
        "x_area": 0.0, "x_rms": 0.0,
        "z_kind": "pca", "z_why": "PCA of the mesh (no usable primitive pair)",
        "origin_note": note,
    }


# A downward plane counts as a base candidate only if it is a real face:
# fitted to within this many noise floors, and carrying at least this share
# of all plane area. The same self-calibrating test stage 50 uses to tell
# machined faces from crater and Poisson artefacts.
BASE_MAX_RMS_FACTOR = 3.0
BASE_MIN_AREA_FRAC = 0.01


def _base_height(mesh: trimesh.Trimesh, R: np.ndarray,
                 planes: list[Plane]) -> tuple[float, str]:
    """Height of the part's base along R's Z axis, measured not bounded.

    A bounding box is defined by a part's WORST points; a fitted plane is
    defined by its AVERAGE points. Poisson leaves a scatter of bulge and
    occlusion artefacts hanging below the true bottom face - on the test scan
    they put vertices.min() 1.115 mm under the real base, which propagated
    into every height in the model. So the base is taken from a measured
    plane facing -Z, and the bounding box is only the fallback.

    The LOWEST genuine downward plane, not the largest. On a stepped part
    the largest downward face can be a shelf part-way up: on the pedal
    adapter it was a 4333 mm2 step with 21 mm of the part (18% of the
    vertices) hanging below it. Z=0 then sat inside the part, and stage 50,
    which pins the bottom layer to Z=0, built a zero-thickness layer that
    OCCT rejected (BRepSweep_Translation) or crashed on (0xC0000374).
    """
    z_dir = R[2]
    downward = [
        p for p in planes
        if float(np.dot(np.asarray(p.normal), z_dir)) < -0.985
    ]
    if downward:
        nf = noise_floor(planes)
        total = sum(p.area for p in planes) or 1.0
        genuine = [p for p in downward
                   if p.rms <= BASE_MAX_RMS_FACTOR * nf
                   and p.area / total >= BASE_MIN_AREA_FRAC]

        def height_of(p: Plane) -> float:
            n = np.asarray(p.normal, dtype=float)
            return float(p.offset / np.dot(n, z_dir))

        if genuine:
            base = min(genuine, key=height_of)
            note = (f"Z=0 on lowest measured base plane "
                    f"(area {base.area:.0f} mm2)")
        else:
            base = max(downward, key=lambda p: p.area)
            note = f"Z=0 on measured base plane (area {base.area:.0f} mm2)"
        return height_of(base), note

    local = np.asarray(mesh.vertices, dtype=float) @ R.T
    return float(local[:, 2].min()), "Z=0 at bounding-box minimum (no base plane found)"


def _pick_origin(mesh: trimesh.Trimesh, R: np.ndarray, cyls: list,
                 planes: list[Plane]) -> tuple[np.ndarray, str]:
    """Place the origin on measured features rather than on extrema.

    XY comes from the dominant bore axis when one runs along Z - it is
    measured from thousands of points and is the feature a designer would
    have dimensioned from. Z comes from the fitted base plane.
    """
    verts = np.asarray(mesh.vertices, dtype=float)
    z_dir = R[2]
    base_h, base_note = _base_height(mesh, R, planes)

    axial = [c for c in cyls
             if abs(float(np.dot(np.asarray(c.axis), z_dir))) > 0.98]
    if axial:
        best = max(axial, key=lambda c: c.n_points)
        pt = np.asarray(best.point, dtype=float)
        # Keep the bore's XY; set Z from the fitted base.
        local_pt = pt @ R.T
        origin = R.T @ np.array([local_pt[0], local_pt[1], base_h])
        return origin, (f"XY on axis of largest bore (d={2 * best.radius:.3f} mm); "
                        f"{base_note}")

    local = verts @ R.T
    corner = local.min(axis=0)
    return (R.T @ np.array([corner[0], corner[1], base_h]),
            f"XY at bounding-box min corner; {base_note}")


def measure(mesh_path: Path, *, thresh: float = 0.4) -> dict:
    """Everything stage 20 needs to know about the scan, measured once."""
    mesh = trimesh.load(mesh_path, force="mesh", process=False)
    planes = extract_planes(mesh, thresh=thresh)
    cands = candidate_axes(planes)
    nf = noise_floor(planes)
    cyls = dedupe_cylinders(extract_cylinders(
        mesh, [c["axis"] for c in cands[:3]], max_rms=3 * nf))
    return {"mesh": mesh, "planes": planes, "cands": cands,
            "cyls": cyls, "noise_floor": nf}


def build(
    mesh_path: Path,
    out_path: Path,
    *,
    thresh: float = 0.4,
    choice: int = 0,
    previews_dir: Path | None = None,
) -> dict:
    """Measure the scan, rank frames, optionally render them, write frame.json."""
    m = measure(mesh_path, thresh=thresh)
    mesh, planes, cands = m["mesh"], m["planes"], m["cands"]
    cyls, nf = m["cyls"], m["noise_floor"]

    options = enumerate_frames(planes, cands, cyls, mesh)
    if not 0 <= choice < len(options):
        raise IndexError(f"choice {choice} out of range (0..{len(options) - 1})")
    picked = options[choice]

    R, origin = picked["rotation"], picked["origin"]
    aligned = (np.asarray(mesh.vertices) - origin) @ R.T
    bounds = np.array([aligned.min(axis=0), aligned.max(axis=0)])
    centre, scale = normalisation_for(bounds)

    notes = [
        f"chose option {choice} of {len(options)} (score {picked['score']:.3f})",
        f"+Z from {picked.get('z_why', 'plane')} (rms {picked['z_rms']:.4f})",
        f"+X from plane group area={picked['x_area']:.1f}mm2 rms={picked['x_rms']:.4f}",
        picked["origin_note"],
        f"scan noise floor {nf:.4f} mm",
    ]
    Frame(rotation=R.tolist(), origin=np.asarray(origin).tolist(),
          centre=centre, scale=scale, units="mm", notes=notes).save(out_path)

    previews: list[str] = []
    if previews_dir is not None:
        from ..preview import render_frame_candidate
        for i, opt in enumerate(options):
            sub = (f"+Z from {opt.get('z_why', 'plane')}"
                   f"   |   +X area={opt['x_area']:.0f}mm2"
                   f"   |   {opt['origin_note']}")
            previews.append(str(render_frame_candidate(
                mesh, opt["rotation"], opt["origin"],
                previews_dir / f"frame_option_{i}.png",
                title=f"Orientation option {i}"
                      + ("  (auto pick)" if i == 0 else ""),
                subtitle=sub)))

    return {
        "frame": str(out_path),
        "chosen": choice,
        "n_options": len(options),
        "n_planes": len(planes),
        "n_cylinders": len(cyls),
        "noise_floor": nf,
        "aligned_extents": (bounds[1] - bounds[0]).tolist(),
        "normalisation_scale": scale,
        "previews": previews,
        "notes": notes,
        "features": {
            "cylinders": [
                {"diameter": round(2 * c.radius, 4), "n_points": c.n_points}
                for c in cyls
            ],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mesh", type=Path)
    ap.add_argument("frame_out", type=Path)
    ap.add_argument("--thresh", type=float, default=0.4)
    ap.add_argument("--choice", type=int, default=0)
    ap.add_argument("--previews", type=Path, default=None)
    a = ap.parse_args()
    emit(build(a.mesh, a.frame_out, thresh=a.thresh, choice=a.choice,
               previews_dir=a.previews))


if __name__ == "__main__":
    main()
