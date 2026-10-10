# How to use it (ELI5)

[← Home](../../README.md) · back: [Setup](Setup.md)

The idea: **measure the real thing → write down the sizes as numbers → a short script draws the part → check it → send the STEP to CAM.** Change a number, run again, and you get a new part.

Before anything, in the repo folder:

```bash
source sim-tools/env.sh
```

## The everyday steps

| Step | What you do | Tool |
|---|---|---|
| 1. Scan | Scan the part (any 3D scanner), export a mesh (`.ply`/`.stl`/`.obj`). Keep scans **outside** the repo. | your scanner app |
| 2. Measure | Load the mesh in Python and measure holes, faces and distances. Round to real sizes (6.6 mm not 6.58). Keep the scan's true scale: only move/rotate, never stretch. Optional helper: [Fairsolid](https://github.com/living-relation/fairsolid) cleans scans and finds a coordinate frame. | `.venv/bin/python` + trimesh |
| 3. Hand-build | Copy `examples/bracket/bracket.py` into a new folder and change it. All sizes are named numbers at the top. | build123d |
| 4. Export | The script writes `part.step` (for Fusion/CAM) and `part.stl` (for pictures/printing). | build123d |
| 5. Fitment check | Write where the holes must be in `spec.json`, then check. | `tools/features.py` |
| 6. Strength check | Hold one side, push another, read the safety factor. | `tools/quick_fea.py` (Gmsh + CalculiX) |
| 7. Pictures | 6-view sheet (PNG) and a spin-around viewer (HTML for any browser). | `tools/views.py`, `tools/viewer.py` |
| 8. Machining notes | Write stock size, setups, tools, tolerances in `MACHINING.md` next to the part. | a text file |

## Worked example: the sample L-bracket

Run everything at once:

```bash
bash examples/bracket/run_all.sh
```

Or step by step, so you see what each piece does:

```bash
cd examples/bracket
../../.venv/bin/python bracket.py
```
You should see: `bracket: volume 2x.xx cm3, mass ~6x g (aluminium); wrote bracket.step, bracket.stl`

```bash
../../.venv/bin/python ../../tools/features.py bracket.step --spec spec.json
```
You should see the holes listed, then `PASS` for each line in `spec.json` and `ALL PASS`. (If a hole moved, you get `FAIL` and the command exits with an error, which is handy in scripts.)

```bash
$SIM_VENV/bin/python ../../tools/quick_fea.py bracket.step --fix z:min --load z:max --force 500,0,0 --yield 276
```
This holds the bottom of the base still (`z:min`), pushes the top of the upright sideways with 500 N (`z:max`, force X=500), and uses 6061-T6 aluminium (yield 276 MPa). You should see something like
`peak stress ~60 MPa -> safety factor ~4 vs yield 276 MPa`. Results are in `bracket_fea/` (`summary.json`, and `result.vtu` to open in ParaView).

```bash
../../.venv/bin/python ../../tools/views.py bracket.stl
../../.venv/bin/python ../../tools/viewer.py bracket.stl -o bracket_viewer.html
```
You get `bracket_views.png` (front/back/left/right/top/bottom/iso with the size and volume) and `bracket_viewer.html` (open it in a browser to spin it).

**Now change it:** open `bracket.py`, set `THICK = 8.0`, and run `bash run_all.sh` again. The bracket is thicker, the hole check still passes, and the safety factor goes up.

## Make your own part

```bash
mkdir -p parts/my_part && cp examples/bracket/{bracket.py,spec.json,run_all.sh} parts/my_part/
```
Rename things, change the shape and sizes, and update `spec.json` with the holes that must line up with the mating parts. The `parts/` folder is ignored by git, so your own designs stay on your computer unless you choose to share them.

## Tool cheat-sheet

| Command | What it does |
|---|---|
| `.venv/bin/python tools/features.py part.step [--spec spec.json]` | Lists round holes/bosses (diameter, axis, position) and checks them against a spec |
| `$SIM_VENV/bin/python tools/quick_fea.py part.step --fix AX:min --load AX:max --force X,Y,Z [--E --nu --yield --size]` | Quick linear strength check. Units: mm, N, MPa |
| `.venv/bin/python tools/views.py part.stl\|part.step [-o sheet.png]` | 6-view + iso picture sheet |
| `.venv/bin/python tools/viewer.py part.stl [more.stl] -o view.html` | Interactive 3D viewer in one HTML file |
| `bash setup.sh --check` | What's installed |

Units everywhere: **millimetres, newtons, MPa, degrees, kilograms**.

## Common problems

| You see | Do this |
|---|---|
| `ModuleNotFoundError: build123d` | Use `.venv/bin/python`, not plain `python`. |
| `ModuleNotFoundError: gmsh` | Use `$SIM_VENV/bin/python` for `quick_fea.py` (run `source sim-tools/env.sh` first). |
| `no nodes found for x:max` | No mesh nodes sit exactly on that plane (e.g. a rounded end). Pick a flat face, or add `--tol 0.5`. |
| Safety factor looks crazy high/low | Check the force direction and units (N), and that `--fix` is a big flat face. A quick check is not a full analysis. |
| build123d `fillet` error | The radius is too big for that edge. Make it smaller, or fillet before cutting holes. |
| STEP opens in Fusion as a mesh | You opened the `.stl`. Open the `.step`. |

## For AI assistants

If you're an AI helping someone with this repo:

1. Read `README.md`, this page, and [Conventions](Conventions.md). Run `bash setup.sh --check` before anything else.
2. New parts go in a new folder (for example `parts/<name>/`), copied from `examples/bracket/`. Keep every size as a named number at the top.
3. After every change: rebuild, run `tools/features.py --spec`, then `tools/quick_fea.py` for anything that carries load. Report the numbers (mass, PASS/FAIL, safety factor), not just "done".
4. Never scale scan data, never commit scans, secrets or big solver output, and never force-push. Keep personal part designs out of the public repo unless the owner says to share them.
5. Use `.venv/bin/python` for CAD, `$SIM_VENV/bin/python` for meshing/FEA, and run heavy simulations in `~/sim-runs/`, not on `/mnt/c`.
More detail: [For AI agents](AI-agents.md).
