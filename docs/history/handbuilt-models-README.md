# Hand-built models

Clean CAD solids built by hand from Daniel's 3D scans: the scan is measured in Python, the sizes are rounded to real values, and a build123d script builds the solid. Each script keeps its sizes as named numbers at the top so they can be changed and rebuilt.

## Folders

| Folder | What it is | Latest / best |
|---|---|---|
| `knuckle/` | Rear suspension knuckle (cast). `v2`-`v5` are successive builds, `renders*` are model-vs-scan pictures, `MEASURED.md` has the measured hole and bore sizes, `frame_hb.json` is the scan alignment. `build/` is the early v2 working copy. | **v4**: the best single valid solid (Daniel approved). Holes, bearing bore steps, bushing eyes and shock mounts are in place; the cast body is simplified. Fit: median 0.66 mm. `v5` holds code only (an experiment that didn't beat v4). |
| `pcv_adapter/` | PCV crankcase ventilation tube, Audi EA888 2.0T, OE **06H103223A**. Photos of the real part are in `photos/`. | **v3** = `pcv_adapter.py` / `.step` / `.stl`: symmetric, 53.0 mm long, 21.8 mm ends, 13.0 mm straight bore, 2 O-ring grooves per end, ball-shaped flare (20.4 mm) into a 16.4 mm neck. `pcv_adapter_v1.*` is the first version. |
| `pedal_adapter/` | Pedal adapter (machined-style part). `work_images/` holds work renders. | `pedal_adapter.py` / `.step` / `.stl`: 9 mm screw posts with 3.5 mm holes, pocket grid, connector, ear. Fit in `check_stats.json` (median 0.16 mm). |
| `catch_can_refscan/` | Reference surfaces of the engine-bay space around the oil catch can mount (from Fairsolid `refscan`), for designing against. `scan2param_T4/` is the earlier trial version. | `40_ref_surfaces.step`: 9 surfaces, most panel points within about 0.07 mm. |
| `bezel/` | Bezel. Being built by another job. | In progress. |
| `sim-tools/` | Simulation tools: CalculiX, Elmer, OpenFOAM 14, Gmsh, ParaView in WSL, plus portable FreeCAD 1.1.4 on Windows. Docs, wrappers, smoke tests and rollback. | See `sim-tools/SIM_TOOLS.md`. |
| `NOTES.md` | Working notes from the hand-build sessions. | |

## Rebuilding a part

The Python environment is at `.venv` (Python 3.13, build123d 0.13.0, trimesh, numpy, scipy, matplotlib).

```powershell
cd C:\projects\active\handbuilt-models\pcv_adapter
..\.venv\Scripts\python.exe pcv_adapter.py      # writes pcv_adapter.step and .stl next to the script
```

Same thing for `pedal_adapter\pedal_adapter.py` (writes to the current folder) and `knuckle\v4\knuckle.py` (run from inside `knuckle\v4`). To change a size, edit the named value at the top of the script and run it again. The STEP files open in Fusion as normal solids.

If the venv is missing: `uv venv .venv --python 3.13` then `uv pip install --python .venv\Scripts\python.exe build123d==0.13.0 trimesh numpy scipy matplotlib rtree`.

## Notes

- This is a local git repo with no remote. STEP/STL files over 50 MB (for example `knuckle/v4/knuckle.step`, about 247 MB) are kept on disk but left out of git; they are listed in `.gitignore`.
- The originals are still in `C:\projects\_scratch\pedal-parametric`, `C:\projects\_scratch\handbuilt` and `C:\Users\danie\agent-tools\`; this folder is a copy.