---
name: primary-source-spec-check
description: >-
  Use whenever a design, drawing, BOM or answer needs a real spec value
  (thread, pinout, dimension, tolerance, part number): cite the official
  source; mark unknowns TBD.
---
# Primary-source spec check

Get the value from the official standard, manual or datasheet (including ratings). Mark anything unconfirmed TBD instead of guessing.

1. List every spec value the task depends on (threads, pins, dimensions, tolerances, ratings, part numbers).
2. For each, find the primary source: the official standard, OEM service/installation manual, or manufacturer datasheet. Forums, AI answers and reseller listings are leads only, not sources.
3. Record per value: value, unit, tolerance/fit class, source title + revision/date, page/table, and a link.
4. If no primary source confirms a value, write `TBD (unconfirmed)` with what was tried. Never guess or "typical value" it into geometry.
5. Purchased parts: give a real manufacturer part number and a live product/datasheet link. Open each link to verify it loads and matches the part number before reporting.
6. Where sources conflict, show both, prefer the newer official revision, and flag it.
7. Put the table in the deliverable (e.g. SUMMARY.md or BOM notes) so reviewers can trace every number.
