---
name: publish-to-models
description: >-
  Use when a CAD part, assembly or scan-to-CAD job (or new revision) is
  finished and must be filed into the user's models home as a versioned,
  hash-verified folder.
---
## When to use
File into the user's single models home as a new versioned folder with SUMMARY.md, REVLOG.md, MADE-WITH.md, drawings, sources and intermediates, then hash-verify. Runs on the user's machine.

Models home (the only one): `[paths] models_dir` in the toolkit repo's `local.toml` (or `MODELS_DIR`). Empty means `<Desktop>/models`, which the repo's setup step resolves from the system's Desktop folder (cloud-synced Desktops included) and creates if missing. Never hard-code a user or cloud-drive path; if the folder can't be resolved, stop and ask the user. Never edit an existing rev folder. The job folder is renamed to `<subject>-rev<current>` when a new rev is filed. Deleting old versions follows step 7; never delete 3D scans.

The project's own rules (AGENTS.md, decision log, revision register) win over this skill wherever they differ.

**A repo with its own CAD rule wins over the models home.** If the project repo says where its CAD is filed (for example a rule in its decision log), file it there by that rule and don't publish it to the models home. The models home is for everything else.

## Where it runs
Publish straight from the user's machine into the models home, never through the agent's own computer. If that machine is offline, stop and tell the user. On Windows + WSL, write from WSL out to `/mnt/c/...`; never write through `\\wsl.localhost` paths from Windows. If a file must be staged, use a dedicated temp folder outside models (`<cad_staging>/<job>`, from `[paths] cad_staging` / `CAD_STAGING`); only that folder is ever removed.

## Sources and runs
Part build scripts live in the parts home (`HBCAD_PARTS_HOME`, default `~/cad-parts/<job>/src/`); copy the ones that built this rev into the rev's `src/`. Working outputs live in `~/cad-parts/<job>/runs/<stamp>/` and are not published, except the finished deliverables (final STEP, drawings, review views, final strength summary, SUMMARY.md). After a successful publish the run's regenerable outputs may be deleted; costly ones go to `~/cad-parts/_archive/<job>/`. Runs that belong to a rev deleted in step 7 are deleted with it. The kept previous rev's runs stay.

## Files others add are expected
Drawings, PDFs, photos or notes dropped into a job or rev folder are legitimate. Never delete, move, rename, overwrite or flag a file this run didn't write, and leave them out of checks. The only exception is deleting a superseded rev (step 7).

