# Where this repo came from

Imported with `git filter-repo` from fresh clones (never the original checkouts). Filters on every
import: part/model files, archives, solver outputs and logs removed from all history
(`*.step *.stp *.stl *.brep *.3mf *.f3d *.fcstd *.ply *.obj *.iges *.glb *.npz *.npy *.frd *.vtu
*.zip *.7z *.log *.out .env*`), and every blob over 1 MB stripped.

| Source | Source commit | Imported into | Method |
|---|---|---|---|
| handbuilt-models (main) | `57729e3094a6ec1c9a53368a6e3b88899860a1e1` | `tools/`, `sim/`, `parts/`, `examples/`, `docs/`, `scans/`, `requirements-sim.txt`; old README/setup/NOTES/ignore files under `docs/history/` | filter-repo (history kept) |
| fairsolid (main) | `d9e17517da580bca3c1df93b73418bfa4741c30e` | `pipelines/fairsolid/` | filter-repo (history kept) |
