---
name: publish-to-models
description: >-
  Use when a CAD part, assembly or scan-to-CAD job (or new version) is
  finished and must be filed into the user's models home as a new,
  hash-verified version folder.
---
## When to use
File usable AP242 STEP models and drawings into the user's models home as a new version folder. Runs on the user's machine.

Models home (the only one): `[paths] models_dir` in the toolkit repo's `local.toml` (or `MODELS_DIR`). Empty means `<Desktop>/models`, which the repo's setup step resolves from the system's Desktop folder (cloud-synced Desktops included) and creates if missing. Never hard-code a user or cloud-drive path; if the folder can't be resolved, stop and ask the user. Scripts, runs, scans and working notes stay in the parts home (`HBCAD_PARTS_HOME`, default `~/cad-parts/<job>/`, `tools/paths.py`).

The project's own rules (AGENTS.md, decision log, revision register) win over this skill wherever they differ.

**A repo with its own CAD rule wins over the models home.** If the project repo says where its CAD is filed (for example a rule in its decision log), file it there by that rule and don't publish it to the models home. The models home is for everything else.

## Models home housekeeping
- The models home holds usable models and drawings only, plus each version's `SUMMARY.md` and `REVLOG.md`. Never put backup ZIPs, purge copies, or copies of things the user told you to delete there; delete such agent-made leftovers instead of archiving them in the models home.
- Never delete or alter a 3D scan, anywhere. Scans live in the parts home.
- Existing job folder names are kept as they are. Never reset or invent a rev letter. Before reorganising existing jobs (only when the user asks), verify each version from its SUMMARY.md, REVLOG and actual files, then hash-check the unchanged contents afterward. Don't merge projects or overwrite a destination.
- Offer every finished model for filing. A filed assembly includes every part and subassembly STEP it references.

## Where it runs
Publish straight from the user's machine into the models home, never through the agent's own computer. If that machine is offline, stop and tell the user. On Windows + WSL, write from WSL out to `/mnt/c/...`; never write through `\\wsl.localhost` paths from Windows. If a file must be staged, stage it in the parts home (`~/cad-parts/<job>/runs/<stamp>/`), never in the models folder. Always delete your own scratch and test files when finished; don't touch the user's unrelated files.

## Sources and runs
Part build scripts live in the parts home (`~/cad-parts/<job>/src/`). Working outputs live in `~/cad-parts/<job>/runs/<stamp>/`. Do not copy either into the models folder. After a successful publish, regenerable run outputs may be deleted; costly ones go to `~/cad-parts/_archive/<job>/`. Agents clean up their own leftovers there.

## Files others add are expected
Drawings dropped into a job folder are legitimate. Do not add scripts, runs, scans, or working notes. Never edit a version folder this run did not just create. Unless the user asks for a cleanup, don't delete, move or overwrite files you didn't write. The only routine deletion is an assembly version older than the 2 latest (step 7).

