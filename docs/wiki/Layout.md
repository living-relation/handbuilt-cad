# Layout — where everything goes

> **Part files moved (2026-10-15):** finished part outputs (STEP, STL, PNG renders, notes) are no longer in this repo. They live in the owner's models folder, `$MODELS_DIR/<job>_<MMDD>/revN/`, each rev with a `SUMMARY.md` and a `src/` copy of its scripts. The folders below keep the generation scripts; rebuild a part from its script, or point `MODELS_DIR` at your own models folder.


[← Home](../../README.md)

This is the single CAD repo (tools, drawings, sim, part scripts). It replaced handbuilt-models (2026-10-17); the old repo's front files are in `docs/history/`.

```
handbuilt-cad/
├── README.md, AGENTS.md, CONTRIBUTING.md   front page, agent rules, PR rules
├── setup.sh / setup.ps1   one-step setup (builds .venv from uv.lock; --full adds the sim tools)
├── pyproject.toml, uv.lock, requirements-sim.txt, apt-sim.txt   pinned packages
├── local.toml.example     per-PC paths (models_dir, freecad_dir, ...); copy to local.toml (git-ignored)
├── docs/                  TOOLS.md (tools index), wiki/ (this wiki), history/ (files kept from the old repos)
├── tools/                 the toolkit: features, cnc_check, quick_fea, views, viewer, an_fitting, blend,
│   │                      sketch_blend, chamfer_batch, rev, scan_helper
│   ├── checks/            model checks: mesh, printed walls, round-trip, interference, edge breaks, hole fixes
│   └── render/            smooth-shaded renders, section plots
├── drawing/               2D drawing engine (part / assembly sheets, rev letters, rev log, templates)
├── pipelines/fairsolid/   scan -> parametric STEP pipeline
├── sim/                   simulation: env.sh, SIM_TOOLS.md, install / smoke / rollback scripts, FreeCAD wrappers (freecad/)
├── skills/                agent skills (publish-to-models, cnc-part-check, scan-to-parametric, ...)
├── examples/bracket/      worked example (run_all.sh)
├── parts/                 generation scripts of the hand-built parts (outputs live in $MODELS_DIR)
│   ├── knuckle/           cast rear knuckle, hand-built from the scan (v2 ... v5; v4 approved)
│   ├── knuckle_billet/    billet redesign of the knuckle + FEA / topology tooling
│   ├── bezel/  pedal_adapter/  pcv_adapter/  pcv_an10/  catch_can_refscan/
├── scans/INDEX.md         list of raw scans (scans themselves are not in git)
├── scripts/               repo hooks: guard-staged, gitleaks
└── tests/                 pytest suite (.venv/bin/python -m pytest -q)
```

## Where new work goes

- **New part:** a new folder `parts/<part>/` (`snake_case`) with `<part>.py` and a short `NOTES.md`. The generated STEP / STL / renders go to `$MODELS_DIR/<job>_<MMDD>/revN/` (skill `publish-to-models`), never into git. If it has versions, use `v1/`, `v2/`... like `parts/knuckle/`.
- **Simulation runs:** run in the Linux home (`~/sim-runs/<part>/…`) or a git-ignored folder, then copy only summaries (JSON/CSV/PNG) into the part folder.
- **Docs:** update the [Parts index](Parts.md) and add a dated line to `NOTES.md`.

## What git ignores

Venvs, `__pycache__`, scan point clouds (`*.ply`), STEP/STL over 50 MB (listed by name in `.gitignore`), solver output (`*.frd`, `*.vtu`, `*.12d`, `*.cvg`, `*.sta`, big `.npz` meshes) under the iteration folders, and run folders (`runs/`, `sim-runs/`). Files already committed before these rules stay as they are.

The previous front-page README (with the original rebuild notes) is kept at [Legacy-README.md](Legacy-README.md).
