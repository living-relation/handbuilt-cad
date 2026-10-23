"""Stage 10 - make the scan geometrically legal.

Raw scans carry non-manifold edges, duplicated vertices, flipped normals and
holes. Feeding that to a CAD kernel guarantees failure, so this stage runs
the MeshLab repair chain the reverse-engineering literature settles on.

Filter names and parameter names below were read out of the installed
pymeshlab (2025.7) with pymeshlab.print_filter_parameter_list(), not copied
from documentation - see recipes/meshlab.md.

Run standalone:
    python -m fairsolid.stages.s10_sanitize IN OUT [--target-faces N] [--no-poisson]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pymeshlab

from ..subproc import emit

# Poisson octree depth. 8 is MeshLab's default and under-resolves scan
# detail; 10 roughly matches typical structured-light density without the
# runaway memory of 11+.
POISSON_DEPTH = 10

# Below this the mesh is already light enough that decimation only costs
# accuracy.
DECIMATE_FLOOR = 200_000


def sanitize(
    src: Path,
    dst: Path,
    *,
    target_faces: int | None = None,
    poisson: bool = True,
    poisson_depth: int = POISSON_DEPTH,
) -> dict:
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(src))
    steps: list[str] = []

    def before() -> tuple[int, int]:
        m = ms.current_mesh()
        return m.vertex_number(), m.face_number()

    v0, f0 = before()

    # 1. Topological hygiene. Order matters: duplicates first, because
    #    non-manifold repair reports false positives on doubled vertices.
    for name in (
        "meshing_remove_duplicate_vertices",
        "meshing_remove_duplicate_faces",
        "meshing_remove_unreferenced_vertices",
        "meshing_repair_non_manifold_edges",
        "meshing_repair_non_manifold_vertices",
    ):
        try:
            ms.apply_filter(name)
            steps.append(name)
        except Exception as exc:  # a filter may legitimately find nothing
            steps.append(f"{name} (skipped: {exc})")

    # 2. Screened Poisson. Wraps a continuous isosurface around the scan,
    #    sealing holes and averaging out sensor noise. It needs per-vertex
    #    normals, which a raw STL does not carry.
    if poisson:
        ms.apply_filter("compute_normal_per_vertex")
        steps.append("compute_normal_per_vertex")
        ms.apply_filter(
            "generate_surface_reconstruction_screened_poisson",
            depth=poisson_depth,
            preclean=True,      # drop degenerate faces before solving
            samplespernode=1.5,
        )
        steps.append(
            f"generate_surface_reconstruction_screened_poisson(depth={poisson_depth})"
        )
        # Poisson emits a new layer; make it current.
        ms.set_current_mesh(ms.mesh_number() - 1)

    # 3. Decimate only if still heavy. planarquadric is what keeps flat
    #    mechanical faces flat and sharp edges sharp - without it, quadric
    #    collapse rounds off exactly the features we need to fit primitives to.
    faces_now = ms.current_mesh().face_number()
    goal = target_faces or DECIMATE_FLOOR
    if faces_now > goal:
        ms.apply_filter(
            "meshing_decimation_quadric_edge_collapse",
            targetfacenum=goal,
            preserveboundary=True,
            preservenormal=True,
            preservetopology=True,
            planarquadric=True,
            autoclean=True,
        )
        steps.append(f"meshing_decimation_quadric_edge_collapse(target={goal})")

    dst.parent.mkdir(parents=True, exist_ok=True)
    ms.save_current_mesh(str(dst))

    m = ms.current_mesh()
    return {
        "input": str(src),
        "output": str(dst),
        "vertices_before": v0,
        "faces_before": f0,
        "vertices_after": m.vertex_number(),
        "faces_after": m.face_number(),
        "steps": steps,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--target-faces", type=int, default=None)
    ap.add_argument("--no-poisson", action="store_true")
    ap.add_argument("--poisson-depth", type=int, default=POISSON_DEPTH)
    a = ap.parse_args()
    emit(sanitize(a.src, a.dst, target_faces=a.target_faces,
                  poisson=not a.no_poisson, poisson_depth=a.poisson_depth))


if __name__ == "__main__":
    main()
