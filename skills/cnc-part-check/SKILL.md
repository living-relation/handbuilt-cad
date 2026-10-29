---
name: cnc-part-check
description: >-
  Use before calling a CNC part or assembly CAD model done, asking for
  approval, handing it off or running FEA. Runs on the user's machine.
---
Use for 3D CAD models (single parts or assemblies) of CNC-made parts, before calling a model done, ready for review, or ready for FEA. Checks include valid bodies, STEP round-trip, size/weight/fit vs saved limits, structural-only minimum wall, machinability sanity, and saved review views. This skill checks the model only; drawings (11x17 PDF for every part, DXF for machined parts) are a separate step. The model always shows the finished part.

The project's own rules (AGENTS.md, decision log, revision register) win over this skill wherever they differ.

## Where it runs
All checks and CAD work run on the user's machine, never on the agent's own computer. If that machine is offline, stop and tell the user; don't fall back.
- Paths come from the toolkit repo's `local.toml` (created by its setup step from `local.toml.example`); each key can also be set by the environment variable named beside it. Never hard-code a user, home or cloud-drive path.
  - `[python] cad_py` (`CAD_PY`): the CAD Python (build123d, pyvista). Empty = the repo's own `.venv`.
  - `[paths] cad_staging` (`CAD_STAGING`): scratch output for review renders and reports, outside the repo.
  - `[paths] freecad_dir` (`FREECAD_DIR`): folder holding `bin/freecadcmd` (`freecadcmd.exe` on Windows) for headless FreeCAD.
  - If a key the step needs is empty or the path is missing, stop and ask the user to fill it in; don't guess.
- Use the project's check scripts if present, else the toolkit's (`tools/cnc_check.py`, `checks/`). A project that pins its own environment keeps it; never re-point or rebuild another project's environment.
- Shared environments and tool folders are read-only for agents: use what's installed, never install or upgrade into them.
- pyvista renders under WSL or headless Linux need offscreen mode (`PYVISTA_OFF_SCREEN=true` plus xvfb or osmesa), or they hang.
- Write review renders and reports under `<cad_staging>/<job>/views`. On Windows + WSL, write from WSL out to `/mnt/c/...`; never write through `\\wsl.localhost` paths from Windows.
- Tip (Windows + WSL): write a .sh file and run it with `wsl -e bash -c "tr -d '\r' < file | bash"` to avoid PowerShell quoting problems.

## First time on a model: fill gaps, then save
Use what the user already gave (brief, BOM, existing SUMMARY.md). Ask only for what's missing; skip asking if nothing is. Save answers in SUMMARY.md and reuse them unless the user changes them. On a check-only run, don't save; report what's missing so it's saved at the next publish.
- Limits: overall size or stock, critical bores and holes, minimum wall for critical or structural features, edge-break skip wall (see Fillets and edge breaks), material. If SUMMARY.md has no minimum-wall value, ask once here; never assume one (not 2 mm, not any default).
- Review views: if none are saved yet, render a sensible default set, send it to whoever assigned the job (the user, or the reviewer) to confirm, then save.
- Fit targets: what it bolts to or sits next to.
- Never ask the user about cutters unless they are the machinist. Assume standard shop end mills and state the radius used.

## Asking the user
- Look it up first. For bought parts, mating parts and standards, find the maker's drawings, datasheets and specs yourself (primary sources) and cite them. Ask only what those can't answer, and mark a value TBD only if no source settles it (primary-source-spec-check). Unplanned GPIO/PCB pins are TBA, not a guessed pin.
- Inside a project repo with its own rules (an AGENTS.md or a decision log), those rules win: for example, open questions go in its open-items list instead of pickers, and maker drawings and specs are looked up before asking.
- Everywhere else: one decision at a time, each with an image and multiple-choice answers labelled with one letter plus a number (a1, a2), with a recommended answer when there is one.

## Which files to check
Check the primary file(s) named in SUMMARY.md/MANIFEST.sha256 (assemblies: the assembly STEP plus each machined part). If none are named, ask; on a check-only run, check the obvious files by name and flag it as a guess. Other files people add (drawings, PDFs, photos) are expected; ignore them, never move or delete them.

## Assemblies: check each body by type
- Before changing any part on its own, look at the assembly to see how it is oriented and what it mates with.
- Machined bodies: all steps.
- 3D-printed bodies: valid body, minimum wall on critical or structural features (step 3 rules; flag the rest), and hole sizes vs saved limits. Skip weight, machinability and setups.
- Purchased or customer-supplied parts (screws, enclosures, circuit boards, extrusion brackets, plates): valid body and no overlap only. Off-the-shelf parts use the supplier's official CAD model, or a clearly labelled best-guess from the datasheet when none exists. Put the supplier's part number on the BOM. Save every part model, purchased and fabricated, in a `parts/` folder inside the project.

