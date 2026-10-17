# Verified command recipes

Each file here documents the **real** commands and parameter names for one
tool, read out of the installed software rather than from tutorials, and
exercised by `tests/`.

## Status

| Tool | File | Status |
|---|---|---|
| MeshLab / pymeshlab 2025.7 | `meshlab.md` | **verified** — filter and parameter names read via `pymeshlab.print_filter_parameter_list`, exercised end-to-end |
| CadQuery 2.8.0 / OCCT | `cadquery.md` | **verified** — including the teardown crash and the `to_planar` frame trap |
| CloudCompare | — | **not yet written.** Not installed; `s20_frame` does alignment natively, so CloudCompare is not currently on the critical path |
| Instant Meshes | — | **not yet written.** Needed only for the freeform/organic branch. Batch mode confirmed to exist (`-o` triggers it, `src/batch.h`) but not yet run here |
| FreeCAD 1.1.3 + Detessellate | — | **not yet written.** The assisted-manual fallback; not installed yet |
| 2STEP-Converter | — | **not yet written.** MIT, Python 3.12, fits analytic primitives; `s50_reconstruct` currently covers this ground |

Anything marked "not yet written" is deliberately absent rather than guessed.
A recipe that has not been run is worse than no recipe, because it reads
exactly like one that has.
