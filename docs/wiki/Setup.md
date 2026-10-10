# Setup: what `setup.sh` installs (for the agent)

[← Home](../../README.md) · back: [Install](Install.md) · next: [How to use](How-To-Use.md)

> **For the agent.** You (the person) don't need to run anything on this page. Your AI agent reads it and runs the commands. Your part is the 3 steps on the [home page](../../README.md#start-here-you-dont-run-any-of-this-yourself).

Think of it as three toolboxes. `setup.sh` checks each one and only adds what's missing, so running it again is safe.

| Toolbox | What it's for | Where it goes | Comes from |
|---|---|---|---|
| **1. Model box** (`.venv`) | Drawing parts with code (build123d), reading scans/meshes (trimesh), maths, pictures | `.venv/` inside the repo | `requirements.txt` |
| **2. Simulation box** (`simvenv`) | Making meshes (gmsh), reading results (meshio), optimisation (nlopt, pypardiso) | `~/simvenv` (change with `SIM_VENV=/somewhere bash setup.sh`) | `requirements-sim.txt` |
| **3. Programs** | **CalculiX** (strength solver), **Gmsh** (mesher), **ParaView** (result viewer), xvfb (lets ParaView make pictures without a screen) | system (`apt`) | Ubuntu packages |

Extras:

- **OpenFOAM** (air/fluid flow) and **Elmer** (heat, multiphysics): only with `bash setup.sh --full`. Elmer is built from source and takes about 15 minutes.
- **FreeCAD** (Windows, optional): a free CAD program with a clickable FEA front end. Download the portable version from freecad.org, unzip it anywhere, and run `FreeCAD.bat` / `bin\freecad.exe`. To make it use the Linux CalculiX, set Edit → Preferences → FEM → CalculiX → binary to the wrapper `sim-tools/ccx_wsl.bat` (copy it next to FreeCAD first).
- **Ollama** (optional local AI helper): install from ollama.com, then `ollama pull qwen2.5-coder:14b`. Nothing in the toolkit needs it.
- **uv**: a fast Python installer that `setup.sh` puts in `~/.local/bin` if missing.

## Options

```bash
bash setup.sh           # boxes 1 + 2 + 3   (normal)
bash setup.sh --python  # boxes 1 + 2 only  (no password, no apt)
bash setup.sh --full    # everything + OpenFOAM + Elmer
bash setup.sh --check   # just tell me what's installed
```

## Check it worked

```bash
bash setup.sh --check
```

Every line should be green `[ok]` (yellow `[skip]` is fine for extras). Then the quick test:

```bash
source sim-tools/env.sh
.venv/bin/python -c "import build123d; print('build123d', build123d.__version__)"
ccx -v | head -2
```

**You should see** `build123d 0.13.0` and `This is Version 2.2x`.

Each time you open a new Ubuntu window, run `source sim-tools/env.sh` inside the repo folder (it loads the simulation box and OpenFOAM if present).

## Problems

| You see | Do this |
|---|---|
| `uv: command not found` after setup | Close and reopen the window, or run `export PATH=$HOME/.local/bin:$PATH`. |
| pip/uv download errors | Internet hiccup: run `bash setup.sh` again. |
| `pypardiso` fails | Only works on normal Intel/AMD (x86_64) PCs; setup skips it on ARM. The quick tools don't need it. |
| ParaView pictures are black/fail | `sudo apt install xvfb`, and use `xvfb-run -a pvpython script.py`. |
| `ZSH_NAME: unbound variable` | You sourced OpenFOAM in a strict shell; use `source sim-tools/env.sh`, which handles it. |

Old helper scripts still work and now just call `setup.sh`: `sim-tools/scripts/setup_venv_wsl.sh` (= `--python`) and `sim-tools/scripts/install_sim_tools_wsl.sh` (= `--full`). Details on the solvers, smoke tests and uninstall: [`sim-tools/SIM_TOOLS.md`](../../sim-tools/SIM_TOOLS.md).
