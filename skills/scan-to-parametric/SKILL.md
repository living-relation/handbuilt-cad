---
name: scan-to-parametric
description: >-
  Use when turning a 3D scan or mesh into a clean, editable, machinable
  parametric CAD model built from hard points and sketched features, never
  mesh-to-solid.
---
**Method: feature-based from hard points.** Measure the hard points exactly (bores, faces, holes, mounts), snap them to cited nominals, then join them with a few named, dimensioned, sketched features. Deliver a clean, closed, machinable solid. Never deliver a solidified mesh, a hull web or faceted faces. Never mesh-to-solid, hull or shrink-wrap. Runs on the user's machine.

## Always
- **Method and tool up front** in every report and message, e.g. "Feature-based from hard points, Fusion". Every model or image caption names its tool: (Fusion), (build123d), (FreeCAD).
- **Repo rules win over this skill.** Read the repo's README and rules (AGENTS.md, decision log, register) first. Start with safe-repo-preflight. Never work on main. Toolkit code changes go in a scratch clone and patch (toolkit-patch-handoff), and you pull fast-forward only after the merge. Run the repo checks after every edit and report pass/fail before calling a step done.
- **Deliverable: STEP only.** No STL unless a print job needs one. The native file (Fusion or build123d source) is filed under reference\ by publish-to-models, never as a deliverable.
- **Add-only.** Never overwrite an earlier rev or the original scan. The models folder is add-only: never archive, move or delete anything there. Nothing is deleted anywhere without the user's yes.
- **Off-repo CAD stays off-repo.** If the README says the CAD lives elsewhere (e.g. a runs folder, `[paths] fairsolid_runs` or similar), file it there, labelled, and never copy it into the repo.
- **Use the user's names** for features. Ask them to define an ambiguous term before you use it.
- **Look it up first.** Find the maker's drawings, datasheets and specs yourself (primary sources) before asking the user; ask only what they can't answer.
- **Inside a project repo with its own rules, they win on asking** (for example: open questions go in its open-items list, no pickers; look up maker drawings and specs yourself first). Everywhere else, use clickable choices (step 8).
- **Look at the assembly first.** Before editing a part on its own, check how it sits and mates in the assembly.

