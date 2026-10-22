# Interactions — what calls what, and where it runs

[← Home](../../README.md)

> **For the agent.** You (the person) don't need to run anything on this page. Your AI agent reads it and runs the commands. Your part is the 3 steps on the [home page](../../README.md#start-here-you-dont-run-any-of-this-yourself).

## Machines

| Where | What runs there |
|---|---|
| **PC, Windows** | Creality Scan, Fusion, FreeCAD, Fairsolid (`pipelines/fairsolid/` here; older runs in the archived checkout, see [`docs/FAIRSOLID.md`](../FAIRSOLID.md)) |
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
                                       structural part: mesh (gmsh) -> CalculiX deck (.inp) -> ccx -> post (.frd -> SF, PNG, JSON), all in ~/cad-parts/<job>/runs/<stamp>/
```

## Part scripts

Part build scripts live in the parts home (`~/cad-parts/<job>/src/`), not in this repo. A typical structural part has a build script that reads a `params.json` and writes STEP + `*_build.json`, a loads script, mesh / FEA / post scripts, and an interface check. Their working outputs go to `~/cad-parts/<job>/runs/<stamp>/`; finished results are published to the models folder.

## Fairsolid link

Fairsolid is used as a tool, not a library: run it (`tools/scan_helper.py` or `pipelines/fairsolid/.venv/bin/fairsolid`), then read its output files from the run folder (`[paths] fairsolid_runs` / `FAIRSOLID_RUNS`, outside git). Runs made before 2026-10-17 are in the archived checkout's `runs/<part>/` (see `docs/FAIRSOLID.md`). Part code here doesn't import Fairsolid code.
