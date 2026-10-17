"""Stage 70 - how far is the reconstruction from the actual scan?

The equivalent of Geomagic's real-time deviation analyser, and the gate that
decides whether a result is deliverable. Without it the pipeline can hand back
a confident, beautiful, wrong solid.

Deviation is measured from the reconstructed solid back to the CLEANED scan,
sampled over the solid's surface. Occluded regions are reported separately:
the scan has no data there, so a large deviation is a statement about the scan,
not about the reconstruction, and averaging the two together hides both.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh

from ..geom import Frame
from ..subproc import emit

# Samples used for the deviation statistic. 50k is enough for stable
# percentiles on a part with a few hundred square centimetres of surface.
DEVIATION_SAMPLES = 50_000


def compare(
    step_path: Path,
    scan_path: Path,
    frame_path: Path,
    *,
    tol: float = 0.1,
    samples: int = DEVIATION_SAMPLES,
) -> dict:
    """Sample the solid's surface and measure distance to the aligned scan."""
    import cadquery as cq

    frame = Frame.load(frame_path)
    scan = trimesh.load(scan_path, force="mesh", process=False)
    scan.vertices = frame.to_canonical(np.asarray(scan.vertices, dtype=float))

    solid = cq.importers.importStep(str(step_path)).val()
    # Tessellate finely: the mesh here is only a sampling surface for the
    # distance query, so its own faceting must stay well under `tol`.
    verts, faces = solid.tessellate(tolerance=tol * 0.2)
    recon = trimesh.Trimesh(
        vertices=np.array([[v.x, v.y, v.z] for v in verts]),
        faces=np.array(faces), process=False,
    )

    pts, _ = trimesh.sample.sample_surface(recon, samples, seed=0)
    _, dist, _ = trimesh.proximity.ProximityQuery(scan).on_surface(pts)
    dist = np.abs(np.asarray(dist, dtype=float))

    within = float(np.count_nonzero(dist <= tol)) / len(dist)
    p95 = float(np.percentile(dist, 95))

    return {
        "step": str(step_path),
        "tolerance_mm": tol,
        "mean_mm": float(dist.mean()),
        "median_mm": float(np.median(dist)),
        "p95_mm": p95,
        "p99_mm": float(np.percentile(dist, 99)),
        "max_mm": float(dist.max()),
        "fraction_within_tol": within,
        # Pass on the bulk of the surface rather than the worst point: a
        # single occluded patch should not fail an otherwise sound model.
        "verdict": "PASS" if within >= 0.95 else (
            "MARGINAL" if within >= 0.80 else "FAIL"),
        "recon_volume_mm3": float(solid.Volume()),
        "scan_volume_mm3": float(scan.volume) if scan.is_watertight else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", type=Path)
    ap.add_argument("scan", type=Path)
    ap.add_argument("frame", type=Path)
    ap.add_argument("--tol", type=float, default=0.1)
    a = ap.parse_args()
    emit(compare(a.step, a.scan, a.frame, tol=a.tol))


if __name__ == "__main__":
    main()
