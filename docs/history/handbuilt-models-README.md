# Hand-built models — a CAD toolkit for CNC and custom parts

A small, free toolkit for turning measurements (and 3D scans) into clean, machinable CAD parts, and checking them before you cut metal: build123d scripts → STEP for Fusion/CAM → hole/fitment checks → quick strength checks (Gmsh + CalculiX) → 6-view picture sheets and a browser 3D viewer → machining notes. Runs on Linux or Windows (WSL).

## Start here: you don't run any of this yourself

This toolkit is driven by an **AI agent** (Claude Code, Cursor, Codex, Grok Bot or similar). You never have to type the commands on the other pages. They're written for the agent. All you do:

1. **Install it.** One script, once. See [Install](docs/wiki/Install.md).
2. **Point your AI agent at this repo.** Tell it where the folder is and to read this README.
3. **Hand it your scan, mesh or idea.** A `.stl`/`.ply`/`.obj` file, a 3D scan, or just a description and some sizes. The agent builds the part, checks it, and shows you pictures and a STEP for your CAM.

**What to tell your agent** (copy, then change the details):

> Use the handbuilt-models repo in `~/handbuilt-models` (start with `README.md` and `docs/wiki/AI-agents.md`). Here's a scan of my bracket: `~/scans/bracket.stl`. Make a clean STEP I can machine from 6061, keep the holes where they are on the scan, run the fit, CNC and strength checks, and show me the 6-view sheet before you call it done.

Or start from an idea instead of a scan:

> Using handbuilt-models, design a 90° -10 AN adapter pipe, no longer than 53 mm, with a smooth bore. Show me the 6-view sheet and the checks.

Everything below is the technical detail the agent reads.

**For the agent: start with these three pages:**

1. **[Install](docs/wiki/Install.md)**: get it running on a new PC (one script).
2. **[Setup](docs/wiki/Setup.md)**: what got installed and how to check it.
3. **[How to use](docs/wiki/How-To-Use.md)**: the everyday workflow, with a worked example (sample L-bracket).

```bash
git clone https://github.com/living-relation/handbuilt-models.git && cd handbuilt-models
bash setup.sh                         # safe to re-run
source sim-tools/env.sh && bash examples/bracket/run_all.sh
```

The part folders (knuckle, bezel, PCV pipe, ...) are real projects built with these tools, kept as examples.

This README is the front page of a small wiki:

| Page | What it answers |
|---|---|
| [Install](docs/wiki/Install.md) | For you: the 3 steps, and installing on a new Windows (WSL) or Linux PC |
| [Setup](docs/wiki/Setup.md) | For the agent: what setup.sh installs, options, how to check it worked |
| [How to use](docs/wiki/How-To-Use.md) | For the agent: everyday workflow, worked example, tool cheat-sheet |
| [Overview](docs/wiki/Overview.md) | What this is, the big picture, what lives where (PC / WSL / box / GitHub) |
| [Layout](docs/wiki/Layout.md) | Where every folder and file goes, and where new work should go |
| [Workflow](docs/wiki/Workflow.md) | Scan → triage → Fairsolid helper → hand-built script → STEP/Fusion → FEA/topology → machining |
| [Parts index](docs/wiki/Parts.md) | Every part, its status, key numbers and files |
| [Tools & dependencies](docs/wiki/Tools.md) | For the agent: Python venvs, CAD/FEA tools, versions, how to reinstall |
| [Interactions](docs/wiki/Interactions.md) | For the agent: which script calls what, and what runs on the PC, in WSL, or on the agent box |
| [Conventions](docs/wiki/Conventions.md) | Rules: true scan scale, smooth machined-look solids, units, git habits |
| [For AI agents](docs/wiki/AI-agents.md) | For the agent: how an AI tool should read, run and change this repo safely |
| [Scans index](scans/INDEX.md) | The raw scans (not stored here): where they are, size, triangle count, hash |

## Toolkit files

- `setup.sh`: one-step, re-runnable installer (`--python`, `--full`, `--check`).
- `sim-tools/env.sh`: load the tools in a new terminal.
- `tools/`: `features.py` (hole/fitment check), `quick_fea.py` (strength check), `views.py` (6-view sheet), `viewer.py` (HTML 3D viewer).
- `examples/bracket/`: the worked example.
- `requirements.txt` / `requirements-sim.txt`: pinned Python packages.

## Related repo

- **Fairsolid** (scan cleanup and measuring helper) is a separate repo: <https://github.com/living-relation/fairsolid>. It is linked, not merged. Version last used with this repo: `bbc57143a6d83980548e497ca624567174f7d17d` (2026-10-09). See [Interactions](docs/wiki/Interactions.md).

## Not in this repo

Raw scans (private and too big; see [scans/INDEX.md](scans/INDEX.md)), STEP files over 50 MB (the cast knuckle v3/v4/v4b STEPs, about 250 MB each; the STL and the build script are here, so the STEP can be rebuilt), solver run output (meshes, `.frd`, `.vtu`), the Python venvs, and the FreeCAD install.

## Where the working copy lives

- WSL Ubuntu: `~/projects/handbuilt-models` (the real working copy, branch `main`).
- From Windows: `\\wsl.localhost\<distro>\home\<user>\projects\handbuilt-models`; a shortcut in the Windows projects folder.

All designs are shared for reference. They are hand-built approximations of scanned parts; check every dimension and do your own engineering before machining or fitting anything to a car.
