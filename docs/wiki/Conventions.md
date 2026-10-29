# Conventions

[← Home](../../README.md)

- **Scan scale stays true.** Only rigid moves (rotate/translate) between scan and part. Never scale a scan to "fix" a size; measure, then round to a real value.
- **Smooth, machined-look solids.** Flat faces, true cylinders, real fillets. No faceted or blobby mesh-derived surfaces in final parts.
- **Named dimensions.** Every size is a named number at the top of the part script (or in `params.json`) so it can be changed and rebuilt.
- **Units:** millimetres, degrees, newtons, MPa, kilograms. Threads named by standard (e.g. 7/8-14 UNF).
- **Fixed interfaces.** Derived designs (billet knuckles) keep every hole, bore, eye and mount exactly where the approved model has them, checked automatically.
- **Safety factor target (knuckle project convention):** 2.0× on yield at the `LOADS.md` cases for its structural parts. Not a repo-wide rule; other jobs use the owner's target.
- **Electronics:** every design with electronics has a plan document (wiring tables, schematic, electronics BOM). Wiring tables list every required wire; unplanned GPIO/PCB pins are TBA. Electrical designs use real gauges, connectors, routing and device specs ([`AGENTS.md`](../../AGENTS.md) "Electrical and design plans").
- **Off-the-shelf CAD.** Off-the-shelf parts (dev boards, extrusion brackets, plates and similar hardware) use the supplier's official CAD model, or a labelled best-guess from the datasheet when none exists. Put the supplier's part number on the BOM. Save every part model, purchased and fabricated, in a `parts/` folder inside the project.
- **Questions to the maintainer:** always multiple choice, labelled a1, a2, with a recommended answer when there is one.
- **Git:** the rules are in [`AGENTS.md`](../../AGENTS.md) and [`CONTRIBUTING.md`](../../CONTRIBUTING.md): branch -> PR -> review -> merge, never commit or push to `main`, never force-push or rewrite pushed history, never skip a hook. There is one clone, in Windows; WSL reaches it through the `~/projects/handbuilt-cad` link. Run git from Windows and pull with `git pull --ff-only`.
- **Backups:** git history is the backup for anything in the repo. The projects `_archive` folder is only for obsolete work, and only with the owner's OK; no zip snapshots there before changes.
- **STEP only:** STEP is the deliverable; STL only when a print job needs one.
- **FEA after approval:** run strength checks (FEA) only after the owner approves the geometry, unless they ask for early tests.
- **Minimum wall:** structural / critical features only, and never assumed: use the value the owner gave (`cnc_check.py --min-wall`, a walls config). Anything unclear is flagged for the owner.
- **Capped sections:** every rendered section view is closed-surface clipped (cut faces filled), never open cut faces that look like hollow shells (`tools/render/section.py`).
- **Keep out of git:** raw scans, solver output, venvs, secrets, personal files. Files over 50 MB are listed by name in `.gitignore`.
- **Paths don't move.** Existing folders keep their names so scripts keep working; if something must move, update the scripts and leave a pointer.
