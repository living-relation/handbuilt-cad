"""Stage 75 - pictures of a reconstruction that did not pass.

the user's standing request: when a model fails or comes out marginal, show it.
Writes into <run>/review/:

  <tag>_model_views.png         the reconstructed solid from three views
  <tag>_deviation_overview.png  the averaged scan coloured by its distance
                                to the solid (red = scan outside the model,
                                blue = inside)
  <tag>_problem_NN.png          close-ups of the biggest patches outside
                                tolerance

Measures only; changes nothing. Runs in its own process because it loads the
STEP through CadQuery/OCCT.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from ..geom import Frame
from ..subproc import emit

SURFACE_SAMPLES = 400_000
MAX_PROBLEM_CLOSEUPS = 6


def review(step_path: Path, scan_path: Path, frame_path: Path, out_dir: Path, *,
           tol: float, tag: str, verdict: str = "") -> dict:
    import cadquery as cq

    from ..review import (deviation_colours, problem_regions, render_closeup,
                          render_views)

    frame = Frame.load(frame_path)
    scan = trimesh.load(scan_path, force="mesh", process=False)
    scan = trimesh.Trimesh(frame.to_canonical(np.asarray(scan.vertices, float)),
                           np.asarray(scan.faces), process=False)

    solid = cq.importers.importStep(str(step_path)).val()
    v, f = solid.tessellate(tolerance=tol * 0.2)
    recon = trimesh.Trimesh(np.array([[p.x, p.y, p.z] for p in v]), np.array(f),
                            process=False)

    # Signed distance from each scan face to the solid: nearest dense surface
    # sample, then the offset along that sample's normal (exact on flat
    # regions whatever the sample spacing).
    pts, fid = trimesh.sample.sample_surface(recon, SURFACE_SAMPLES, seed=0)
    nrm = np.asarray(recon.face_normals)[fid]
    c = np.asarray(scan.triangles_center)
    d, idx = cKDTree(pts).query(c)
    signed = np.einsum("ij,ij->i", c - pts[idx], nrm[idx])
    # Far from the solid (missing material) the projection understates the
    # gap; use the straight distance there, keeping the sign.
    dev = np.where(d > 3 * tol, np.sign(signed) * d, signed)

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob(f"{tag}_*.png"):
        old.unlink()
    absd = np.abs(dev)
    within = float((absd <= tol).mean())
    limit = max(3 * tol, float(np.percentile(absd, 95)))
    head = f"{verdict + ': ' if verdict else ''}{step_path.name}"
    paths = [render_views(
        recon, np.tile([0.55, 0.68, 0.85], (len(recon.faces), 1)),
        out_dir / f"{tag}_model_views.png",
        title=f"{head} - the reconstructed solid",
        subtitle=f"{len(recon.faces)} triangles from the STEP; same frame as the scan")]
    paths.append(render_views(
        scan, deviation_colours(dev, limit), out_dir / f"{tag}_deviation_overview.png",
        title=f"{head} - averaged scan vs the solid",
        subtitle=(f"distance from each scan face to the solid (stage 70 measures "
                  f"solid -> scan); {within * 100:.1f}% within {tol} mm; median "
                  f"{np.median(absd):.3f}  p95 {np.percentile(absd, 95):.3f}  "
                  f"max {absd.max():.3f} mm"),
        limit=limit, cbar_label="scan minus model (mm)"))
    regions = problem_regions(scan, absd > tol, top=MAX_PROBLEM_CLOSEUPS)
    for k, m in enumerate(regions):
        a = float(np.asarray(scan.area_faces)[m].sum())
        paths.append(render_closeup(
            scan, deviation_colours(dev, limit), m,
            out_dir / f"{tag}_problem_{k + 1:02d}.png",
            title=f"{head} - problem area {k + 1} of {len(regions)} "
                  f"({a:.0f} mm2 outside {tol} mm)",
            subtitle=(f"worst {absd[m].max():.3f} mm, median "
                      f"{np.median(absd[m]):.3f} mm in this patch"),
            limit=limit, cbar_label="scan minus model (mm)"))
    return {"step": str(step_path), "tolerance_mm": tol,
            "fraction_within_tol": within,
            "median_mm": float(np.median(absd)),
            "p95_mm": float(np.percentile(absd, 95)), "max_mm": float(absd.max()),
            "images": [str(p) for p in paths]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", type=Path)
    ap.add_argument("scan", type=Path)
    ap.add_argument("frame", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--tol", type=float, default=0.15)
    ap.add_argument("--tag", default="50")
    ap.add_argument("--verdict", default="")
    a = ap.parse_args()
    emit(review(a.step, a.scan, a.frame, a.out_dir, tol=a.tol, tag=a.tag,
                verdict=a.verdict))


if __name__ == "__main__":
    main()
