# Where this repo came from

Imported with `git filter-repo` from fresh clones (never the original checkouts). Filters on every
import: part/model files, archives, solver outputs and logs removed from all history
(`*.step *.stp *.stl *.brep *.3mf *.f3d *.fcstd *.ply *.obj *.iges *.glb *.npz *.npy *.frd *.vtu
*.zip *.7z *.log *.out .env*`), and every blob over 1 MB stripped.

| Source | Source commit | Imported into | Method |
|---|---|---|---|
| handbuilt-models (main) | `57729e3094a6ec1c9a53368a6e3b88899860a1e1` | `tools/`, `sim/`, `parts/`, `examples/`, `docs/`, `scans/`, `requirements-sim.txt`; old README/setup/NOTES/ignore files under `docs/history/` | filter-repo (history kept) |
| fairsolid (main) | `d9e17517da580bca3c1df93b73418bfa4741c30e` | `pipelines/fairsolid/` | filter-repo (history kept) |
| stevecad-tools (branch drawing-rules-1017) | `73b49cf1a44f7e9b995a6852d389c28eeef36ff8` (filtered tree identical to 1a7ab56; 73b49cf only changed the excluded skills/ copies) | `drawing/`, `tools/checks/` (minus `check_printed_walls.py`), `tools/render/`, `tests/test_revs.py`; old README/requirements under `docs/history/` | filter-repo (history kept; examples and skill copies left out) |