## Steps
1. Job folder. `<subject>-rev<current>`, for example `bracket-revD`, with the rev folders inside it. The subject is a short name with no date. Reuse that subject for the life of the job. `tools/rev.py` adds the next `rev<LETTER>` and renames the job folder to the new rev. An old `<subject>_<MMDD>` folder is renamed to this form the next time a rev is filed. Never edit files inside an existing rev folder. One source-of-truth assembly is filed from the newest part models; do not keep a second Fusion copy per rev.
2. Unchanged? Compare the new output model(s) and every file listed in the last rev's manifest. If everything matches, don't make a new rev; report "unchanged". If only drawings changed and fit, form and function are untouched, make a clerical rev (step 3). Different build switches or a different scan input always mean a new letter.
3. Next rev. In the models home the rev folder is `rev<LETTER>` (e.g. `revD`) inside `<subject>-rev<current>`. If the project has its own rules or record (its AGENTS.md, revision register), those win: in a project repo that keeps revs in its title block and register, the letter lives only there (no rev folder) and git history is the record.
   - Letters: A, B, C ... Z, then AA, AB ... Skip I, L, O and Q in every position, first and second letter alike (so ... AG, AH, AJ, AK, AM ...). Lookup table:
     1=A, 2=B, 3=C, 4=D, 5=E, 6=F, 7=G, 8=H, 9=J, 10=K, 11=M, 12=N, 13=P, 14=R, 15=S, 16=T, 17=U, 18=V, 19=W, 20=X, 21=Y, 22=Z, 23=AA, 24=AB, 25=AC, 26=AD, 27=AE, 28=AF, 29=AG, 30=AH.
   - A release is a merged PR that changed that model (moves and render- or trimetric-only PRs don't count) or, going forward where there is no PR (most models-home jobs), the user's explicit approval. Only releases use up a letter. A pending or unapproved candidate gets no letter until it is released; keep it in staging, not in a rev folder.
   - Brand-new model with no earlier folders: starts at A. Rev A is only for brand-new models.
   - Job already has `rev<LETTER>` folders: take the next letter after the highest one.
   - Job has old `rev<number>` folders: don't convert the numbers (many were iterations, not releases). Count the model's real releases in the repo history, skipping I, L, O and Q, and the next letter follows that count. For past history with no repo record, count the saved versions in which the model changed. List those releases as evidence in the revision register and the new SUMMARY.md. If both numbered and lettered folders exist, the lettered ones win: take the next letter after the highest letter. Example: a model with 7 counted releases is at G, so its next release is H.
   - Never rename or renumber old `rev<number>` folders. Count their releases first; once the new rev is filed they are deleted like any older rev (step 7).
   - Clerical rev (only for a drawing already released; an unreleased drawing keeps its counted letter): a drawing-only change that doesn't affect fit, form or function goes in `rev<LETTER>.<NN>` (e.g. `revD.01`, `revD.02`) under the current model letter. It holds only the new drawings, a SUMMARY.md and a manifest, never a model file. A changed model always means a new letter. Its SUMMARY.md points to the `rev<LETTER>` model folder and is the only place the clerical change is logged (it is not added to REVLOG.md).
   - Create the folder so the step fails if it already exists. If it fails, re-read the folders and recompute; never reuse a letter.
4. Inside the rev folder:
   - One assembly STEP at the top (not in clerical revs), plus STL only when a print job needs one. A job that is a single part is that one STEP and has no `Parts` folder. The STEP copy keeps the same tree as the source (parts, subassemblies, bodies, external files), whatever tool made the source.
   - `Parts\`: every external part and subassembly, one file each. A made part is one solid. A piece that installs in its own step (legs that cover screws, for example) is its own part. Several pieces are an assembly of linked parts, never one fused body. Fusion: each of these is a linked component (right-click > Open), in a Parts folder beside the assembly.
   - `drawings\`: PDF, DXF, SVG
   - `src\`: build scripts (leave it out if there are none)
   - `reference\`: intermediates, native files (.f3d, .FCStd), bought-part STEPs, OEM/reference STEPs, and the scan mesh (or a path to it if it's huge; raw scans stay out of public repos)
   - review views and preview PNGs (smooth-shaded, no mesh lines). Section views are capped (closed-surface clipping, solid cut faces), never open cut faces, which render as hollow shells.
   - `SUMMARY.md`: job, rev letter (and clerical decimal, if any), date, source path, primary file(s), made with, mass (with material) and bounding box, check results, what changed, open issues, approval status (FEA not run until approved), and the evidence for the letter (step 3). Scan-to-CAD jobs also give the scan, the pipeline or script commit, the build script and its switches, and deviation from the scan if measured.
   - `MADE-WITH.md`: the tool that made each model file (e.g. Fusion, build123d, FreeCAD, CadQuery), plus a version if known. Mark anything you can't confirm as "unconfirmed". Whenever the model is shown in chat, put the same tool name in parentheses after it so the two never disagree. If the project has a register with a Made-with column, update it together with MADE-WITH.md.
   - Rev log: one cumulative changelog per model, one row per release (Rev, Description, By, Date). One model in the folder: `REVLOG.md`; several: one `<part no>.REVLOG.md` per model (what the drawing tool reads). A new rev folder copies the old rows forward and adds one. Dates are dd/mm/yy: day first, then month, then 2-digit year (e.g. 17/10/26 = 17 October 2026). Rev A's description is "Initial". Clerical revs aren't listed (see step 3). The drawing's Rev log table is generated from it (newest rows shown, oldest drop off first).
   - bought parts: supplier's part number on the BOM plus a cited datasheet or the maker's own page and the key values the design uses, looked up from primary sources (`skills/primary-source-spec-check`); anything no source confirms is marked TBD. The bought-part STEP is the supplier's official CAD model. List each one in SUMMARY.md under `## Bought parts` as `- name: reference/<maker file>`. A missing or empty maker file fails the release check. Every part model, purchased and fabricated, is saved in a `parts/` folder inside the project; the published maker STEP goes in `reference\`. Designs with electronics also file the plan document (wiring tables, schematic, electronics BOM).
   - Fasteners from Dan's SR Fasteners add-in stay as bodies inside the assembly or subassembly (the only bodies that are not their own file). Fasteners that add-in does not offer are files in `Parts\`. If the STEP writer cannot keep SR fastener bodies inside the assembly, separate files are allowed; SUMMARY.md must say they are separate files.
   - `MANIFEST.sha256`: every file this run wrote, including SUMMARY.md, but not the manifest itself; written on the user's machine after the copy
5. Copy, confirm each file landed (cloud-synced online-only or locked files can fail; let them download, retry if locked), then SHA-256 check every copied file; on Windows + WSL re-check the hashes from Windows, since sync clients can lag. Stop on any mismatch.
6. Copy vs move. From a live project folder always copy. Move only when the user asks; then remove only manifest sources whose hash matched. A source in a git repo is removed with a normal commit via safe-repo-preflight.
7. Retention (Daniel, 2026-11-20; supersedes 2026-11-04). Keep two model letters: the newest and the one before it, plus the clerical decimals of those letters (a clerical folder has drawings only, so its model rev stays). Run the release check (step 9) first. Only after step 5 and step 9 pass, run `tools/rev.py <subject> --prune`. It deletes older `rev<LETTER>`, their clerical decimals, and old numeric `rev<N>` folders. It does not delete a folder that contains a 3D scan (`.ply`, `.e57`, `.pts`, `.xyz`, `.las`, `.laz`). Then delete the `~/cad-parts/<job>/runs/` folders that belong to a deleted rev. Regenerate a kept rev's MANIFEST.sha256 if a file was removed from it. Screenshots live in the kept revs (drawings PDF/DXF/SVG are not screenshots). The kept revs' REVLOG.md and SUMMARY.md carry the history. Real changes always go in a new rev, never into an existing one.
8. Folder notes: run `.venv/bin/python tools/folder_notes.py` so a new job folder, and its parts-home `<job>/`, `src/` and `runs/`, each get a README.md from `templates/notes/` when one is missing. Never edit an existing README.
9. Release check: `.venv/bin/python tools/checks/release_structure.py <rev-folder>`. It fails a made part with more than one solid, a bought part with no maker model, a STEP tree that does not match `Parts\` (SR fastener names are ignored), or a STEP path that points at an older rev. Fix and re-file; do not edit the previous rev.
10. Report the rev path, the files and the check result.

## Fusion checklist
This repo cannot open a Fusion document, so these are not in `release_structure.py`. Confirm them before filing:
- Each part and subassembly is a linked component (right-click > Open), not a body fused into the assembly.
- A piece that installs in its own step is its own part.
- SR Fasteners screws, nuts and washers are bodies inside the assembly. Any other fastener is a file in Parts.
- One Fusion assembly and one parts folder, updated in place from the newest parts. No per-rev copy of that assembly.
- Each link is the newest version of that part.

## Notes
- Other tools find "the part" through SUMMARY/MANIFEST, never "whatever's in the folder".
- The model drives the letter, and the drawings in a rev folder always carry the same letter as the model in it (clerical revs: the parent letter plus the decimal, e.g. D.01). Workflow: redline the drawing, then change the model, then regenerate the drawing.
- File names: follow the project's rules. If they say no rev letters in file names, the letter lives only in the title block, the register and (in the models home) the folder name. Otherwise file names may carry the letter if useful.
- Filing into a project repo also needs whatever its AGENTS.md asks for (e.g. a README row, a trimetric view).
