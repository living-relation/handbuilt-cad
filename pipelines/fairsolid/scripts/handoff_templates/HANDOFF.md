# Fairsolid CAD handoff (for Grok Bot)

Written 2026-10-15 for Grok Bot. You have no access to our chats or tools, so everything you need is in
this zip. Read this file first, then `RULES.md`, then `TASK-TEMPLATE.md` (Dan fills one in per job).
`MANIFEST.md` lists every file.

## 1. What Fairsolid is

Fairsolid is a private helper tool, not a product. It turns Dan's 3D scans (STL / OBJ / PLY / XYZ) into
clean groundwork for CAD:

- **Cleanup and scale check**: load, repair, smooth away scan texture, confirm the size is true.
  It never rescales. If a size check fails it stops and you report it.
- **Frame**: finds the part's main directions and origin so measurements come out square.
- **Measuring**: fits flats, holes, rounds, fillets, posts and blends, measures scan noise, snaps sizes.
- **Reference-scan surfaces**: for scans of a space (not a part), makes smooth open B-spline surfaces and
  datums as STEP to design against.

Fairsolid alone does NOT make the finished machined-looking solid. **You build the final parts yourself as
parametric build123d scripts**, using Fairsolid's numbers and the scan frame. The worked example
(`worked-example/fuel_hanger_billet_1014/rev7/`) is exactly that: `hanger_billet.py`.

Goals: final models look like perfect machined parts (straight flats, true rounds, clean sizes), scan
texture is never carried into a model, and scan scale is locked.

## 2. Install and run

You need TWO Python environments. They are kept apart on purpose (different OCC builds).

| Env | For | Python | Lock file |
|---|---|---|---|
| `.venv` (Fairsolid) | scan pipeline, tests | **3.13** (pyproject: `>=3.13`; built and tested on 3.13.12) | `env/requirements-fairsolid-lock.txt` |
| `.venv-cad` (build123d) | model scripts, STEP checks, 2D renders | **3.13** | `env/requirements-build123d-lock.txt` (build123d 0.13.0) |

Tested on Windows 11. **Unzip to a SHORT folder such as `C:\work\`**: in a deep folder the build123d install
works but `import build123d` fails with "DLL load failed ... The filename or extension is too long".
Commands are PowerShell; `uv` (https://docs.astral.sh/uv/) is used because it makes
the venvs fast. Plain `python -m venv` + `pip install` also works.

```powershell
# from the folder you unzipped into
cd fairsolid
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe -e ".[test]"
.venv\Scripts\fairsolid.exe --help          # should list prepare, choose, run, fit, refscan, review, status

cd ..
uv venv --python 3.13 .venv-cad
uv pip install --python .venv-cad\Scripts\python.exe -r env\requirements-build123d-lock.txt
.venv-cad\Scripts\python.exe -c "import build123d; print(build123d.__version__)"   # 0.13.0
```

(`-e ".[test]"` installs from `fairsolid\pyproject.toml`: numpy, scipy, trimesh, pymeshlab, cadquery,
pyransac3d, typer, rich, jinja2, networkx, manifold3d, shapely, fast-simplification, rtree 1.4.1, pytest 9.1.1.
If you want the exact versions Dan's machine used, add
`-r ..\env\requirements-fairsolid-lock.txt` instead of relying on the loose ranges.)

Rules for running (also in `RULES.md`): always use the venv; never install into the system Python; do not
set `PYTHONIOENCODING`; each scan goes in a NEW folder under `runs\`.

### Scan commands (run from the `fairsolid` folder)

```powershell
# closed part (a thing you can hold)
.venv\Scripts\fairsolid.exe prepare SCAN.stl --run runs\X          # clean, frame, orientation previews
# look at runs\X\20_previews\*.png, pick the right orientation N
.venv\Scripts\fairsolid.exe choose N --run runs\X
.venv\Scripts\fairsolid.exe fit --run runs\X --units metric        # or inch; only picks the hole-size table
# unattended alternative:
.venv\Scripts\fairsolid.exe run SCAN.stl --run runs\X

