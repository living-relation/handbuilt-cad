# How to use it (for the agent)

[← Home](../../README.md) · back: [Setup](Setup.md)

> **For the agent.** You (the person) don't need to run anything on this page. Your AI agent reads it and runs the commands. Your part is the 3 steps on the [home page](../../README.md#start-here-you-dont-run-any-of-this-yourself).

**What to tell your agent** (copy, then change the details):

> Use the handbuilt-cad repo in `~/handbuilt-cad` (start with `README.md` and `docs/wiki/AI-agents.md`). Here's a scan of my bracket: `~/scans/bracket.stl`. Make a clean STEP I can machine from 6061, keep the holes where they are on the scan, run the fit, CNC and strength checks, and show me the 6-view sheet before you call it done.

Or start from an idea instead of a scan:

> Using handbuilt-cad, design a 90° -10 AN adapter pipe, no longer than 53 mm, with a smooth bore. Show me the 6-view sheet and the checks.

The idea: **measure the real thing → write down the sizes as numbers → a short script draws the part → check it → send the STEP to CAM.** Change a number, run again, and you get a new part.

Before anything, in the repo folder:

```bash
source sim/env.sh
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
{"tool_radii_mm": [3.0, 5.0, 6.0], "lip_max_mm": 0.1, "min_wall_mm": 1.5, "spindle_axis": "z", "wall_samples": 20000,
 "reach_samples": 20000, "reach_min_gain_pct": 0.25, "ray_chunk": 1000, "mesh_tol_mm": 0.02, "max_listed": 25}
```
1.5 mm is an aluminium rule of thumb; use more for parts that carry load. Add `--strict` to make it exit with an error when anything is flagged (handy in scripts), and `--out PREFIX` to put the report somewhere else. Round holes (half a circle or more) count as drilled or bored, so they aren't reported as corners.

**Lips.** A concave edge next to a face narrower than `lip_max_mm` (0.1 mm), where the faces on both sides of that sliver are within 15 deg of tangent, is a **lip**: a tiny step, not a corner (a `tools/blend.py` blend leaves a 0.015 mm step along each edge of the blend, one per lofted strip, which used to add hundreds of "sharp corners"). Lips are counted on their own line under item 2 and listed under `lips` in the JSON; they don't make the check fail. A sliver face inside a real corner (the faces either side turn more than 15 deg, e.g. a failed tiny fillet or a boolean seam) is still reported as a sharp corner, marked "split by a sliver face". Set `"lip_max_mm": 0` to count every concave edge as before.