## Steps
1. Job folder: reuse the existing one for this subject, whatever its name. A new job folder is the plain subject. `tools/rev.py <job>` makes the next version folder `rev<LETTER>/` with its `SUMMARY.md`, and fails if it already exists; then re-read the folder and recompute, never reuse a letter.
2. Unchanged? Compare the new output model(s) and every file listed in the last version's SUMMARY.md. If everything matches, don't make a new version; report "unchanged". If only drawings changed and fit, form and function are untouched, make a clerical rev (step 3). Different build switches or a different scan input always mean a new letter.
3. Next letter (the model drives it; drawings carry the same letter). If the project has its own revision register, those rules win.
   - Letters: A, B, C ... Z, then AA, AB ... Skip I, L, O and Q in every position, first and second letter alike (so ... AG, AH, AJ, AK, AM ...). Lookup table:
     1=A, 2=B, 3=C, 4=D, 5=E, 6=F, 7=G, 8=H, 9=J, 10=K, 11=M, 12=N, 13=P, 14=R, 15=S, 16=T, 17=U, 18=V, 19=W, 20=X, 21=Y, 22=Z, 23=AA, 24=AB, 25=AC, 26=AD, 27=AE, 28=AF, 29=AG, 30=AH.
   - A release is a merged PR that changed that model (moves and render- or trimetric-only PRs don't count) or, going forward where there is no PR (most models-home jobs), the user's explicit approval. Only releases use up a letter. A pending or unapproved candidate gets no letter until it is released; keep it in the parts home, not in the models folder.
   - Rev A is only for brand-new models; existing history is never reset to A. Otherwise take the next letter after the highest `rev<LETTER>` folder.
   - Old numeric `rev<N>` folders are not converted. Count real releases and pass `--releases N` or `--letter X`.
   - Clerical rev: `rev<LETTER>.<NN>/` with the new drawings and SUMMARY.md only, pointing to its parent letter. Not listed in REVLOG.md. A model change takes the next letter.
4. Publish only these files into the version folder:
   - The assembly (or single part) as one AP242 STEP at the version root. Schema `AP242DIS`. No STL or second copy. Fusion exports to STEP; file the .f3d beside it too when it is needed to keep working (AGENTS.md rule 13). Fusion's own STEP export may bundle every part into one file (unverified); convert that with `tools/step_release.py` before filing.
   - `Parts/`: every part and subassembly as its own AP242 STEP, referenced from the assembly STEP as `Parts/<part>.stp` (AP242 external references, resolvable on reopen). Write it with `tools/step_release.py`. A made part is one solid. A piece that installs in its own step is its own part. SR fastener bodies may stay inside the assembly STEP; other fasteners are files in `Parts/`.
   - Bought parts: the maker's STEP in `Parts/` (re-saved as AP242 if the maker file is another schema), listed in SUMMARY.md under `## Bought parts` as `- name: Parts/<maker>.stp`, with the supplier part number on the BOM, a cited datasheet or maker page and the key values used; unconfirmed values are TBD (`skills/primary-source-spec-check`). Fasteners are real fastener-tool models, never placeholders. A missing maker file fails the check.
   - `drawings/`: the assembly-only package (`skills/cad-drawing`) and, for assemblies with 3D-printed parts, the one-page printed parts list. No separate part PDFs or DXFs.
   - `SUMMARY.md` (from `tools/rev.py`): rev, what changed, made with (tool and version if known, else "unconfirmed"), source path, mass, material and bounding box, files, check results, approval and rev evidence, open issues, bought parts.
   - `REVLOG.md` beside the assembly STEP, cumulative: copy forward old rows, then add the new one (Rev, Description, By, Date dd/mm/yy). Rev A is "Initial". Clerical revs are not listed. The drawing reads this file.
   - Do not publish `src/`, `runs/`, scripts, scans, renders, or other working notes.
5. Copy, confirm each file landed (cloud-synced online-only or locked files can fail; let them download, retry if locked), then SHA-256 check every copied file; on Windows + WSL re-check the hashes from Windows, since sync clients can lag. Stop on any mismatch.
6. Copy vs move. From a live project folder always copy. Move only when the user asks; then remove only sources whose hash matched. A source in a git repo is removed with a normal commit via safe-repo-preflight.
7. Retention: keep the 2 latest versions of each assembly (the user, 2026-11-20). After the new version is filed, hash-checked and passes step 9, run `tools/rev.py <job> --prune` to list older version folders, then `--prune --apply` to delete them with the parts inside them. Clerical decimals go with their letter. A folder holding a 3D scan is never deleted. Real changes always go in a new version, never into an existing one.
8. Folder notes: run `.venv/bin/python tools/folder_notes.py` so a new job folder, and its parts-home `<job>/`, `src/` and `runs/`, each get a README.md from `templates/notes/` when one is missing. Never edit an existing README.
9. Release check: `.venv/bin/python tools/checks/release_structure.py <job-folder>`. It fails more than two model versions, a non-AP242 STEP, a non-STEP model, a duplicate STEP, a multi-solid made part, a bought part with no maker file, an assembly that embeds parts or references a missing one, a part in `Parts/` no assembly uses, or a script, run, scan or working note. Fix and re-file; do not edit the previous version.
10. Report the version path, the files and the check result, and offer the complete finished assembly (all part and subassembly STEPs) for filing.

## Fusion checklist
This repo cannot open a Fusion document, so these are not in `release_structure.py`. Confirm them before filing:
- Each part and subassembly is a linked component (right-click > Open), not a body fused into the assembly.
- A piece that installs in its own step is its own part.
- SR Fasteners screws, nuts and washers are bodies inside the assembly. Any other fastener is a file in Parts.
- One Fusion assembly and one parts folder, updated in place from the newest parts. No per-version copy of that assembly.
- Each link is the newest version of that part.

## Notes
- Find the current model by the highest `rev<LETTER>` folder in the job, not by "whatever is in the folder".
- The drawing letter matches the model (clerical: D.01). Redline the drawing, then change the model, then regenerate the drawing.
- Whenever a model is shown in chat, put its tool in parentheses after it, e.g. "<part> Rev F (build123d)".
- Filing into a project repo also needs whatever its AGENTS.md asks for (e.g. a README row, a trimetric view).
