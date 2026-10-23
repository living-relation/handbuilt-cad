"""Stage 00 - load a scan and establish its real-world size.

Accepts what scanners actually emit: STL/OBJ/PLY/OFF meshes and XYZ/PTS/
ASC point clouds. Produces a single trimesh object plus a size report that
later stages use to decide tolerances.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

MESH_SUFFIXES = {".stl", ".obj", ".ply", ".off", ".3mf", ".glb", ".gltf"}
CLOUD_SUFFIXES = {".xyz", ".pts", ".asc", ".txt", ".csv"}

# A scan longer than this in its own units is almost certainly metres or
# inches mislabelled as mm; shorter than this, almost certainly metres.
# Used only to warn - never to silently rescale, because a wrong guess
# here is exactly the failure mode this project exists to prevent.
SUSPICIOUS_MAX_MM = 5000.0
SUSPICIOUS_MIN_MM = 1.0


def load(path: str | Path) -> trimesh.Trimesh | trimesh.PointCloud:
    """Load a scan, tolerating the messiness of real scanner output."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()

    if suffix in CLOUD_SUFFIXES:
        pts = _load_ascii_cloud(path)
        return trimesh.PointCloud(pts)

    if suffix not in MESH_SUFFIXES:
        raise ValueError(
            f"unsupported scan format {suffix!r}; "
            f"expected one of {sorted(MESH_SUFFIXES | CLOUD_SUFFIXES)}"
        )

    obj = trimesh.load(path, force="mesh", process=False)
    if isinstance(obj, trimesh.Scene):
        obj = trimesh.util.concatenate(
            [g for g in obj.geometry.values() if isinstance(g, trimesh.Trimesh)]
        )
    if obj is None or (hasattr(obj, "faces") and len(obj.faces) == 0):
        raise ValueError(f"{path.name} contains no triangles")
    return obj


def _load_ascii_cloud(path: Path) -> np.ndarray:
    """Read an XYZ-style cloud, ignoring any extra normal/colour columns."""
    for delimiter in (None, ",", ";"):
        try:
            arr = np.loadtxt(path, delimiter=delimiter, ndmin=2)
        except Exception:
            continue
        if arr.ndim == 2 and arr.shape[1] >= 3:
            return arr[:, :3].astype(float)
    raise ValueError(f"could not parse {path.name} as an ASCII point cloud")


def describe(obj) -> dict:
    """Summarise the scan, flagging anything that smells like a unit error."""
    bounds = np.asarray(obj.bounds, dtype=float)
    extents = (bounds[1] - bounds[0]).astype(float)
    longest = float(extents.max())

    is_mesh = isinstance(obj, trimesh.Trimesh)
    info = {
        "kind": "mesh" if is_mesh else "pointcloud",
        "vertices": int(len(obj.vertices)),
        "faces": int(len(obj.faces)) if is_mesh else 0,
        "bounds": bounds.tolist(),
        "extents": extents.tolist(),
        "longest_extent": longest,
        "warnings": [],
    }

    if is_mesh:
        info["watertight"] = bool(obj.is_watertight)
        info["winding_consistent"] = bool(obj.is_winding_consistent)
        # Volume is only meaningful once the mesh is closed.
        info["volume"] = float(obj.volume) if obj.is_watertight else None
        euler = int(obj.euler_number)
        info["euler_number"] = euler
        if not obj.is_watertight:
            info["warnings"].append(
                "mesh is not watertight - stage 10 will run Poisson reconstruction"
            )

    if longest > SUSPICIOUS_MAX_MM:
        info["warnings"].append(
            f"longest extent {longest:.1f} suggests the file is not in mm "
            "(metres or microns?) - pass --units to override"
        )
    elif longest < SUSPICIOUS_MIN_MM:
        info["warnings"].append(
            f"longest extent {longest:.4f} is implausibly small for mm "
            "- pass --units to override"
        )
    return info