Two extra options for big or curved parts:
- `--reach` adds **5. Reach**. It shoots rays from points all over the surface toward the 6 axis directions, the setup directions from item 1 and the main hole axes. It reports the fewest directions that together see everything reachable, how much each one adds, and what % of the surface no direction can see, with locations. Give your own plan instead with `--reach "+Z,-Z,+X,0.97/0/-0.24"` (axis names or x/y/z vectors). It is line of sight only: it doesn't know cutter length, holder or radius. Treat it as "at least this hard", not as a CAM plan.
- `--stl part.stl` runs the wall scan and reach on a mesh you already have (same part, same units and position; a warning is printed if the box doesn't match). Without it the STEP is meshed. If OCC can't mesh some faces, they are meshed one by one, then retried coarser, and any that still fail are skipped and counted in the report (never a crash).

The report ends with the run time and peak memory. On a large part (330 mm knuckle) lower `wall_samples` / `reach_samples` or `ray_chunk` if memory is tight.

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
You should see a JSON line (length, major diameter, volume, `"solids": 1, "valid": true`) and `PASS: one valid solid`. Sizes in the table: `-10` (7/8-14 UNF-2A) and `-6` (9/16-18 UNF-2A). In your own part script, `from an_fitting import AN, male_an_leg` gives the outer solid only (`leg, L = male_an_leg(AN[10], lead=0.5)`, nose face at `+Z = L`), so fuse it to your body first and cut one bore through everything. Every flare-end number (nose-to-shoulder J, nose D, cone major C, 37°, nose-to-chamfer B, relief F × Q, root radius, bore A) comes from the `STD` table at the top of `an_fitting.py` (MS33656 / AS4395 / ISO 8434-2, with the source next to each value), and the threads from ASME B1.1 UNF-2A. The standard bore A is `AN[size]["bore_d"]` (12.29 for `-10`, 7.54 for `-6`); don't bore a male end bigger than that, or the nose face gets paper thin. After any change to the file, run the self-check:
```bash
../../.venv/bin/python ../../tools/an_fitting.py --selfcheck
```
It builds a `-6` and a `-10`, measures the meshes (not the parameters) and prints each dimension against its standard range. You should see `SELFCHECK PASS`; any `FAIL` row exits 1.

**Blending where `fillet()` fails (for the agent).** Kernel fillets often fail where a lofted arm meets a plate. Don't sweep a circle along the junction by hand (those tubes come out invalid, or "valid" with a few % of the volume they should have). Use `tools/blend.py`: it finds the crease where the two solids meet, places a rolling ball of radius r on each section, lofts the fillet cross-sections, fuses them and checks the result. Try the demo first:
```
../../.venv/bin/python ../../tools/blend.py demo --angle 45 --r 6 -o runs/tilt45
```
You should see `fused: valid True, solids 1, added ... vs expected ... -> PASS` and a JSON line with `"ok": true`; the part and report go to `runs/tilt45.step` / `.json` (`runs/` is git-ignored, so nothing shows up in `git status`). In your own script use `from blend import blend, fuse_blend`, then `res = blend(arm, plate, 6.0)` and `part, rep = fuse_blend(arm + plate, res, "part.step")`. Check `rep["ok"]` (valid, one solid, STEP re-import, and the volume check: the part must gain the expected fillet volume within 10 %) and read `res.notes`. A note about **sharp corners** in the crease means one body has a sharp edge or a flat end cap poking out through the other; the blend stops on each side of that corner, so fix the geometry if the corner shows. For two STEP files: `tools/blend.py pair arm.step plate.step --r 6 -o out`. It needs `shapely` (`uv pip install shapely` into the build venv).

**Blend quality and skipped sections.** Section spacing is adaptive by default: blend() puts sections close together where the root curves or twists (until each ruled strip is within `chord_tol=0.005` mm of the true rolling-ball surface) and far apart where it is straight, so curved roots no longer show flat "teeth". `adaptive=False` gives the old uniform spacing; `loft="auto"` tries a smooth B-spline loft and falls back to the ruled one (ruled stays the default: the smooth loft overshoots at the seam of closed loops). Where the crease crosses a small round or edge, a section that cannot be built is retried slightly moved and then with a smaller radius; what still fails, or would fold over its neighbour (a concave round smaller than r), is skipped. Skips are never silent: they print a `WARNING loop ...` line with how many and where (u and x, y, z), are listed in `res.skipped` and `rep["skipped"]` / `rep["skipped_sections"]`, and a gap wider than 3 x step splits the blend there (no blend in that gap). Check `rep["single_valid_solid"]` and `rep["volume_check"]` as before. Tests, from the repo root: `.venv/bin/python -m pytest -q tests/test_blend.py` (pytest comes with `setup.sh`) (straight root, boss on a cylinder, root across r1 rounds; about 3 min).

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
| `.venv/bin/python tools/cnc_check.py part.step [--spec cnc_spec.json] [--strict] [--out PREFIX] [--stl part.stl] [--reach [DIRS]]` | CNC screen: setup directions, sharp or too-small inside corners (tiny blend run-out steps counted separately as lips), vertical corners, thin walls; `--reach` = line-of-sight surface coverage and fewest directions. Writes `_cnc.txt` + `_cnc.json` |
| `$SIM_VENV/bin/python tools/quick_fea.py part.step --fix AX:min --load AX:max --force X,Y,Z [--E --nu --yield --size]` | Quick linear strength check. Units: mm, N, MPa |
| `.venv/bin/python tools/views.py part.stl\|part.step [-o sheet.png] [--six] [--name NAME]` | 6-view + iso picture sheet; `--six` = only the 6 labelled plain-grey views |
| `.venv/bin/python tools/viewer.py part.stl [more.stl] -o view.html` | Interactive 3D viewer in one HTML file |
| `.venv/bin/python tools/an_fitting.py --size 10\|6 [-o end.step] [--stl] [--no-bore] [--lead MM]` | Male AN / JIC 37° flare fitting end with a real UNF thread; checks it's one valid solid (exit 1 if not) |
| `.venv/bin/python tools/an_fitting.py --selfcheck [--json rows.json]` | Measures built `-6` and `-10` ends against MS33656 / AS4395 / ISO 8434-2 and UNF-2A; exit 1 on any miss |
| `.venv/bin/python tools/blend.py pair A.step B.step --r 6 [--base body.step] [-o OUT] [--path crease.step]` | Rolling-ball blend (fillet) between two solids where `fillet()` fails; fuses it and checks valid, one solid, STEP re-import and fillet volume (the gain is measured locally as pieces minus base, never as the difference of two big part volumes; exit 1 on a miss). `demo --angle 45` and `compare` show it on a tilted cylinder |
| `.venv/bin/python tools/chamfer_batch.py in.step out.step [--size 0.8] [--min-angle 25] [--time 600]` | Edge-break chamfer on every sharp convex edge where fillets fail: all at once, then halves, then one by one; an edge that will not chamfer is skipped and listed (`WARNING` lines, `out.step.chamfer.json`) |
| `from sketch_blend import capsule, round_outline, plan_union, poly_face, prism, skirt, strict_fuse, strict_cut, round_edges` | Helpers for clean CNC sketch bodies: true line + arc outlines, rounded plan outlines, concave blend skirts, and joins / cuts / edge rounds that fail loudly instead of silently skipping (tests: `tests/test_sketch_tools.py`) |
| `bash setup.sh --check` | What's installed |

Units everywhere: **millimetres, newtons, MPa, degrees, kilograms**.

## Common problems

| You see | Do this |
|---|---|
| `ModuleNotFoundError: build123d` | Use `.venv/bin/python`, not plain `python`. |
| `ModuleNotFoundError: gmsh` | Use `$SIM_VENV/bin/python` for `quick_fea.py` (run `source sim/env.sh` first). |
| `no nodes found for x:max` | No mesh nodes sit exactly on that plane (e.g. a rounded end). Pick a flat face, or add `--tol 0.5`. |
| Safety factor looks crazy high/low | Check the force direction and units (N), and that `--fix` is a big flat face. A quick check is not a full analysis. |
| build123d `fillet` error | The radius is too big for that edge. Make it smaller, or fillet before cutting holes. |
| `fillet` fails where a loft meets a plate | Use `tools/blend.py` (rolling-ball blend solid, fused and volume-checked) instead of sweeping a circle yourself. |
| STEP opens in Fusion as a mesh | You opened the `.stl`. Open the `.step`. |

## For AI assistants

If you're an AI helping someone with this repo:

1. Read `README.md`, this page, and [Conventions](Conventions.md). Run `bash setup.sh --check` before anything else.
2. New parts go in a new folder (for example `parts/<name>/`), copied from `examples/bracket/`. Keep every size as a named number at the top.
3. After every change: rebuild, run `tools/features.py --spec` and `tools/cnc_check.py`, then `tools/quick_fea.py` for anything that carries load. Report the numbers (mass, PASS/FAIL, safety factor), not just "done".
4. Never scale scan data, never commit scans, secrets or big solver output, and never force-push. Keep personal part designs out of the public repo unless the owner says to share them.
5. Use `.venv/bin/python` for CAD, `$SIM_VENV/bin/python` for meshing/FEA, and run heavy simulations in `~/sim-runs/`, not on `/mnt/c`.
More detail: [For AI agents](AI-agents.md).

## Helpers: Fairsolid runs and new revs

- `tools/scan_helper.py` runs [Fairsolid](https://github.com/living-relation/fairsolid) on a scan. It finds Fairsolid **only** through `FAIRSOLID_HOME` (a Fairsolid checkout with its own `.venv`), so nothing in this repo hard-codes where it lives:

  ```bash
  export FAIRSOLID_HOME=~/projects/fairsolid
  .venv/bin/python tools/scan_helper.py check
  .venv/bin/python tools/scan_helper.py prepare ~/scans/bracket.stl --run /tmp/bracket_run
  .venv/bin/python tools/scan_helper.py fit --run /tmp/bracket_run
  ```

  Keep run folders outside the repo.
- `tools/rev.py` makes the next revision folder for a finished part in your models folder, `$MODELS_DIR/<job>_<MMDD>/revN/`, with a `SUMMARY.md` template. It never overwrites an existing rev:

  ```bash
  export MODELS_DIR=~/models
  .venv/bin/python tools/rev.py bracket --source ~/work/bracket
  ```

  Part files (STEP/STL/renders) go there, not into this repo.
