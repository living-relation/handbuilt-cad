# Layout — where everything goes

> **Part files moved (2026-10-15):** finished part outputs (STEP, STL, PNG renders, notes) are no longer in this repo. They live in the owner's models folder, `$MODELS_DIR/<subject>-rev<current>/rev<LETTER>/` (keep the newest rev and the one before it; filing a new rev deletes the oldest). Each rev has a `SUMMARY.md` and a `src/` copy of its scripts. The assembly STEP sits at the rev root and external parts in `Parts\`. The folders below keep the generation scripts; rebuild a part from its script, or point `MODELS_DIR` at your own models folder.


[← Home](../../README.md)

This is the single CAD repo (tools, drawings, sim; part scripts live in the parts home, `~/cad-parts`). It replaced handbuilt-models (2026-10-17); the old repo's front files are in `docs/history/`.

```
handbuilt-cad/
├── README.md, AGENTS.md, CONTRIBUTING.md   front page, agent rules, PR rules
├── INSTALL.md, SETUP-PROMPT.txt   four install routes; the agent prompt
├── setup.sh / setup.ps1   toolkit setup (builds .venv from uv.lock; does not add the plugin)
├── install.cmd            Windows shortcut for setup.ps1
├── install-plugins.*      open the claude.ai Plugins page and copy the Cursor plugin when you run them
├── pyproject.toml, uv.lock, requirements-sim.txt, apt-sim.txt   pinned packages
├── local.toml.example     per-PC paths (models_dir, freecad_dir, ...); copy to local.toml (git-ignored)
├── docs/                  TOOLS.md (tools index), wiki/ (this wiki), history/ (files kept from the old repos)
├── tools/                 the toolkit: features, cnc_check, quick_fea, views, viewer, an_fitting, blend,
│   │                      sketch_blend, chamfer_batch, rev, scan_helper
│   ├── checks/            model checks: mesh, printed walls, round-trip, interference, edge breaks, hole fixes, release structure
│   └── render/            smooth-shaded renders, section plots
├── drawing/               2D drawing engine (part / assembly sheets, rev letters, rev log, templates)
├── pipelines/fairsolid/   scan -> parametric STEP pipeline
├── sim/                   simulation: env.sh, SIM_TOOLS.md, install / smoke / rollback scripts, FreeCAD wrappers (freecad/)
├── skills/                agent skills; the plugin installs them (CI zips at skills/<name>.zip are not the install path)
├── examples/bracket/      worked example (run_all.sh)
├── templates/parts-home/ owner AGENTS.md that setup.sh puts in the parts home
├── scans/INDEX.md         list of raw scans (scans themselves are not in git)
├── scripts/               repo hooks: guard-staged, gitleaks; pack-skill-zips
└── tests/                 pytest suite (.venv/bin/python -m pytest -q)
```

## Where new work goes

- **New part:** `~/cad-parts/<job>/src/` (parts home, `HBCAD_PARTS_HOME`, outside git; `<job>` is `<name>_<MMDD>`) with `<part>.py` and a short `NOTES.md`. Finished STEP / drawings / review views go to `$MODELS_DIR/<subject>-rev<current>/rev<LETTER>/` (skill `publish-to-models`), never into git. Old versions go to `~/cad-parts/_archive/<job>/`.
- **Working outputs and simulation runs:** `~/cad-parts/<job>/runs/<YYYYMMDD-HHMM>/` (`tools/paths.py run_dir`, `quick_fea.py --job`). Delete regenerable outputs once a run is published or superseded.
- **Docs:** update the [Parts index](Parts.md) and add a dated line to `NOTES.md`.

## What git ignores

Venvs, `__pycache__`, scan point clouds (`*.ply`), STEP/STL over 50 MB (listed by name in `.gitignore`), solver output (`*.frd`, `*.vtu`, `*.12d`, `*.cvg`, `*.sta`, big `.npz` meshes) under the iteration folders, and run folders (`runs/`, `sim-runs/`). Files already committed before these rules stay as they are.

The previous front-page README (with the original rebuild notes) is kept at [Legacy-README.md](Legacy-README.md).
