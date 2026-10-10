# Workflow — scan to machined part

[← Home](../../README.md)

> **For the agent.** You (the person) don't need to run anything on this page. Your AI agent reads it and runs the commands. Your part is the 3 steps on the [home page](../../README.md#start-here-you-dont-run-any-of-this-yourself).

```
 scan (Creality)  →  triage  →  Fairsolid helper  →  hand-built script  →  STEP / Fusion
                                                         │
                                                         └→  FEA / topology  →  machining plan
```

1. **Scan.** Parts are scanned with a Creality scanner (Creality Scan app). Projects live in `C:\project_3D_scans\…` or `%USERPROFILE%\AppData\Local\Creality\CrealityScan\Projects\…`; exported meshes are `result\Mesh.ply` / `Fused.ply`. Scans stay outside git ([scans/INDEX.md](../../scans/INDEX.md)).
2. **Triage.** Pick the best mesh for the part (closed, clean, highest detail), note its size, triangle count and hash in `scans/INDEX.md`. Triage pictures go next to the part (for example `bezel/triage_a.png`).
3. **Fairsolid helper** (separate repo, <https://github.com/living-relation/fairsolid>). Cleans and decimates the scan (`10_clean.ply`), idealises it (`15_ideal.ply`), finds a coordinate frame (`20_frame`) and can fit reference surfaces (`refscan` → `40_ref_surfaces.step`). Runs live in `C:\projects\active\fairsolid\runs\<part>\`. The hand-built work only reads Fairsolid outputs; it never changes Fairsolid.
4. **Measure and hand-build.** In this repo, a part script loads the scan (or the Fairsolid output), applies a rigid frame (`frame_hb.json`, never a scale), measures features (circle fits for holes/bores, plane fits for faces, sections), rounds them to real values and records them (`MEASURED.md`). The build123d script then builds the solid from named dimensions and writes STEP + STL. A fit check compares the solid to the scan (median / p95 distance, % within 0.5 mm) and renders model-vs-scan pictures.
5. **STEP / Fusion.** Open the STEP in Fusion from `\\wsl.localhost\Ubuntu\home\daniel\projects\handbuilt-models\…`. It is a normal solid body.
6. **FEA and topology (optional).** For structural parts (`knuckle_billet/`): loads from `LOADS.md` → `mesh_*.py` (Gmsh, tet10) → `fea_*.py` writes CalculiX decks → `ccx` → `post_*.py` reads `.frd`, reports safety factor per load case and renders. Topology: `topo_simp*.py` (density), `topo_stress.py` (stress-limited, nlopt MMA + pypardiso), then a manual rebuild as a machinable solid and a full FEA re-check. Every derived design must pass the 24 location checks in `knuckle/feature_check/`.
7. **Machining.** Pick a final version, check wall thickness / tool access (`wall_check.py`), write setups, stock and tolerances (`MACHINING.md`). Export the final STEP into `final/<version>/`.
