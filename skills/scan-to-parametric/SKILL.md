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
- **Deliverable: AP242 STEP only** (publish-to-models). No STL or other format in the models folder (a Fusion .f3d only when needed, AGENTS.md rule 13); a print STL stays in the parts home. The native source (build123d script, Fusion document) stays in the parts home or Fusion's cloud, never in the models folder.
- **Don't overwrite.** Never edit an existing rev or the original scan. 3D scans are never deleted. Old versions in the models folder follow publish-to-models step 7 (the 2 latest versions of each assembly are kept).
- **Off-repo CAD stays off-repo.** If the README says the CAD lives elsewhere (e.g. a runs folder, `[paths] fairsolid_runs` or similar), file it there, labelled, and never copy it into the repo.
- **Use the user's names** for features. Ask them to define an ambiguous term before you use it.
- **Look it up first.** Find the maker's drawings, datasheets and specs yourself (primary sources) before asking the user; ask only what they can't answer.
- **Inside a project repo with its own rules, they win on asking** (for example: open questions go in its open-items list, no pickers; look up maker drawings and specs yourself first). Everywhere else, multiple choice labelled a1, a2, with a recommended answer when there is one (step 8).
- **Look at the assembly first.** Before editing a part on its own, check how it sits and mates in the assembly.

## Where it runs
- Heavy work runs on the user's machine (e.g. WSL plus Windows Fusion). If that machine is offline, stop and tell the user. Don't fall back to another machine.
- **Paths** come from the toolkit repo's `local.toml` (set up by its setup step; each key also has an environment variable): `[python] cad_py` (`CAD_PY`), `[paths] parts_home` (`HBCAD_PARTS_HOME`), `[paths] cad_staging` (`CAD_STAGING`), `[paths] models_dir` (`MODELS_DIR`), `[paths] freecad_dir` (`FREECAD_DIR`). Never hard-code a user, home or cloud-drive path. If a needed key is empty, ask the user.
- **Python:** treat shared environments (another project's venv) as read-only for every agent, even with a yes. Use the packages already in them (e.g. numpy, trimesh, Open3D) or make your own separate venv.
- **Working folder:** one per job in the parts home (`~/cad-parts/<job>/runs/<stamp>/` with `fits/ model/ checks/ views/`, `tools/paths.py`), named in SUMMARY.md. Never use a build folder or the models home as a working folder. When Windows Fusion must read or write a file, use `<cad_staging>/<job>/` as a transient exchange folder only, write from WSL into `/mnt/c/...` (never through `\\wsl.localhost`), and empty it after publish. Regenerable working outputs are deleted after publish-to-models hash-verifies; agents clean up after themselves.
- **Chunk and checkpoint.** Each step finishes inside 50 minutes. After each step, save the model and `progress.json`: steps done, fit results, CAD version or timeline marker, and the script commit or hash. On restart, resume from the last save.
- **Timeline owner:** pick one at the start (Fusion, or build123d as master) and write it in SUMMARY.md. Later edits go in the owner.

## Fusion rules
- Local Fusion Desktop runs only under the per-PC Fusion Desktop lock (`-Name fusion-desktop`, workstation `instructions/projects-AGENTS.md` section 5): acquire first, check in at least every 10 min, release when done.
- Reuse the existing document (Fusion's open-document limit). Before each script run, save a version and add a timeline marker named for the step. If a script fails partway, roll back to that version before you retry.
- One script at a time. Send scripts inline in the MCP call. Don't use staged temp files, because they hang. Test with a one-line version print first.
- An open dialog blocks writes. **Never close a dialog or cancel a command by script.** Stop and ask the user to clear it.
- Inspect with Section Analysis or Measure only. Never cut, split or extrude-cut to look inside. Show and hide count as edits, so record the visibility state and restore it.

## First time per job
Ask once per job for anything not in the brief or SUMMARY.md: material, process, stock or size limits, critical bores and interfaces, clearances, minimum wall (for structural / critical features) and gap, allowed deviation from the scan, and review views. Save the answers in SUMMARY.md and reuse them. Re-ask only if the brief changes. Never assume a minimum wall.

## Steps
1. **Prep the scan.** Record the file and units. Align to a part frame and crop out the fixture without smoothing away real geometry. **Scale:** check against a known dimension. If there isn't one, the snapped bore becomes the scale reference. Flag it as "scale derived from bore X", and that bore can't then pass its own fit check. Stop and tell the user if scale is off by more than 0.5%.
2. **Hard points (Python fit, exact bodies).** Find every mounting interface first (scan plus OEM photos), and ask the user about anything ambiguous. Best-fit cylinders and planes, then snap each to a nominal that cites its source (standard, datasheet, brief or measured table). If a value falls between two standards or is far from nominal, stop, ask, and mark it TBD (primary-source-spec-check). Write `fits/fits.csv` with RMS and max residual, point count, nominal vs measured and source. Also save the named critical interfaces. Flag high-residual (worn or cast) fits. First report: list the hard points with a hard-points-only render.
3. **Connect (sketched features only).** Use a few named, dimensioned features (pads, ribs, arms, pockets) that follow the scan outline, hold clearances and minimum wall, and favour 3-axis access. For CNC inside corners, put the tool radius at 1.3x the nearest standard tool, never an exact standard size (`docs/CNC-MACHINING-RULES.md` CNC-CORNER-R). Apply keep-clear zones (bushing ends, clamp faces, sensor bodies) as named cut bodies before the exact cuts. No fillets at this stage. If a region can't be done with sketched features, ask the user before using any freeform surface.
   **Fillets last:** fillets go at the very end, as the last features on the finished solid after all cuts (tangent-edge handling in Fusion and other CAD). Never fillet features before the boolean union. Do not fillet inside edges of CNC parts; leave floors sharp unless function needs a floor radius. If a fillet fails, skip it and list it for the user (flag list and drawing notes).
4. **Clean up.** Remove flash, fins, sprue stubs, dangling edges, scan holes and noise. The result must be a closed, machinable solid.
5. **Checks** (on the saved solid, never the mesh, except deviation):
   - Deviation from the scan: mean, RMS, 95th percentile and max, shown pass/fail against the allowance in SUMMARY.md, with removed flash reported separately. Fix the heatmap scale to the allowance.
   - Fits and named interfaces in `fits.csv` vs targets (passes out of total). If a target moves, update the checker in a new versioned file and list what changed. Never claim "matches OEM" from design targets.
   - Minimum wall (including bolt-hole walls) on structural / critical features (fail) and other thin spots (flag), and **minimum gap** (slots and slivers) against the process limit, checked on BRep or Section Analysis. CNC machined walls use `docs/CNC-MACHINING-RULES.md` (0.030" / 0.762 mm metal, 0.060" / 1.52 mm plastic or composite); a wall under that floor fails.
   - Tapped holes: model as real hole geometry (tap drill plus thread) with the real screw and stack-up. 1.5×D is the minimum engagement; under that is a model-check flag only and must not change drawing callouts. Deeper than 2×D is never flagged. Call out actual blind thread depth; both drill and thread depth when the hole is deeper; through holes are `THRU` with no depth (`docs/CNC-MACHINING-RULES.md` CNC-THREAD-DEPTH).
   - Mass vs OEM scan volume × material.
   - Then run **cnc-part-check**. It must pass.
6. **Edge breaks (never auto-applied, last).** If chamfers or fillets are already modeled, dimension them and add no general note. If not, and exposed sharp edges could cut hands, prompt the user; only if they approve, add a leader `BREAK ALL EDGES, STD` or a length they gave. Prefer 45° chamfers when the user asks to model breaks. Then re-check walls and fits. (`docs/CNC-MACHINING-RULES.md` CNC-EDGE-BREAK).
7. **Renders** from the delivered model only, shown as smooth solid bodies with mesh triangulation and polygon edges hidden, with the saved views plus the heatmap. Tool in each caption. Check that any marker lands on its feature before sending. Section views are capped (closed-surface clipping, solid cut faces), never open cut faces, which render as hollow shells.
8. **Report.** Method and tool first, then fits, scale assumption, deviation, checks and open problems. Walk the user through open problems one decision at a time, each with a marked image and multiple-choice answers labelled a1, a2, with a recommended answer when there is one (inside a project with an open-items rule: its list instead).
9. **File.** Only after the user approves, file with **publish-to-models**. The scan stays in the parts home, never in the models folder. Record the scan path, commit and build switches, and the tool (Made with) in the version's SUMMARY.md. Copy any finished, reusable new script into the user's shared tools folder only if the project asks for it (copy-in only, no secrets, no models).
10. No FEA until the user approves the geometry, unless they ask for it.

## Tool per step
| Step | Tool |
|---|---|
| Scan prep, scale, fitting, deviation | Python (residuals; Fusion has no fitting API) |
| Hard points, connecting features, edge breaks | Timeline owner (build123d or Fusion) |
| Wall, gap, hollow checks | BRep / Fusion Section Analysis |
| STEP export, renders | Either, into the job's working folder in the parts home |

The in-repo Xometry guide text is `docs/references/xometry-design-guide-cnc-machining-2025-04-16.md`; project CNC rules are in `docs/CNC-MACHINING-RULES.md`. The full PDF stays in the models folder (`references/`).
