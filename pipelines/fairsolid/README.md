# Fairsolid

**A private helper tool for Grok Bot. It is not a product, and nobody is meant to run it by hand.**

Grok Bot uses Fairsolid as one step in building clean CAD models from the user's 3D scans. Grok Bot builds the final solid parts itself, as parametric build123d scripts. Fairsolid does the groundwork and makes surfaces for open spaces.

## What Grok Bot uses it for

- **Cleanup and scale check.** Load a scan, repair it, smooth away scan texture, and confirm the size is true. Fairsolid never rescales. If a size check fails, it stops.
- **Frame.** Find the part's main directions and origin, so measurements come out square.
- **Measuring.** Fit flats, holes, rounds, fillets, posts and blends, measure the scan noise, and snap sizes. Grok Bot reads these numbers to write the parametric model.
- **Reference-scan surfaces.** For scans of a space instead of a part (like the engine bay around the catch can), it makes smooth open B-spline surfaces plus datums as STEP to design against.

The automatic fit stage alone does not make a finished machined-looking solid. That job belongs to Grok Bot's hand-built models.

## Goals it serves

- Final models look like perfect machined parts, with straight flats, true rounds and clean sizes. They are not copies of the imperfect scan.
- Scan texture is never carried into a model.
- Scan scale is locked. Units only affect snapping and display.

## Commands (for Grok Bot)

Always run inside the venv. Put each scan in its own new folder under `runs\`.

    .venv\Scripts\fairsolid.exe prepare SCAN --run runs\X
    .venv\Scripts\fairsolid.exe choose N --run runs\X
    .venv\Scripts\fairsolid.exe fit --run runs\X --units metric
    .venv\Scripts\fairsolid.exe refscan --run runs\X [--knit] [--patch-box x0,y0,z0,x1,y1,z1] [--no-tidy]

Tests: `.venv\Scripts\python.exe -m pytest -q` (about 8 minutes). See `AGENTS.md` for working rules.

### Linux / WSL

Fairsolid also runs on Linux and in WSL (Ubuntu). Clone it onto the Linux file system
(for example `~/projects/fairsolid`, not `/mnt/c`) and give it its own Python 3.13 venv with
[uv](https://docs.astral.sh/uv/). It matches the Windows pin, 3.13.12:

    git clone https://github.com/living-relation/fairsolid ~/projects/fairsolid
    cd ~/projects/fairsolid
    uv venv --python 3.13.12 .venv
    uv pip install --python .venv/bin/python -e ".[test]"

Then use the same commands with `.venv/bin/fairsolid` and forward slashes:

    .venv/bin/fairsolid prepare SCAN --run runs/X
    .venv/bin/fairsolid choose N --run runs/X
    .venv/bin/fairsolid fit --run runs/X --units metric

Tests: `.venv/bin/python -m pytest -q`. Tools that call Fairsolid from elsewhere (for example the
handbuilt-models `tools/scan_helper.py`) find it through the `FAIRSOLID_HOME` environment variable,
which should point at this checkout.

## Stages

| Stage | Does |
|---|---|
| `s00_ingest` | load STL/OBJ/PLY/XYZ |
| `s10_sanitize` | repair, smooth, decimate |
| `s15_idealize` | snap vertices onto measured planes and cylinders |
| `s20_frame` | measure primitives, pick orientation and origin |
| `s30_fit` | area map, surface fits, snapping, size check |
| `s40_refscan` | open B-spline surfaces and datums for reference scans |
| `s50_reconstruct` | prismatic rebuild |
| `s70_deviate` | grade against the cleaned scan |
| `s75_review` | pictures of results |
| `s80_export` | faceted fallback solid |

## Docs

- `docs/SURFACE_FIT_PLAN.md` is the design plan and decisions.
- `docs/AI_METHODS_REPORT.md` is history only: the neural scan-to-CAD research. That AI stage was removed.
- `recipes/` has verified commands for the underlying tools.

Fairsolid was formerly named scan2step.