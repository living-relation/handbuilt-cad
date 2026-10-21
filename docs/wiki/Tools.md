# Tools & dependencies

[← Home](../../README.md)

> **For the agent.** You (the person) don't need to run anything on this page. Your AI agent reads it and runs the commands. Your part is the 3 steps on the [home page](../../README.md#start-here-you-dont-run-any-of-this-yourself).

## Python environments (WSL)

| Env | Path | Python | Used for | Pinned list |
|---|---|---|---|---|
| Build venv | `.venv/` in this repo | 3.13 | build123d models, scan measuring (trimesh, numpy, scipy, rtree, scikit-learn, matplotlib) | `requirements.txt` |
| Sim venv | `~/simvenv` | 3.14 | meshing and FEA post (gmsh 4.15.2, meshio, pygmsh, vtk 9.7.1, ccx2paraview), topology (nlopt 2.11, pypardiso 0.4.7, scikit-image) | `requirements-sim.txt` |

Key versions: build123d 0.13.0 (OCP 8.0.1.1), trimesh 5.1.1, numpy 2.5.3, scipy 1.18.1.

Recreate everything: `bash setup.sh` (see [Setup](Setup.md)).

## Repo tools (`tools/`, for the agent)

| Tool | What it does |
|---|---|
| `features.py` | Lists round holes/bosses and checks them against a `spec.json` |
| `cnc_check.py` | CNC screen: setups, inside/vertical corners, thin walls |
| `quick_fea.py` | Quick linear strength check (Gmsh + CalculiX, sim venv) |
| `views.py` | 6-view picture sheet (`--six` plain 6 views) |
| `viewer.py` | Spin-around 3D viewer in one HTML file |
| `an_fitting.py` | Male AN / JIC 37° flare fitting end (`-10`, `-6`) with a real helical UNF thread; import `male_an_leg` in part scripts or run it to write a checked STEP |

Usage and examples: [How to use it](How-To-Use.md#tool-cheat-sheet).

## Simulation tools (WSL Ubuntu 26.04)

| Tool | Version | Where |
|---|---|---|
| CalculiX `ccx` | 2.21 (apt) in WSL; 2.23 is used on the agent box | `/usr/bin/ccx` |
| Gmsh | 4.14 (apt) + 4.15.2 Python module | `/usr/bin/gmsh` |
| Elmer FEM | 26.2.1, built from source | `/opt/elmer` |
| OpenFOAM | 14 (openfoam.org apt) | `/opt/openfoam14` |
| ParaView | 6.0.1 (apt), `pvpython` headless via `xvfb-run` | `/usr/bin/paraview` |

Load them with `source sim/wsl-env.sh`. Full details, smoke tests and rollback: [`sim/SIM_TOOLS.md`](../../sim/SIM_TOOLS.md).

## Windows side

- **FreeCAD 1.1.4** portable at `C:\projects\_tools\FreeCAD` (`FreeCAD.bat`; `ccx_wsl.bat` / `gmsh_wsl.bat` wrappers let it use the WSL solvers).
- **Fusion** opens the STEP files.
- **Ollama** with `qwen2.5-coder:14b` is available locally for helper/coding tasks (optional; nothing in this repo requires it).
- **Creality Scan** for scanning.

## Related repo

- **Fairsolid** — `pipelines/fairsolid/` (own venv: `bash setup.sh --with-fairsolid`; see its README and `docs/FAIRSOLID.md`). The old `living-relation/fairsolid` GitHub repo was deleted on 2026-10-21.
