"""Render orientation candidates as images so a human can choose one.

Frame selection cannot be fully automated - which face is "the bottom" is a
convention that depends on the part and on how the user intends to model it.
But it also should not require reading code or coordinates. This module
renders each candidate frame as a labelled orthographic triptych, so the
choice becomes "option B looks right".

Deliberately matplotlib rather than an OpenGL renderer: Fairsolid already
runs headless inside subprocesses, and pulling in a GL context (pyglet,
moderngl) adds a driver dependency that breaks in exactly the environments
this has to work in - WSL, CI, and remote shells.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.collections import PolyCollection

# Faces beyond this are decimated away before drawing; matplotlib's painter
# is O(n) per polygon and 200k faces takes minutes for no visual gain.
RENDER_FACE_BUDGET = 25_000

VIEWS = (
    ("Front  (looking along -Y)", (0, 2), (1, 1)),
    ("Right  (looking along +X)", (1, 2), (1, 1)),
    ("Top    (looking along -Z)", (0, 1), (1, 1)),
)


def _shade(mesh: trimesh.Trimesh, axis_pair: tuple[int, int]) -> tuple:
    """Project triangles onto two axes and shade them by depth + facing."""
    tris = np.asarray(mesh.triangles, dtype=float)
    i, j = axis_pair
    depth_axis = 3 - i - j

    poly = tris[:, :, [i, j]]
    depth = tris[:, :, depth_axis].mean(axis=1)

    # Painter's algorithm: draw far triangles first.
    order = np.argsort(depth)
    poly = poly[order]

    normals = np.asarray(mesh.face_normals, dtype=float)[order]
    light = np.array([0.3, 0.4, 0.87])
    light /= np.linalg.norm(light)
    intensity = 0.35 + 0.65 * np.clip(np.abs(normals @ light), 0, 1)
    colours = np.column_stack([
        intensity * 0.55, intensity * 0.68, intensity * 0.85,
    ])
    return poly, colours


def render_frame_candidate(
    mesh: trimesh.Trimesh,
    rotation: np.ndarray,
    origin: np.ndarray,
    out_path: Path,
    *,
    title: str = "",
    subtitle: str = "",
) -> Path:
    """Draw one candidate frame as three orthographic views with axes marked."""
    m = mesh.copy()
    if len(m.faces) > RENDER_FACE_BUDGET:
        m = m.simplify_quadric_decimation(face_count=RENDER_FACE_BUDGET)

    verts = (np.asarray(m.vertices, dtype=float) - np.asarray(origin)) @ np.asarray(rotation).T
    m = trimesh.Trimesh(vertices=verts, faces=m.faces, process=False)

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.8))
    fig.patch.set_facecolor("white")
    lo, hi = m.bounds
    span = float((hi - lo).max()) * 0.6
    centre = (lo + hi) / 2.0
    labels = "XYZ"

    for ax, (name, pair, _) in zip(axes, VIEWS):
        poly, colours = _shade(m, pair)
        ax.add_collection(PolyCollection(
            poly, facecolors=colours, edgecolors="none", antialiased=False))
        i, j = pair
        ax.set_xlim(centre[i] - span, centre[i] + span)
        ax.set_ylim(centre[j] - span, centre[j] + span)
        ax.set_aspect("equal")
        ax.set_title(name, fontsize=9, family="monospace")
        ax.set_xlabel(f"{labels[i]} (mm)", fontsize=8)
        ax.set_ylabel(f"{labels[j]} (mm)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, lw=0.3, alpha=0.35)
        # Mark the origin so the user can see where the part sits.
        ax.axhline(0, color="crimson", lw=0.8, alpha=0.7)
        ax.axvline(0, color="crimson", lw=0.8, alpha=0.7)
        ax.plot([0], [0], "o", color="crimson", ms=5)

    fig.suptitle(title, fontsize=12, weight="bold")
    if subtitle:
        fig.text(0.5, 0.925, subtitle, ha="center", fontsize=8.5,
                 family="monospace", color="#444")
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path