# open space (reference scan, e.g. an engine bay)
.venv\Scripts\fairsolid.exe prepare SCAN.stl --run runs\X
.venv\Scripts\fairsolid.exe refscan --run runs\X [--knit] [--patch-box x0,y0,z0,x1,y1,z1] [--no-tidy] [--cell MM]

.venv\Scripts\fairsolid.exe status --run runs\X                    # what the run holds now
.venv\Scripts\fairsolid.exe review --run runs\X                    # pictures of result vs scan
```

Large scans (1 to 3 million faces) take minutes: run them in the background and check back.
Note: `prepare` / `run` are the real command names (`prepare-cmd` / `run-cmd` are aliases).

## 3. How a run is structured

**Fairsolid scan runs** live in `runs\<name>\` (not committed to git). A run folder holds numbered stage
outputs: `00_scan.*` (input) -> `10_clean.ply` -> `15_ideal.ply` -> `20_frame.json` + `20_previews\` ->
`30_*` (areas, fit, report) -> `40_*` (reference surfaces / programs) -> `50_part.step` -> `80_part_faceted.step`
(fallback faceted solid), plus `review\` and `state.json`. Hand over the STEP named `"primary"` in
`state.json` for parts; for reference scans hand over `40_ref_surfaces.step` and `40_ref_datums.step`.
Stages: `s00_ingest`, `s10_sanitize`, `s15_idealize`, `s20_frame`, `s30_fit`, `s40_refscan`,
`s50_reconstruct`, `s70_deviate`, `s75_review`, `s80_export` (in `fairsolid\src\fairsolid\stages\`).

**CAD jobs** (what you will mostly do) live in `runs\<job>_<MMDD>\` and are versioned by folder:

```
runs\<job>\
    scan_canon.ply            scan in its canonical frame (only rotated / moved, never scaled)
    rev2\ rev3\ ... revN\     one folder per revision; NEVER edit an old one, make revN+1
        <job>.py              the build123d script: named numbers at the top, one build, exports
        <part>.step / .stl    one file per part, plus the assembly
        <job>_report.json     mass, clearances, per-part facts written by the script
        SUMMARY.md            what changed vs the last rev, Dan's answers, checks, open items
        2d_bottom_view.png  2d_trimetric.png  (+ any other 2D drawings)
        rebuild.sh / checks.sh / build.log
