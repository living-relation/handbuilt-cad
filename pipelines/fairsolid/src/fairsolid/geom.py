"""Rigid frames, unit-cube normalization, and their inverses.

This module carries the single most important invariant in Fairsolid:

    Absolute scale and world orientation are recorded BEFORE the scan is
    handed to anything that normalizes, and re-applied AFTER a solid comes
    back. No downstream stage is trusted to preserve millimetres.

Every published scan-to-CAD model (CAD-Recode, cadrille, CADReasoner)
centres the input and rescales it into a cube of side 2, then emits
dimensionless code. Their benchmarks use IoU, which is scale-invariant, so
the loss never shows up in a published number - but it is fatal for a STEP
file that has to be manufactured. `Frame` is what makes it recoverable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np

# CAD-Recode / cadrille / CADReasoner all normalise into a cube of side 2
# spanning [-1, 1]. Matching it exactly means the model sees the input
# distribution it was trained on.
MODEL_CUBE_SIDE = 2.0


@dataclass
class Frame:
    """Maps scan coordinates to canonical CAD coordinates, reversibly.

    Forward (scan -> canonical):   p_c = R @ (p_s - origin)
    Normalise (canonical -> unit): p_n = (p_c - centre) * scale
    """

    # World alignment
    rotation: list = field(default_factory=lambda: np.eye(3).tolist())
    origin: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    # Unit-cube normalisation
    centre: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: float = 1.0
    # Provenance
    units: str = "mm"
    notes: list = field(default_factory=list)

    # -- matrices -------------------------------------------------------
    @property
    def R(self) -> np.ndarray:
        return np.asarray(self.rotation, dtype=float)

    def to_canonical(self, pts: np.ndarray) -> np.ndarray:
        """Scan coords -> axis-aligned CAD coords, still in real units."""
        pts = np.asarray(pts, dtype=float)
        return (pts - np.asarray(self.origin)) @ self.R.T

    def from_canonical(self, pts: np.ndarray) -> np.ndarray:
        pts = np.asarray(pts, dtype=float)
        return pts @ self.R + np.asarray(self.origin)

    def to_unit(self, pts: np.ndarray) -> np.ndarray:
        """Canonical real-unit coords -> the [-1,1] cube a model expects."""
        pts = np.asarray(pts, dtype=float)
        return (pts - np.asarray(self.centre)) * self.scale

    def from_unit(self, pts: np.ndarray) -> np.ndarray:
        """The inverse that every published pipeline omits."""
        pts = np.asarray(pts, dtype=float)
        return pts / self.scale + np.asarray(self.centre)

    def unit_to_canonical_matrix(self) -> np.ndarray:
        """4x4 taking model-space output back to canonical real units.

        Applied to a whole solid rather than point-by-point, so a STEP body
        can be de-normalised in one transform.
        """
        m = np.eye(4)
        m[:3, :3] = np.eye(3) / self.scale
        m[:3, 3] = np.asarray(self.centre)
        return m

    # -- io -------------------------------------------------------------
    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "Frame":
        return cls(**json.loads(Path(path).read_text()))


def normalisation_for(bounds: np.ndarray) -> tuple[list, float]:
    """Return (centre, scale) reproducing the models' own preprocessing.

    Mirrors CAD-Recode's demo exactly:
        mesh.apply_translation(-(bounds[0] + bounds[1]) / 2)
        mesh.apply_scale(2.0 / max(extents))
    """
    bounds = np.asarray(bounds, dtype=float)
    centre = (bounds[0] + bounds[1]) / 2.0
    extents = bounds[1] - bounds[0]
    longest = float(np.max(extents))
    if longest <= 0:
        raise ValueError("degenerate bounds: object has zero extent")
    return centre.tolist(), MODEL_CUBE_SIDE / longest


def orthonormalise(primary: np.ndarray, secondary: np.ndarray) -> np.ndarray:
    """Build a right-handed rotation whose rows are the CAD axes.

    `primary` becomes +Z, `secondary` is Gram-Schmidt'd into the XY plane
    to become +X. Rows (not columns) are the axes, so `pts @ R.T` maps
    scan coords into the frame.
    """
    z = np.asarray(primary, dtype=float)
    z = z / np.linalg.norm(z)

    x = np.asarray(secondary, dtype=float)
    x = x - np.dot(x, z) * z
    nx = np.linalg.norm(x)
    if nx < 1e-9:
        # Secondary was parallel to primary; pick any perpendicular axis.
        fallback = np.array([1.0, 0.0, 0.0])
        if abs(np.dot(fallback, z)) > 0.9:
            fallback = np.array([0.0, 1.0, 0.0])
        x = fallback - np.dot(fallback, z) * z
        nx = np.linalg.norm(x)
    x = x / nx

    y = np.cross(z, x)
    return np.vstack([x, y, z])
