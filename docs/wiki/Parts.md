# Parts

[← Home](../../README.md)

Part build scripts are not kept in this repo. Each machine keeps them in its **parts home**, created by `setup.sh`:

| What | Where | Notes |
|---|---|---|
| Build scripts, inputs, params, interface JSON, notes | `$HBCAD_PARTS_HOME/<job>/src/` (default `~/cad-parts`) | the editable source of a part; job names match the models folder |
| Working outputs (meshes, solver files, iteration STEPs, topo `.npz`, renders, interim JSON) | `$HBCAD_PARTS_HOME/<job>/runs/<YYYYMMDD-HHMM>/` | disposable; `tools/paths.py run_dir()` |
| Iteration history, superseded versions, costly results | `$HBCAD_PARTS_HOME/_archive/<job>/` | read-only by convention |
| Finished deliverables (final STEP, drawings, review views, final strength summary, SUMMARY.md) | `$MODELS_DIR/<job>/rev<LETTER>/` | skill `publish-to-models`; STEP only |

Cleanup: once a run is published or superseded, delete its regenerable outputs; keep only results that are costly to regenerate, in `_archive/<job>/`. Logs and caches are deleted.
