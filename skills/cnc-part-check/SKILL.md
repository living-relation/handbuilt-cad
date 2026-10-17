---
name: cnc-part-check
description: >-
  Use when finishing or handing off any 3D CAD model (part or assembly) of a
  CNC-made part, before calling it done, asking for approval, or running FEA:
  valid bodies, STEP round-trip, size/weight/fit vs saved limits, machinability
  sanity check, saved review views. Runs on the CAD workstation.
---
Use for 3D CAD models (single parts or assemblies) of CNC-made parts, before calling a model done, ready for review, or ready for FEA. This skill checks the model only; drawings (11x17 PDF for every part, DXF for machined parts) are a separate step. The model always shows the finished part.

## Where it runs
All checks and CAD work run on the CAD workstation (the machine with the WSL working copy), never on an agent's own computer. If it is offline, stop and tell the owner; don't fall back.
- Python checks: WSL, `$CAD_PY` (handbuilt-cad's own `.venv`: build123d, pyvista). Use the project's check scripts if present, else `$CAD_HOME/tools/cnc_check.py`.
- pyvista renders in WSL need offscreen mode (`PYVISTA_OFF_SCREEN=true` plus xvfb or osmesa), or they hang.
- Write review renders and reports under `$CAD_STAGING/<job>/views` (a staging folder outside any repo and outside the models folder) so the agent can read them. Always write from WSL out to `/mnt/c`; never write through `\\wsl.localhost` paths from Windows.
- Headless FreeCAD: `$FREECAD_DIR/bin/freecadcmd.exe` (read-only for agents; never install or upgrade there).
- Tip: write a .sh file and run it with `wsl -e bash -c "tr -d '\r' < file | bash"` to avoid PowerShell quoting problems.

## First time on a model: fill gaps, then save
Use what the owner already gave (brief, BOM, existing SUMMARY.md). Ask only for what's missing; skip asking if nothing is. Save answers in SUMMARY.md and reuse them unless the owner changes them. On a check-only run, don't save; report what's missing so it's saved at the next publish.
- Limits: overall size or stock, critical bores and holes, minimum wall for critical or structural features, material.
- Review views: if none are saved yet, render a sensible default set, send it to whoever assigned the job to confirm, then save.
- Fit targets: what it bolts to or sits next to.
- Don't ask the owner about cutters unless they are the machinist. Assume standard shop end mills and state the radius used.

## Which files to check
Check the primary file(s) named in SUMMARY.md/MANIFEST.sha256 (assemblies: the assembly STEP plus each machined part). If none are named, ask; on a check-only run, check the obvious files by name and flag it as a guess. Other files people add (drawings, PDFs, photos) are expected; ignore them, never move or delete them.

## Assemblies: check each body by type
- Machined bodies: all steps.
- 3D-printed bodies: valid body, quick wall and hole check (minimum wall on critical or structural features; flag the rest, see step 3).
- Purchased or customer-supplied parts (screws, fuse boxes, ECU boards): valid body and no overlap only.

## Steps
1. Valid bodies. A part is one valid solid; in an assembly every body is valid on its own.
2. STEP round-trip. Export, reopen, confirm the same bodies and volume within 0.1%. The STEP is what the shop gets, and export can silently break geometry.
3. Size vs saved limits (machined bodies). Size, bores, minimum wall; flag anything out of range. The minimum wall applies to critical or structural features only: load-bearing walls, outer skins behind pockets, mounting / clip / retention features, walls that separate circuits or fluids, and anything that seals. A thin spot on any of those fails. A thin spot elsewhere is not a failure, but list it for the owner to change or approve. If you can't tell whether a spot is structural, call it questionable and flag it; never pass it silently. Fix thin structural walls in geometry before adding edge breaks.
4. Weight (machined bodies). Compute mass; record material and density. Compare to the last approved rev's mass from its SUMMARY.md, or write "no baseline". A sudden drop with the same material usually means a chunk fell out when shapes were joined.
5. Fit. Check against saved fit targets; report passes vs total. Assemblies also check overlaps and mates. Intentional O-ring or gasket squeeze is not a failure: report the squeeze % and flag it if outside the normal range (static O-rings about 15–30%).
6. Machinability, no toolpaths (machined bodies). Report the setup count (flips and re-clamps, as a minimum), the smallest inside corner radius vs the assumed cutter radius, and unreachable or knife-edge spots.
7. Review views. Render the saved views, look at them yourself, then send.
8. Report numbers, views, open problems and the flag list (thin spots that are non-structural or unclear, each for the owner to change or approve). No strength or FEA until geometry is approved, unless the owner asks for early tests to check the overall design or find risks.

## Edge breaks
- Optional. Model them as small chamfers when the CAD handles them cleanly; otherwise skip them in the model and cover them with a BREAK SHARP EDGES drawing note.
- Select only convex outside edges, never inside corners. Skip edges next to walls under 3 mm (chamfers there leave slivers).
- Apply in small batches with headless FreeCAD; log which edges each batch did so a retry never chamfers an edge twice; if a batch fails, split it to find the bad edge; save progress between batches.
- Afterward, re-run the size/minimum-wall (including bolt-hole walls) and fit checks on the final solid. A new thin spot on a structural feature is a failure; any other new thin spot goes on the flag list.

## Notes
- New revs go in new files or folders; never overwrite an old rev.
