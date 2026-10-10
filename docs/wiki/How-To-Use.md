# How to use it (for the agent)

[← Home](../../README.md) · back: [Setup](Setup.md)

> **For the agent.** You (the person) don't need to run anything on this page. Your AI agent reads it and runs the commands. Your part is the 3 steps on the [home page](../../README.md#start-here-you-dont-run-any-of-this-yourself).

**What to tell your agent** (copy, then change the details):

> Use the handbuilt-models repo in `~/handbuilt-models` (start with `README.md` and `docs/wiki/AI-agents.md`). Here's a scan of my bracket: `~/scans/bracket.stl`. Make a clean STEP I can machine from 6061, keep the holes where they are on the scan, run the fit, CNC and strength checks, and show me the 6-view sheet before you call it done.

Or start from an idea instead of a scan:

> Using handbuilt-models, design a 90° -10 AN adapter pipe, no longer than 53 mm, with a smooth bore. Show me the 6-view sheet and the checks.

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
| 6. CNC check | Can it be milled? Setups, inside corners tighter than your cutters, vertical corners, thin walls. | `tools/cnc_check.py` |
| 7. Strength check | Hold one side, push another, read the safety factor. | `tools/quick_fea.py` (Gmsh + CalculiX) |
| 8. Pictures | 6-view sheet (PNG) and a spin-around viewer (HTML for any browser). | `tools/views.py` (`--six` for the plain 6-view sheet), `tools/viewer.py` |
| 9. Machining notes | Write stock size, setups, tools, tolerances in `MACHINING.md` next to the part. | a text file |

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
../../.venv/bin/python ../../tools/cnc_check.py bracket.step --spec cnc_spec.json
```
This is a quick "can it be milled?" screen. It prints, and saves as `bracket_cnc.txt` + `bracket_cnc.json`:
1. **Setups**: which directions the cutter has to come from (every flat face reachable, every hole on-axis). It's a lower bound, because it doesn't know when one part of the model blocks another.
2. **Inside corners** with no radius (sharp) or a radius smaller than your smallest cutter, with their x, y, z.
3. **Vertical inside corners** a cutter coming straight down can't make (they come out at the tool radius).
4. **Thin walls** under the minimum wall, with locations.

For the bracket you should see 3 directions (bottom, top, and the side for the upright hole), no corners and no thin walls, then `Result: nothing flagged`.
`cnc_spec.json` lists the cutters you have and your minimum wall. Every key is optional; the defaults are:
```json
{"tool_radii_mm": [3.0, 5.0, 6.0], "min_wall_mm": 1.5, "spindle_axis": "z", "wall_samples": 20000, "max_listed": 25}
```
1.5 mm is an aluminium rule of thumb; use more for parts that carry load. Add `--strict` to make it exit with an error when anything is flagged (handy in scripts), and `--out PREFIX` to put the report somewhere else. Round holes (half a circle or more) count as drilled or bored, so they aren't reported as corners.

```bash
$SIM_VENV/bin/python ../../tools/quick_fea.py bracket.step --fix z:min --load z:max --force 500,0,0 --yield 276
```
This holds the bottom of the base still (`z:min`), pushes the top of the upright sideways with 500 N (`z:max`, force X=500), and uses 6061-T6 aluminium (yield 276 MPa). You should see something like
`peak stress ~60 MPa -> safety factor ~4 vs yield 276 MPa`. Results are in `bracket_fea/` (`summary.json`, and `result.vtu` to open in ParaView).

```bash
../../.venv/bin/python ../../tools/views.py bracket.stl --six --name "Sample bracket"
../../.venv/bin/python ../../tools/viewer.py bracket.stl -o bracket_viewer.html
```
You get `bracket_views.png` and `bracket_viewer.html` (open it in a browser to spin it). With `--six` the sheet is just the six labelled views (FRONT, BACK, LEFT, RIGHT, TOP, BOTTOM, each saying which side it looks from) in plain grey, plus the size and volume in the title. `--name` sets the part name on the labels. Leave `--six` off to get the older sheet with a 7th iso (3D) panel.

**Parts with AN fittings (for the agent).** Don't draw AN threads by hand. Build the male end with `tools/an_fitting.py`:
```bash
../../.venv/bin/python ../../tools/an_fitting.py --size 10 -o an10.step --stl
```
You should see a JSON line (length, major diameter, volume, `"solids": 1, "valid": true`) and `PASS: one valid solid`. Sizes in the table: `-10` (7/8-14 UNF-2A) and `-6` (9/16-18 UNF-2A). In your own part script, `from an_fitting import AN, male_an_leg` gives the outer solid only (`leg, L = male_an_leg(AN[10], lead=0.5)`, nose face at `+Z = L`), so fuse it to your body first and cut one bore through everything. The `-6` nose, cone and thread length are scaled from the `-10`, so tell the owner to check them against a real `-6` fitting before machining.

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
| `.venv/bin/python tools/cnc_check.py part.step [--spec cnc_spec.json] [--strict] [--out PREFIX]` | CNC screen: setup directions, sharp or too-small inside corners, vertical corners, thin walls. Writes `_cnc.txt` + `_cnc.json` |
| `$SIM_VENV/bin/python tools/quick_fea.py part.step --fix AX:min --load AX:max --force X,Y,Z [--E --nu --yield --size]` | Quick linear strength check. Units: mm, N, MPa |
| `.venv/bin/python tools/views.py part.stl\|part.step [-o sheet.png] [--six] [--name NAME]` | 6-view + iso picture sheet; `--six` = only the 6 labelled plain-grey views |
| `.venv/bin/python tools/viewer.py part.stl [more.stl] -o view.html` | Interactive 3D viewer in one HTML file |
| `.venv/bin/python tools/an_fitting.py --size 10\|6 [-o end.step] [--stl] [--no-bore] [--lead MM]` | Male AN / JIC 37° flare fitting end with a real UNF thread; checks it's one valid solid (exit 1 if not) |
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
3. After every change: rebuild, run `tools/features.py --spec` and `tools/cnc_check.py`, then `tools/quick_fea.py` for anything that carries load. Report the numbers (mass, PASS/FAIL, safety factor), not just "done".
4. Never scale scan data, never commit scans, secrets or big solver output, and never force-push. Keep personal part designs out of the public repo unless the owner says to share them.
5. Use `.venv/bin/python` for CAD, `$SIM_VENV/bin/python` for meshing/FEA, and run heavy simulations in `~/sim-runs/`, not on `/mnt/c`.
More detail: [For AI agents](AI-agents.md).
