---
name: quick-fea
description: >-
  Use for a first strength check of a single STEP part (one linear static
  load case with Gmsh + CalculiX, tools/quick_fea.py) after the user has
  approved the geometry. Runs on the user's machine.
---
> Draft by Grok Bot (17/10/26). Owner: SteveCAD, who will refine it. Changes go through a PR he reviews.

The project's own rules win over this skill wherever they differ.

## When
- Only after the user approves the geometry (cnc-part-check passed), unless they ask for early tests to check the overall design or find risks.
- It is a first check, not a certification. Real parts need proper load cases and a safety margin agreed with the user. Never assume a safety factor; ask once per job and save it in SUMMARY.md.

## Where it runs
WSL or Linux on the user's machine, with the sim venv (`source sim/wsl-env.sh` or `sim/env.sh`; `$SIM_VENV`, default `~/simvenv`) and `ccx` installed (`bash setup.sh`). Shared venvs are read-only for agents.

## Use
```bash
$SIM_VENV/bin/python tools/quick_fea.py part.step --fix x:min --load x:max --force 0,0,-500 \
    --E 69000 --nu 0.33 --yield 276 --size 2
```
- `--fix` / `--load`: `AXIS:min`, `AXIS:max` or `AXIS:VALUE` (nodes within `--tol` mm of that plane).
- `--force`: total newtons X,Y,Z, spread over the load nodes. Material defaults are 6061-T6; always pass the real material.
- Output: `<part>_fea/` (deck, results, `summary.json`, `result.vtu`). Move it to the job's working folder; never commit it.

## Report
Load case, fixed and loaded faces, material, mesh size, peak stress, safety factor and max displacement. Check that the peak isn't a mesh artefact at a sharp corner or load node (refine `--size` and re-run). Show a ParaView or smooth render of the result.
