# Conventions

[← Home](../../README.md)

- **Scan scale stays true.** Only rigid moves (rotate/translate) between scan and part. Never scale a scan to "fix" a size; measure, then round to a real value.
- **Smooth, machined-look solids.** Flat faces, true cylinders, real fillets. No faceted or blobby mesh-derived surfaces in final parts.
- **Named dimensions.** Every size is a named number at the top of the part script (or in `params.json`) so it can be changed and rebuilt.
- **Units:** millimetres, degrees, newtons, MPa, kilograms. Threads named by standard (e.g. 7/8-14 UNF).
- **Fixed interfaces.** Derived designs (billet knuckles) keep every hole, bore, eye and mount exactly where the approved model has them, checked automatically.
- **Safety factor target:** 2.0× on yield at the `LOADS.md` cases for structural parts.
- **Git:** work on `main`, small commits with plain messages. Normal pushes only, never force-push, never rewrite pushed history. Back up (zip to `C:\projects\_archive`) before big reorganisations.
- **Keep out of git:** raw scans, solver output, venvs, secrets, personal files. Files over 50 MB are listed by name in `.gitignore`.
- **Paths don't move.** Existing folders keep their names so scripts keep working; if something must move, update the scripts and leave a pointer.
