# Hand-built models

Daniel's scan-to-CAD workshop: 3D scans of real car parts are measured in Python, the sizes are rounded to real values, and a [build123d](https://github.com/gumyr/build123d) script builds a clean, machinable solid (STEP for Fusion). Some parts then go through strength checks (CalculiX FEA), topology optimisation and machining planning.

This README is the front page of a small wiki. Start here, then follow the links.

| Page | What it answers |
|---|---|
| [Overview](docs/wiki/Overview.md) | What this is, the big picture, what lives where (PC / WSL / box / GitHub) |
| [Layout](docs/wiki/Layout.md) | Where every folder and file goes, and where new work should go |
| [Workflow](docs/wiki/Workflow.md) | Scan → triage → Fairsolid helper → hand-built script → STEP/Fusion → FEA/topology → machining |
| [Parts index](docs/wiki/Parts.md) | Every part, its status, key numbers and files |
| [Tools & dependencies](docs/wiki/Tools.md) | Python venvs, CAD/FEA tools, versions, how to reinstall |
| [Interactions](docs/wiki/Interactions.md) | Which script calls what, and what runs on the PC, in WSL, or on the agent box |
| [Conventions](docs/wiki/Conventions.md) | Rules: true scan scale, smooth machined-look solids, units, git habits |
| [For AI agents](docs/wiki/AI-agents.md) | How an AI tool should read, run and change this repo safely |
| [Scans index](scans/INDEX.md) | The raw scans (not stored here): where they are, size, triangle count, hash |

## Quick start (WSL Ubuntu)

```bash
cd ~/projects/handbuilt-models
bash sim-tools/scripts/setup_venv_wsl.sh        # build venv (.venv) if missing
cd pcv_adapter && ../.venv/bin/python pcv_adapter.py   # rebuild a part -> STEP + STL next to the script
source ../sim-tools/wsl-env.sh                  # load FEA/CFD tools (CalculiX, Gmsh, OpenFOAM, simvenv)
```

New machine? `bash sim-tools/scripts/install_sim_tools_wsl.sh` installs the simulation tools, and `requirements.txt` / `requirements-sim.txt` pin the Python packages.

## Related repo

- **Fairsolid** (scan cleanup and measuring helper) is a separate repo: <https://github.com/living-relation/fairsolid>. It is linked, not merged. Version last used with this repo: `bbc57143a6d83980548e497ca624567174f7d17d` (2026-10-09). See [Interactions](docs/wiki/Interactions.md).

## Not in this repo

Raw scans (private and too big; see [scans/INDEX.md](scans/INDEX.md)), STEP files over 50 MB (the cast knuckle v3/v4/v4b STEPs, about 250 MB each; the STL and the build script are here, so the STEP can be rebuilt), solver run output (meshes, `.frd`, `.vtu`), the Python venvs, and the FreeCAD install.

## Where the working copy lives

- WSL Ubuntu: `/home/daniel/projects/handbuilt-models` (the real working copy, branch `main`).
- From Windows: `\\wsl.localhost\Ubuntu\home\daniel\projects\handbuilt-models`; shortcut in `C:\projects\active\handbuilt-models`.

All designs are shared for reference. They are hand-built approximations of scanned parts; check every dimension and do your own engineering before machining or fitting anything to a car.