```

The script's header comment records the history, the measured interfaces kept from the scan, and what
changed. `runs\fuel_hanger_billet_1014\` is the example. The newest revision is `rev7`; `rev2`..`rev6` are
not in this zip (superseded).

## 4. Build a part (the worked example, verified)

```powershell
cd worked-example\fuel_hanger_billet_1014\rev7
..\..\..\.venv-cad\Scripts\python.exe hanger_billet.py > build.log 2>&1
```

Takes about 1.5 minutes. Expected last lines: `"billet_mass_g": 511.0`. `build.log` starts with
`edge breaks: 16 edges done, 8 failed` (known and harmless: 8 optional edge breaks the kernel refuses, the same
in Dan's copy) and `note: foot came out as 1 pieces` (means one piece, fine). It writes `hanger_*.step`,
`hanger_*.stl` for every part and `hanger_report.json`. Output must match the copies already in the folder.

How to write a new one: copy `hanger_billet.py`, change the named constants at the top (interfaces first),
rebuild, check, render. Keep numbers named; keep every part its own solid; export each part to STEP and STL.

## 5. Render the 2D pictures (bottom + trimetric)

Dan gets **2D renders: a bottom view and a trimetric view** (PNG), not CAD files to open.

Generic helper (any STEP / STL, same camera for every model):

```powershell
.venv-cad\Scripts\python.exe tools\render_views.py part1.step part2.step --out path\to\revN --name "Short title"
# writes 2d_bottom_view.png and 2d_trimetric.png; each file gets its own grey / colour shade
# options: --bottom-dir X,Y,Z  --up X,Y,Z  --tri-dir X,Y,Z  (if the part's axes differ)
```

(about 1 minute for a few parts). Check the picture yourself: right way up, nothing missing, whole part in frame.
Re-render whenever the model changes.

Hanger example, hand-tuned drawings (dimensioned top view, sections, side view, OEM-scan overlay, bottom,
trimetric): from the rev folder, with `scan_canon.ply` one folder up:

```powershell
..\..\..\.venv-cad\Scripts\python.exe dump_geom.py       # model numbers -> drawing_geom.json
..\..\..\.venv-cad\Scripts\python.exe renders_2d.py      # 2d_*.png (6 pictures)
..\..\..\.venv-cad\Scripts\python.exe port_drawing.py    # top_plate_ports.pdf / .png
```

Fairsolid's own "grey scan above, shaded result below" picture (use it when showing a scan result):
`render_pair` in `fairsolid\src\fairsolid\stages\s40_refscan.py` (see `worked-example\...\rev7\render.py`; its
paths assume it is run from a folder that has `runs\fuel_hanger_billet_1014\rev7`). For a part result: tessellate the
STEP with cadquery, move `10_clean.ply` into the part frame (`Frame.load("20_frame.json").to_canonical`), and
draw both with `render_pair`. No heat maps or coloured-deviation images.

`reference\st185-render_trimetric.py` is the ST185 repo's headless trimetric renderer (OCP + VTK; it expects
Dan's WSL setup, so use `tools\render_views.py` instead unless you have VTK). It is there to show the camera
and style Dan's other models use.

## 6. Export STEP / STL

In a build123d script (from `hanger_billet.py`):

```python
from build123d import export_step, export_stl
export_step(part, "hanger_top_plate.step")                       # exact geometry, what Dan builds from
export_stl(part, "hanger_top_plate.stl", tolerance=0.02, angular_tolerance=0.2)   # mesh, for printing / viewing
```

- One file per part, plus one assembly file. Name them so the path tells what it is.
- STL tolerance 0.02 mm / 0.2 rad is what the worked example uses; looser (0.05 / 0.3) is fine for the
  big "with fittings" display mesh.
- Units are millimetres. Never scale.
- Fairsolid's own fits (CadQuery): see `fairsolid\recipes\cadquery.md` (verified commands, including the
  teardown crash and the `to_planar` frame trap) and `meshlab.md`.

## 7. Verify before you hand anything back

1. **Each part is one valid solid:**
   `.venv-cad\Scripts\python.exe tools\check_step.py hanger_top_plate.step hanger_foot.step ...`
   (`OK` = 1 solid, valid; `BAD` = floating pieces or invalid. An assembly file shows several solids, that is fine;
   check the part files.)
2. **Clearances and fit:** overlaps and minimum gaps between parts (the example script writes them to
   `hanger_report.json`: `overlap_mm3` must be 0.0 unless the summary explains it; `min_gap_mm` as designed).
3. **Rule gates from `RULES.md`:** 3 mm live-to-live, crimp-sized holes, bend radius, PA12 wall / cavity rules,
   2x weight load stress table, sealing faces. Show each as a small table in `SUMMARY.md`.
4. **Manufacturing check:** the example used `handbuilt-models\tools\cnc_check.py` (sharp inside corners,
   thin walls, flat-end-mill floors). That script is NOT in this zip (it lives in Dan's WSL project); its
   results for rev 7 are in `cnc_*.txt` / `cnc_*.json`. Without it, check minimum wall by hand and list it.
5. **Pictures:** `2d_bottom_view.png` and `2d_trimetric.png` exist, are current and look right.
6. **Lists:** every part has its true file path and a trimetric; every buyable part has a real part number
   and live link (`RULES.md` rules 1 and 3).
7. **Fairsolid itself** (only if you changed its code): from `fairsolid\`,
   `.venv\Scripts\python.exe tests\make_fixture.py` once (makes the test scan in `tests\data\`; use the venv's
   Python, it needs cadquery), then `.venv\Scripts\python.exe -m pytest -q` (Fairsolid's AGENTS.md says about 8 minutes; in a fresh unzipped copy on
   Dan's machine it had NOT finished after 17 minutes when we stopped it, so run the test files for the stage you
   changed rather than the whole suite). Fast example, about
   25 seconds: `.venv\Scripts\python.exe -m pytest tests\test_flat_check.py tests\test_round_check.py tests\test_pass_check.py -q`.
   KNOWN: tests that read `work\clean.ply` (for example `tests\test_primitives.py`) need a leftover file from an older
   run layout that is not in git, so they error in a fresh copy. That is not a code failure.

## 8. Hand-back checklist (what Dan expects)

- New folder `revN` (or new job folder), nothing earlier touched.
- Script, per-part STEP + STL, report JSON, `SUMMARY.md`, the 2D PNGs.
- `SUMMARY.md` states: what Dan asked, what you built, which of Dan's rules applied and how each was met
  (with numbers), open questions as multiple choice (A / B / C, recommendation marked), the true file paths.
- Plain words, short, no jargon. Lead with the answer.

## 9. Other jobs in the original `runs\` (not included, listed so you know they exist)

All are Fairsolid scan runs on Dan's PC under `C:\projects\_archive\2026-10-17-fairsolid\fairsolid\runs\` (moved there 2026-10-17). Each is 90 to 190 MB of scan
and stage files, so they are not in this zip. Ask Dan if you need one.

| Run | What it is |
|---|---|
| `knuckle`, `knuckle_1009` | Rear knuckle scan, 3M faces. Closed part. Hand-built model attempts were v2 (best fit, median 0.55 mm) and v4 (one valid solid). |
| `bezel_1009` | Bezel scan (about 1M faces). Closed part. |
| `dash_housing`, `dash_housing_1009` | Dash housing scan (131k faces). Closed part. |
| `pedal_adapter` | Subaru pedal adapter. Done (hand-built parametric part). |
| `pump_hanger_1009` | OEM fuel pump hanger scan; its canonical frame is `scan_canon.ply` of the worked example. |
| `fuel_pump`, `fuel_pump_1009` | Fuel pump scan. |
| `oil_catch`, `celica_catch_1009` | Reference scans (open space, `refscan`): the Audi oil catch bracket, and the engine bay around the catch can. |
| `scan0608_1009`, `current`, `diag` | Trial and diagnostic runs. |

## 10. Pitfalls we hit

- Booleans on spline-heavy solids get slow or produce invalid / split solids. Prefer plain geometry (planes,
  cylinders, simple fillets). Check solid count after every join.
- Never trust a "success" message alone: run `check_step.py` and look at the picture.
- `rebuild.sh`, `checks.sh`, `views.sh` in the example folder were written for Dan's WSL; the commands inside show
  the order (build, cnc_check, views) but the paths do not apply on your machine.
- No Fusion. No throwaway files at the `C:\projects` root.

## 11. Skipped on purpose (unclear or not available when this zip was made)

- Knuckle, bezel and dash_housing run folders: too big (listed in section 9). No recipes for them are included.
- Earlier hanger revisions (rev2 to rev6): superseded by rev7.
- `cnc_check.py` and `views.py` (handbuilt-models, Dan's WSL project): not reachable when the zip was made. Their rev 7 output is included.
- A full Fairsolid test-suite result: it did not finish in our check (section 7).
- Dan's rules with no written source in the repos (one solid, new version not overwrite, 2x weight load, 2D-render output): written in `RULES.md` from his handoff request; confirm with him if unsure.
- Fusion files, ST185 harness / wiring / CAN rules, and the other ST185 CAD models: not needed for Fairsolid jobs.
- `scripts\batch_eval.py` from the source repo: it holds paths into the user profile.
