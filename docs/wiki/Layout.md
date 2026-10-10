# Layout — where everything goes

[← Home](../../README.md)

Existing paths are kept exactly as they were, so scripts keep working. New things follow the same pattern.

```
handbuilt-models/
├── README.md              front page of the wiki
├── NOTES.md               running session notes (dated, newest at the bottom)
├── requirements.txt       build venv (.venv) packages, pinned
├── requirements-sim.txt   simulation venv (~/simvenv) packages, pinned
├── docs/wiki/             this wiki
├── scans/INDEX.md         list of raw scans (location, size, triangles, hash) — scans themselves are not in git
├── knuckle/               cast rear knuckle, hand-built from the scan
│   ├── MEASURED.md        measured holes, bores, eyes
│   ├── frame_hb.json      scan → part coordinate frame (rigid, no scale)
│   ├── v2 … v5/           successive builds (knuckle.py + STEP/STL); v4 is the approved one
│   ├── renders*/          model-vs-scan pictures
│   └── feature_check/     the 24 location features every derived design must keep
├── knuckle_billet/        billet (7075) redesign of the knuckle + FEA/topology tooling
│   ├── LOADS.md, loads.py, loads.json   load cases (fast road, slicks, coilovers, solid bushings)
│   ├── PLAN.md, NOTES.md, MACHINING.md
│   ├── knuckle_billet.py  parametric billet builder (params.json drives it)
│   ├── fea_*.py, mesh_*.py, post_*.py, run_iter.sh, run_wsl.sh   FEA pipeline
│   ├── topo_*.py, beso_map.py, topo/                             topology optimisation
│   ├── iter/              iteration outputs (solver files are git-ignored)
│   ├── baseline/          FEA of the original v4 shape
│   ├── stress_renders/    stress plots of the saved versions
│   └── final/             best / middle / full-arm / easy / two-piece — STEP, STL, params, FEA summaries
├── bezel/                 dash bezel (v1–v3)
├── pedal_adapter/         pedal adapter
├── pcv_adapter/           stock PCV pipe (Audi EA888 06H103223A)
├── pcv_an10/              PCV pipe with angled −10 AN male end (35° and 45°)
├── catch_can_refscan/     reference surfaces of the catch-can area (from Fairsolid refscan)
└── sim-tools/             simulation tool docs, wrappers, install/smoke/rollback scripts
```

## Where new work goes

- **New part:** a new top-level folder named after the part (`snake_case`). Inside: `<part>.py`, the generated `<part>.step` / `<part>.stl`, a short `NOTES.md`, and renders in `renders/`. If it has versions, use `v1/`, `v2/`… like `knuckle/`.
- **Simulation runs:** run in the Linux home (`~/sim-runs/<part>/…`) or a git-ignored folder, then copy only summaries (JSON/CSV/PNG) into the part folder.
- **Docs:** update the [Parts index](Parts.md) and add a dated line to `NOTES.md`.

## What git ignores

Venvs, `__pycache__`, scan point clouds (`*.ply`), STEP/STL over 50 MB (listed by name in `.gitignore`), solver output (`*.frd`, `*.vtu`, `*.12d`, `*.cvg`, `*.sta`, big `.npz` meshes) under the iteration folders, and run folders (`runs/`, `sim-runs/`). Files already committed before these rules stay as they are.

The previous front-page README (with the original rebuild notes) is kept at [Legacy-README.md](Legacy-README.md).