## Where it runs
- Heavy work runs on the user's machine (e.g. WSL plus Windows Fusion). If that machine is offline, stop and tell the user. Don't fall back to another machine.
- **Paths** come from the toolkit repo's `local.toml` (set up by its setup step; each key also has an environment variable): `[python] cad_py` (`CAD_PY`), `[paths] cad_staging` (`CAD_STAGING`), `[paths] models_dir` (`MODELS_DIR`), `[paths] freecad_dir` (`FREECAD_DIR`). Never hard-code a user, home or cloud-drive path. If a needed key is empty, ask the user.
- **Python:** treat shared environments (another project's venv) as read-only for every agent, even with a yes. Use the packages already in them (e.g. numpy, trimesh, Open3D) or make your own separate venv.
- **Working folder:** one per job, named in SUMMARY.md (default `<cad_staging>/<job>/` with `fits/ model/ checks/ views/`). Never use a build folder or the models home as a working folder. On Windows + WSL, write from WSL into `/mnt/c/...`, never through `\\wsl.localhost`. The working folder stays until the user OKs removing it after publish-to-models hash-verifies.
- **Chunk and checkpoint.** Each step finishes inside 50 minutes. After each step, save the model and `progress.json`: steps done, fit results, CAD version or timeline marker, and the script commit or hash. On restart, resume from the last save.
- **Timeline owner:** pick one at the start (Fusion, or build123d as master) and write it in SUMMARY.md. Later edits go in the owner.

## Fusion rules
- Reuse the existing document (Fusion's open-document limit). Before each script run, save a version and add a timeline marker named for the step. If a script fails partway, roll back to that version before you retry.
- One script at a time. Send scripts inline in the MCP call. Don't use staged temp files, because they hang. Test with a one-line version print first.
- An open dialog blocks writes. **Never close a dialog or cancel a command by script.** Stop and ask the user to clear it.
- Inspect with Section Analysis or Measure only. Never cut, split or extrude-cut to look inside. Show and hide count as edits, so record the visibility state and restore it.

## First time per job
Ask once per job for anything not in the brief or SUMMARY.md: material, process, stock or size limits, critical bores and interfaces, clearances, minimum wall (for structural / critical features) and gap, allowed deviation from the scan, and review views. Save the answers in SUMMARY.md and reuse them. Re-ask only if the brief changes. Never assume a minimum wall.

## Steps
1. **Prep the scan.** Record the file and units. Align to a part frame and crop out the fixture without smoothing away real geometry. **Scale:** check against a known dimension. If there isn't one, the snapped bore becomes the scale reference. Flag it as "scale derived from bore X", and that bore can't then pass its own fit check. Stop and tell the user if scale is off by more than 0.5%.
2. **Hard points (Python fit, exact bodies).** Find every mounting interface first (scan plus OEM photos), and ask the user about anything ambiguous. Best-fit cylinders and planes, then snap each to a nominal that cites its source (standard, datasheet, brief or measured table). If a value falls between two standards or is far from nominal, stop, ask, and mark it TBD (primary-source-spec-check). Write `fits/fits.csv` with RMS and max residual, point count, nominal vs measured and source. Also save the named critical interfaces. Flag high-residual (worn or cast) fits. First report: list the hard points with a hard-points-only render.
3. **Connect (sketched features only).** Use a few named, dimensioned features (pads, ribs, arms, pockets) that follow the scan outline, hold clearances and minimum wall, and favour 3-axis access. Apply keep-clear zones (bushing ends, clamp faces, sensor bodies) as named cut bodies before the exact cuts. No fillets at this stage. If a region can't be done with sketched features, ask the user before using any freeform surface.
   **Fillets last:** fillets go at the very end, as the last features on the finished solid after all cuts (tangent-edge handling in Fusion and other CAD). Never fillet features before the boolean union. If a fillet fails, skip it and list it for the user (flag list and drawing notes).
4. **Clean up.** Remove flash, fins, sprue stubs, dangling edges, scan holes and noise. The result must be a closed, machinable solid.
5. **Checks** (on the saved solid, never the mesh, except deviation):
   - Deviation from the scan: mean, RMS, 95th percentile and max, shown pass/fail against the allowance in SUMMARY.md, with removed flash reported separately. Fix the heatmap scale to the allowance.
   - Fits and named interfaces in `fits.csv` vs targets (passes out of total). If a target moves, update the checker in a new versioned file and list what changed. Never claim "matches OEM" from design targets.
   - Minimum wall (including bolt-hole walls) on structural / critical features (fail) and other thin spots (flag), and **minimum gap** (slots and slivers) against the process limit, checked on BRep or Section Analysis.
   - Tapped holes: ≥1.5×D engagement with the real screw and stack-up, modelled as real hole geometry (tap drill plus thread).
   - Mass vs OEM scan volume × material.
   - Then run **cnc-part-check**. It must pass.
6. **Edge breaks (optional, last).** Model them when the CAD does it cleanly, on a saved version after geometry passes, then re-check walls and fits. Otherwise add a drawing note. Either is fine. Don't force it.
7. **Renders** from the delivered model only, shown as smooth solid bodies with mesh triangulation and polygon edges hidden, with the saved views plus the heatmap. Tool in each caption. Check that any marker lands on its feature before sending. Section views are capped (closed-surface clipping, solid cut faces), never open cut faces, which render as hollow shells.
8. **Report.** Method and tool first, then fits, scale assumption, deviation, checks and open problems. Walk the user through open problems one decision at a time, each with a marked image and clickable choices (inside a project with an open-items rule: its list instead).
9. **File.** Only after the user approves, file with **publish-to-models** (scan or a path to it goes in `reference\`). Record the scan file, commit and build switches in SUMMARY.md, and the tool in MADE-WITH.md. Copy any finished, reusable new script into the user's shared tools folder only if the project asks for it (copy-in only, no secrets, no models).
10. No FEA until the user approves the geometry, unless they ask for it.

## Tool per step
| Step | Tool |
|---|---|
| Scan prep, scale, fitting, deviation | Python (residuals; Fusion has no fitting API) |
| Hard points, connecting features, edge breaks | Timeline owner (build123d or Fusion) |
| Wall, gap, hollow checks | BRep / Fusion Section Analysis |
| STEP export, renders | Either, into the job's working folder |
