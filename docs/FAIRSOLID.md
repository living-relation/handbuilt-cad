# Fairsolid: which copy is the source of truth

**For now, the live fairsolid repo is the source of truth, and `pipelines/fairsolid/` here is a vendored copy.**
This note describes how things stand on 2026-10-17. The owner hasn't made a final decision yet (see "Open decision" below).

## The copies

| Copy | What it is | Used by |
|---|---|---|
| GitHub `living-relation/fairsolid` (main `df79534`) | The live repo, with its own `AGENTS.md` | Source of the two checkouts below |
| Windows checkout `C:\projects\active\fairsolid` | Has a built `.venv`, plus the `runs\` and `handoff\` folders (both outside git) | Real scan runs, e.g. `runs\fuel_hanger_billet_1014` (st185 fuel hanger: `cad/render_trimetric.py`, `cad/DRAWING-REVS.md`, `cad/fuel-hanger/MADE-WITH.md`), and the Grok Bot handoff kit (st185 R106) |
| WSL checkout `~/projects/fairsolid` | Has a built `.venv`, no runs | `tools/scan_helper.py` when `FAIRSOLID_HOME` points at it |
| `pipelines/fairsolid/` (this repo) | Imported from fairsolid `d9e1751` with history (`docs/history/README.md`), plus one commit that pins its dependencies (`uv.lock`, `.python-version`, `[tool.uv]` constraints) | Nothing runs from it today. `setup.sh` can build its venv, but none is built |

## Differences (checked 2026-10-17)
- The source code, tests and recipes are the same as fairsolid `d9e1751`.
- Only here: `uv.lock`, `.python-version` and the transitive pins in `pyproject.toml`.
- Only in the live repo: the test data meshes (`tests/data/*.stl`, `nominal.step`), which this repo's no-model-files rule keeps out, and one later docs commit (`df79534`, the "read first" section in `AGENTS.md`).

## Rules until the owner decides
- Make fairsolid code changes in the live repo, through a PR there. Don't edit `pipelines/fairsolid/` on its own, or the two copies drift apart.
- Point `FAIRSOLID_HOME` at a live checkout. `tools/scan_helper.py` never hard-codes a location.
- Run folders stay outside both repos.

## Open decision (for the owner)
Pick one:
- Keep the live repo as the source. Re-sync `pipelines/fairsolid/` from it now and then, or drop the copy.
- Switch to `pipelines/fairsolid/`. Archive the live repo, but only after its runs and handoff kit have moved.
