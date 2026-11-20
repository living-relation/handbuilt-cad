# Parts

[← Home](../../README.md)

Part build scripts are not kept in this repo. Each machine keeps them in its **parts home**, created by `setup.sh`:

| What | Where | Notes |
|---|---|---|
| Build scripts, inputs, params, interface JSON, notes | `$HBCAD_PARTS_HOME/<job>/src/` (default `~/cad-parts`) | the editable source of a part; `<job>` is `<name>_<MMDD>`, paired with models `<subject>_<MMDD>` |
| Working outputs (meshes, solver files, iteration STEPs, topo `.npz`, renders, interim JSON) | `$HBCAD_PARTS_HOME/<job>/runs/<YYYYMMDD-HHMM>/` | disposable; `tools/paths.py run_dir()` |
| Iteration history, superseded versions, costly results | `$HBCAD_PARTS_HOME/_archive/<job>/` | read-only by convention |
| Finished STEP and drawings | `$MODELS_DIR/<subject>_<MMDD>/` | one AP242 STEP per part rev; assembly references `Parts/`; no scripts or .f3d |

Cleanup: once a run is published or superseded, delete its regenerable outputs; keep only results that are costly to regenerate, in `_archive/<job>/`. Logs and caches are deleted.
