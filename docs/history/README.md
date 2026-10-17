# Where this repo came from

Imported with `git filter-repo` from fresh clones (never the original checkouts). Filters on every
import: part/model files, archives, solver outputs and logs removed from all history
(`*.step *.stp *.stl *.brep *.3mf *.f3d *.fcstd *.ply *.obj *.iges *.glb *.npz *.npy *.frd *.vtu
*.zip *.7z *.log *.out .env*`), and every blob over 1 MB stripped.

| Source | Source commit | Imported into | Method |
|---|---|---|---|
| handbuilt-models (main) | `57729e3094a6ec1c9a53368a6e3b88899860a1e1` | `tools/`, `sim/`, `parts/`, `examples/`, `docs/`, `scans/`, `requirements-sim.txt`; old README/setup/NOTES/ignore files under `docs/history/` | filter-repo (history kept) |
| fairsolid (main) | `d9e17517da580bca3c1df93b73418bfa4741c30e` | `pipelines/fairsolid/` | filter-repo (history kept) |
| stevecad-tools (branch drawing-rules-1017) | `5e1355875f5cbe4a24f9ff1c494aca7b8d94f632` | `drawing/`, `tools/checks/` (minus `check_printed_walls.py`), `tools/render/`, `tests/test_revs.py`; old README/requirements under `docs/history/` | filter-repo (history kept; examples and skill copies left out) |
| stevecad-tools (branch generic-skills-1017) | `7688e333f15925442942fdc9b57576847bc64f4e` | `skills/` (cnc-part-check, publish-to-models, scan-to-parametric, toolkit-patch-handoff), `tools/checks/check_printed_walls.py`, `wall_classes.py`, `walls.example.toml`, `walls_any.py`, `tests/test_walls.py`, `drawing/part.py`, rule 16 of `drawing/DRAWING-RULES.md`; `patches/handbuilt-cad-freecad-check.patch` applied to `sim/smoke/`, `tests/` and `local.toml.example` | file copy (no history); paths `checks/` -> `tools/checks/`; `dwg.py`, `revs.py`, README and requirements changes not taken |
