"""Pictures of whatever did not turn out right.

the user's standing request: every fail, marginal result or bad area gets PNGs
he can look at - the whole part from three views, close-ups of each problem
area, and a deviation colour map against the scan. Everything here is
matplotlib off-screen (same reason as preview.py: no GL context), and every
image lands in the run folder's review/ directory.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.cm import ScalarMappable
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from scipy.spatial import cKDTree

from .preview import RENDER_FACE_BUDGET, VIEWS

GREY = np.array([0.72, 0.72, 0.72])
CMAP = "coolwarm"


def deviation_colours(dev: np.ndarray, limit: float) -> np.ndarray:
    """Blue = scan inside the model surface, red = outside, grey = not measured."""
    cmap = plt.get_cmap(CMAP)
    out = np.tile(GREY, (len(dev), 1))
    ok = np.isfinite(dev)
    out[ok] = cmap(np.clip(dev[ok] / limit, -1, 1) * 0.5 + 0.5)[:, :3]
    return out


def _decimated(mesh: trimesh.Trimesh, values: np.ndarray, budget: int):
    """Decimate for drawing; carry per-face values across by nearest face."""
    if len(mesh.faces) <= budget:
        return mesh, values
    small = mesh.simplify_quadric_decimation(face_count=budget)
    _, idx = cKDTree(np.asarray(mesh.triangles_center)).query(
        np.asarray(small.triangles_center))
    return small, values[idx]


def render_views(mesh: trimesh.Trimesh, face_rgb: np.ndarray, out_path: Path, *,
                 title: str, subtitle: str = "", limit: float | None = None,
                 cbar_label: str = "deviation (mm)", box=None,
                 budget: int = RENDER_FACE_BUDGET) -> Path:
    """Three orthographic views with per-face colours, optional colour bar.

    `box` (lo, hi) zooms all three views onto a region - the close-ups.
    """
    m, rgb = _decimated(mesh, np.asarray(face_rgb, float), budget)
    tris = np.asarray(m.triangles, float)
    normals = np.asarray(m.face_normals, float)
    light = np.array([0.3, 0.4, 0.87]) / np.linalg.norm([0.3, 0.4, 0.87])
    inten = 0.45 + 0.55 * np.clip(np.abs(normals @ light), 0, 1)

    lo, hi = (m.bounds if box is None else box)
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    span = float((hi - lo).max()) * 0.6
    centre = (lo + hi) / 2
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
    for ax, (name, (i, j), _) in zip(axes, VIEWS):
        depth = tris[:, :, 3 - i - j].mean(axis=1)
        order = np.argsort(depth)
        ax.add_collection(PolyCollection(
            tris[order][:, :, [i, j]], facecolors=rgb[order] * inten[order][:, None],
            edgecolors="none", antialiased=False))
        ax.set_xlim(centre[i] - span, centre[i] + span)
        ax.set_ylim(centre[j] - span, centre[j] + span)
        ax.set_aspect("equal")
        ax.set_title(name, fontsize=9, family="monospace")
        ax.set_xlabel(f"{'XYZ'[i]} (mm)", fontsize=8)
        ax.set_ylabel(f"{'XYZ'[j]} (mm)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, lw=0.3, alpha=0.35)
    fig.suptitle(title, fontsize=11, weight="bold", y=0.985)
    if subtitle:
        fig.text(0.5, 0.925, subtitle, ha="center", fontsize=8.5,
                 family="monospace", color="#444")
    if limit is not None:
        fig.subplots_adjust(top=0.84, bottom=0.22, left=0.05, right=0.98, wspace=0.25)
        sm = ScalarMappable(norm=Normalize(-limit, limit), cmap=CMAP)
        cax = fig.add_axes((0.15, 0.08, 0.7, 0.03))
        cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
        cb.set_label(f"{cbar_label}; grey = not measured; colour saturates "
                     f"at +/-{limit:.3g} mm", fontsize=8)
        cb.ax.tick_params(labelsize=7)
    else:
        fig.tight_layout(rect=(0, 0, 1, 0.88))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path


def closeup_box(mesh: trimesh.Trimesh, face_mask: np.ndarray, *,
                margin_frac: float = 0.25, min_margin: float = 3.0):
    """Bounding box of the selected faces, padded so their surroundings show."""
    tri = np.asarray(mesh.triangles)[face_mask].reshape(-1, 3)
    lo, hi = tri.min(axis=0), tri.max(axis=0)
    pad = max(min_margin, margin_frac * float((hi - lo).max()))
    return lo - pad, hi + pad


def crop(mesh: trimesh.Trimesh, values: np.ndarray, box):
    """Faces whose centres fall inside box, so the close-up is not hidden
    behind the rest of the part in an orthographic view."""
    c = np.asarray(mesh.triangles_center)
    lo, hi = box
    keep = np.all((c >= lo) & (c <= hi), axis=1)
    sub = mesh.submesh([np.flatnonzero(keep)], append=True, repair=False)
    return sub, values[keep]


def render_closeup(mesh: trimesh.Trimesh, face_rgb: np.ndarray, face_mask: np.ndarray,
                   out_path: Path, *, title: str, subtitle: str = "",
                   limit: float | None = None,
                   cbar_label: str = "deviation (mm)") -> Path:
    box = closeup_box(mesh, face_mask)
    sub, rgb = crop(mesh, np.asarray(face_rgb, float), box)
    return render_views(sub, rgb, out_path, title=title, subtitle=subtitle,
                        limit=limit, box=box, cbar_label=cbar_label)


def problem_regions(mesh: trimesh.Trimesh, bad: np.ndarray, *, top: int = 6,
                    min_area: float = 2.0) -> list[np.ndarray]:
    """Connected patches of bad faces, largest first, as face masks."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    adj = np.asarray(mesh.face_adjacency)
    both = adj[bad[adj[:, 0]] & bad[adj[:, 1]]]
    n = len(mesh.faces)
    g = coo_matrix((np.ones(len(both)), (both[:, 0], both[:, 1])), shape=(n, n))
    _, comp = connected_components(g, directed=False)
    area = np.asarray(mesh.area_faces)
    comp_area = np.bincount(comp[bad], weights=area[bad], minlength=comp.max() + 1)
    order = [c for c in np.argsort(-comp_area) if comp_area[c] >= min_area][:top]
    return [(comp == c) & bad for c in order]
