# Interactions — what calls what, and where it runs

[← Home](../../README.md)

> **For the agent.** You (the person) don't need to run anything on this page. Your AI agent reads it and runs the commands. Your part is the 3 steps on the [home page](../../README.md#start-here-you-dont-run-any-of-this-yourself).

## Machines

| Where | What runs there |
|---|---|
| **PC, Windows** | Creality Scan, Fusion, FreeCAD, Fairsolid (`pipelines/fairsolid/` here; old runs in `C:\projects\_archive\2026-10-17-fairsolid\fairsolid\runs`, see [`docs/FAIRSOLID.md`](../FAIRSOLID.md)) |
| **PC, WSL Ubuntu** | This repo, both Python venvs, all solvers (CalculiX, Gmsh, Elmer, OpenFOAM, ParaView) |
| **Agent box** (Linux machine the AI agent works on) | Heavy or parallel runs (FEA iterations, topology, renders). Results are copied back into this repo; the box is not a source of truth |
| **GitHub** | `living-relation/handbuilt-cad` (this repo, includes Fairsolid); the old `living-relation/fairsolid` repo was deleted (2026-10-21) |

## Data flow

```
Creality Scan ──Mesh.ply──► Fairsolid (pipelines/fairsolid) ──10_clean / 15_ideal / 20_frame / 40_ref_surfaces──► part scripts here (WSL .venv)
                                                                                                        │ build123d
                                                                                                        ▼
                                                                                         <part>.step / .stl ──► Fusion / FreeCAD
                                                                                                        │
                                       knuckle_billet: mesh_*.py (gmsh) ─► fea_*.py (writes .inp) ─► ccx ─► post_*.py (.frd → SF, PNG, JSON)
                                                       topo_simp*.py / topo_stress.py (nlopt + pypardiso) ─► topo/ ─► knuckle_billet.py rebuild
```

## Script relationships (knuckle_billet)

- `loads.py` → writes `loads.json` (load cases used by every FEA script).
- `knuckle_billet.py` reads a `params.json`, builds the solid, writes STEP/STL + `*_build.json`; `check_interface.py` checks the 24 fixed features against `knuckle/feature_check/`.
- `mesh_step.py` / `mesh_stl.py` / `remesh.py` → Gmsh tet mesh (`*_mesh.npz`).
- `fea_iter.py` / `fea_v4b.py` → CalculiX deck (`*.inp`) per load case; `run_iter.sh` / `run_wsl.sh` run `ccx` and the post step.
- `post_iter.py` / `post_v4b.py` → safety factors (`fea_summary.json`), `.vtu`; `render_pv.py` / `render_solid.py` → pictures.
- `summarize_iter.py` → `iterations.csv`.
- `topo_simp.py`, `topo_simp_v2.py`, `topo_stress.py`, `topo_connect.py`, `topo_post.py`, `beso_map.py` → topology studies in `topo/`.
- `two_piece.py` + `joint_check.py` → two-piece version and bolted-joint hand check.
- `wall_check.py` → minimum wall / tool access for machining.

## Fairsolid link

Fairsolid is used as a tool, not a library: run it (`tools/scan_helper.py` or `pipelines/fairsolid/.venv/bin/fairsolid`), then read its output files from the run folder (`[paths] fairsolid_runs` / `FAIRSOLID_RUNS`, outside git). Runs made before 2026-10-17 are in `C:\projects\_archive\2026-10-17-fairsolid\fairsolid\runs\<part>\` (WSL: `/mnt/c/projects/_archive/2026-10-17-fairsolid/fairsolid/runs/<part>/`). Part code here doesn't import Fairsolid code.