## Steps
1. Valid bodies. A part is one valid solid; in an assembly every body is valid on its own.
2. STEP round-trip. Export, reopen, confirm the same bodies and volume within 0.1%. The STEP is what the shop gets, and export can silently break geometry.
3. Size vs saved limits (machined bodies). Size, bores, minimum wall (the saved value; if none is saved, ask once per First time, never assume); flag anything out of range. The minimum wall applies to critical or structural features only: load-bearing walls, outer skins behind pockets, mounting / clip / retention features, walls that separate circuits or fluids, and anything that seals. A thin spot on any of those fails. A thin spot elsewhere is not a failure, but list it for the user to change or approve. If you can't tell whether a spot is structural, call it questionable and flag it; never pass it silently. Thin spots the user already approved are listed under "Approved thin spots" in SUMMARY.md (location, thickness, date), or in the project's own record if it has one (e.g. the exemptions in its wall-check config, `checks/walls.example.toml`); don't re-flag them unless the geometry there changed (different thickness or surrounding faces). Fix thin structural walls in geometry before adding fillets or edge breaks.
4. Weight (machined bodies). Compute mass; record material and density. Compare to the last approved rev's mass from its SUMMARY.md, or write "no baseline". A sudden drop with the same material usually means a chunk fell out when shapes were joined.
5. Fit. Check against saved fit targets; report passes vs total. Assemblies also check overlaps and mates. Intentional O-ring or gasket squeeze is not a failure: report the squeeze % and flag it if outside the normal range (static O-rings about 15–30%).
6. Machinability, no toolpaths (machined bodies). Report the setup count (flips and re-clamps, as a minimum), the smallest inside corner radius vs the assumed cutter radius, and unreachable or knife-edge spots.
7. Review views. Render the saved views with the model shown as smooth solid bodies, mesh triangulation and polygon edges hidden; look at them yourself, then send. Section views are capped (closed-surface clipping, solid cut faces), never open cut faces, which render as hollow shells. (`tools/render/smooth_render.py --section`).
8. Report numbers and views, then (following Asking the user) walk the user through the open problems and the flag list (thin spots that are non-structural or unclear, skipped fillets) one decision at a time: each finding gets an image of the spot and multiple-choice answers labelled a1, a2 (e.g. a1 Change it / a2 Approve as is — recommended / a3 Not sure, discuss). Save the approvals where step 3 lists them (on a check-only run, report them so they're saved at the next publish). No strength or FEA until geometry is approved, unless the user asks for early tests to check the overall design or find risks.

## Fillets and edge breaks
- Both come last, after all cuts (pockets, holes, slots) are done.
- Fillets: apply in small batches; if a batch fails, split it to find the bad edge; if that edge still fails on its own, skip it and add it to the flag list and the drawing notes. Never stall the model on one fillet.
- Edge breaks are optional. Model them as small chamfers when the CAD handles them cleanly; otherwise skip them in the model and cover them with a BREAK SHARP EDGES drawing note.
- Select only convex outside edges, never inside corners. Skip edges next to walls thinner than the saved edge-break skip wall in SUMMARY.md (chamfers there leave slivers), and never chamfer an edge if it would take a structural wall below the saved minimum wall. If no skip wall is saved, suggest 3 mm and ask once with the other limits.
- Apply in small batches (headless FreeCAD from `freecad_dir`, or the timeline owner's CAD); log which edges each batch did so a retry never chamfers or fillets an edge twice; if a batch fails, split it to find the bad edge; save progress between batches.
- Afterward, re-run the size/minimum-wall (including bolt-hole walls) and fit checks on the final solid. A new thin spot on a structural feature is a failure; any other new thin spot goes on the flag list.

## Notes
- New revs follow publish-to-models: in the models home, new rev-letter folders (`rev<LETTER>`, clerical `rev<LETTER>.<NN>`); in a project repo with its own revision register, its rules win. Never overwrite a rev; file a new one. The latest rev replaces the previous one: once it is filed, delete the old rev's models and outputs (models folder and runs). Never keep old revs side by side.
- Drawings follow the drawing rules: no hidden lines, no mesh lines, the model drives the drawing. Workflow: redline the drawing, then change the model, then regenerate the drawing.
- Designs with electronics need a plan document (wiring tables, schematic, electronics BOM) per AGENTS.md "Electrical and design plans". Wiring tables list every required wire; unplanned GPIO/PCB pins are TBA. Electrical designs use real gauges, connectors, routing and device specs.
