---
name: scan-to-parametric
description: >-
  Use when turning a 3D scan (mesh) into a clean, editable, machinable CAD
  model. Builds feature-based from exact hard points joined by a few named
  sketched features. Never mesh-to-solid, hull or shrink-wrap. Runs on Daniel's
  PC.
---
**Method: feature-based from hard points.** Measure the hard points exactly (bores, faces, holes, mounts), snap them to cited nominals, then join them with a few named, dimensioned, sketched features. Deliver a clean, closed, machinable solid. Never deliver a solidified mesh, a hull web or faceted faces.

## Always
- **Method and tool up front** in every report and message, e.g. "Feature-based from hard points, Fusion". Every model or image caption names its tool: (Fusion), (build123d), (FreeCAD).
- **Repo rules win over this skill.** Read the repo's README and rules first. Start with safe-repo-preflight. Never work on main. Toolkit code changes go in a scratch clone and patch (toolkit-patch-handoff), and you pull fast-forward only after the merge. Run the repo checks after every edit and report pass/fail before calling a step done.
- **Deliverable: STEP only.** No STL. The native file (Fusion or build123d source) is filed under reference\ by publish-to-models, never as a deliverable.
- **Add-only.** Never overwrite an earlier rev or the original scan. The models folder is add-only: never archive, move or delete anything there. Nothing is deleted anywhere without Daniel's yes.
- **Off-repo CAD stays off-repo.** If the README says the CAD lives elsewhere (e.g. a runs folder), file it there, labelled, and never copy it into the repo.
- **Use Daniel's names** for features. Ask him to define an ambiguous term before you use it.

## Where it runs
- Heavy work runs on Daniel's PC (WSL plus Windows Fusion). If that PC is offline, stop and tell Daniel. Don't fall back to another machine.
- **Python:** treat the shared repo venvs (e.g. `handbuilt-models/.venv`) as read-only for every bot, even with a yes. Use the packages already in them (numpy, trimesh, Open3D approved 10-16) or make your own separate venv.
- **Working folder:** one per job, named in SUMMARY.md (default `C:\Users\<user>\_staging\<job>\` with `fits/ model/ checks/ views/`). Never use the Workstation build folder or Desktop\models as a working folder. Write from WSL into `/mnt/c/...`, never through `\\wsl.localhost`. The working folder stays until Daniel OKs removing it after publish-to-models hash-verifies.
- **Chunk and checkpoint.** Each step finishes inside 50 minutes. After each step, save the model and `progress.json`: steps done, fit results, Fusion version or timeline marker, and the script commit or hash. On restart, resume from the last save.
- **Timeline owner:** pick one at the start (Fusion, or build123d as master) and write it in SUMMARY.md. Later edits go in the owner.

## Fusion rules
- Reuse the existing document (10-document limit). Before each script run, save a version and add a timeline marker named for the step. If a script fails partway, roll back to that version before you retry.
- One script at a time. Send scripts inline in the MCP call. Don't use staged temp files, because they hang. Test with a one-line version print first.
- An open dialog blocks writes. **Never close a dialog or cancel a command by script.** Stop and ask Daniel to clear it.
- Inspect with Section Analysis or Measure only. Never cut, split or extrude-cut to look inside. Show and hide count as edits, so record the visibility state and restore it.

## First time per job
Ask once per job for anything not in the brief or SUMMARY.md: material, process, stock or size limits, critical bores and interfaces, clearances, minimum wall and gap, allowed deviation from the scan, and review views. Save the answers in SUMMARY.md and reuse them. Re-ask only if the brief changes.

## Steps
1. **Prep the scan.** Record the file and units. Align to a part frame and crop out the fixture without smoothing away real geometry. **Scale:** check against a known dimension. If there isn't one, the snapped bore becomes the scale reference. Flag it as "scale derived from bore X", and that bore can't then pass its own fit check. Stop and tell Daniel if scale is off by more than 0.5%.
2. **Hard points (Python fit, exact bodies).** Find every mounting interface first (scan plus OEM photos), and ask Daniel about anything ambiguous. Best-fit cylinders and planes, then snap each to a nominal that cites its source (standard, datasheet, brief or measured table). If a value falls between two standards or is far from nominal, stop, ask, and mark it TBD (primary-source-spec-check). Write `fits/fits.csv` with RMS and max residual, point count, nominal vs measured and source. Also save the named critical interfaces. Flag high-residual (worn or cast) fits. First report: list the hard points with a hard-points-only render.
3. **Connect (sketched features only).** Use a few named, dimensioned features (pads, ribs, arms, pockets) that follow the scan outline, hold clearances and minimum wall, and favour 3-axis access. Apply keep-clear zones (bushing ends, clamp faces, sensor bodies) as named cut bodies before the exact cuts. No fillets at this stage. **Solid-body check (warning):** by default the finished part is a true solid body with real arcs and holes, because it is going to be machined or printed. If any feature is still mesh- or polygon-built, note it for the user. It does not fail the job. If a region can't be done with sketched features, ask Daniel before using any freeform surface.
   **Fillets last:** fillets go at the very end, as the last features on the finished solid after all cuts (tangent-edge handling in Fusion and other CAD). Never fillet features before the boolean union. If a fillet fails, skip it and list it for Daniel to add.
4. **Clean up.** Remove flash, fins, sprue stubs, dangling edges, scan holes and noise. The result must be a closed, machinable solid.
5. **Checks** (on the saved solid, never the mesh, except deviation):
   - Deviation from the scan: mean, RMS, 95th percentile and max, shown pass/fail against the allowance in SUMMARY.md, with removed flash reported separately. Fix the heatmap scale to the allowance.
   - Fits and named interfaces in `fits.csv` vs targets (passes out of total). If a target moves, update the checker in a new versioned file and list what changed. Never claim "matches OEM" from design targets.
   - Minimum wall (including bolt-hole walls) and **minimum gap** (slots and slivers) against the process limit, checked on BRep or Section Analysis.
   - Tapped holes: ≥1.5×D engagement with the real screw and stack-up, modelled as real hole geometry (tap drill plus thread).
   - Mass vs OEM scan volume × material.
   - Then run **cnc-part-check**. It must pass.
6. **Edge breaks (optional, last).** Model them when the CAD does it cleanly, on a saved version after geometry passes, then re-check walls and fits. Otherwise add a drawing note. Either is fine. Don't force it.
7. **Renders** from the delivered model only. Smooth-shaded, no mesh lines, with the saved views plus the heatmap. Tool in each caption. Check that any marker lands on its feature before sending.
8. **Report.** Method and tool first, then fits, scale assumption, deviation, checks and open problems. Walk Daniel through open problems one at a time, each with a marked image and clickable choices.
9. **File.** Only after Daniel approves, file with **publish-to-models** (scan or a path to it goes in `reference\`). Record the scan file, commit and build switches in SUMMARY.md. Copy any finished new script into the Workstation "skills and tools" folder (copy-in only, no secrets, no models).
10. No FEA until Daniel approves the geometry, unless he asks for it.

## Tool per step
| Step | Tool |
|---|---|
| Scan prep, scale, fitting, deviation | WSL Python (residuals; Fusion has no fitting API) |
| Hard points, connecting features, edge breaks | Timeline owner (build123d or Fusion) |
| Wall, gap, hollow checks | BRep / Fusion Section Analysis |
| STEP export, renders | Either, into the job's working folder |
