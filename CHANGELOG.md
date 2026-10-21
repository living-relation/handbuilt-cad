# Changelog

## 2026-10-21: wall checker (`tools/checks/check_printed_walls.py`, #18)
New detection defaults that can change results for existing configs. Each one is a config key; set it to 0 to turn it off:
- `snap = 1e-4` mm: section segment ends closer than this are joined (fixes outlines dropped from a section).
- `despike = 0.02` mm: each section is opened and closed by this, which drops spikes and slits where two cut faces meet.
- `sliver = 0.01` mm: round-off slivers along the shared edges of a thin piece are dropped.
- `graze_sections = 4`: a spot seen by one axis family in fewer sections than this counts as planes grazing a square edge, and is dropped.
- `skin = 1.5` mm: a thin piece must stand at least this far out of the body to count as a cantilever.
These were tuned on a sweep of real printed parts, where the results matched the previous project-specific checker exactly.
Other configs may now report fewer spots. Re-run them and compare, or set the keys to 0 to get the old behaviour.
Also: `walls()` now uses `opts['step']` when `step` isn't passed (before, it silently used the 0.5 mm default).
