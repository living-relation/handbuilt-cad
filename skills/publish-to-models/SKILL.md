---
name: publish-to-models
description: >-
  Use when a CAD part, assembly or scan-to-CAD job (or new revision) is
  finished and must be filed into the user's models home as a versioned,
  hash-verified folder.
---
## When to use
File STEP and drawings into the user's models home. One AP242 STEP per designed part rev, plus a short data card. Runs on the user's machine.

Models home (the only one): `[paths] models_dir` in the toolkit repo's `local.toml` (or `MODELS_DIR`). Empty means `<Desktop>/models`. Never hard-code a user path. The job folder is `<subject>_<MMDD>` and is not a rev. Never edit an existing part's rev file. Scripts, runs, scans and working notes stay in the parts home (`HBCAD_PARTS_HOME`, default `~/cad-parts/<job>/`, `tools/paths.py`).

The project's own rules (AGENTS.md, decision log, revision register) win over this skill wherever they differ.

**A repo with its own CAD rule wins over the models home.** If the project repo says where its CAD is filed (for example a rule in its decision log), file it there by that rule and don't publish it to the models home. The models home is for everything else.

## Where it runs
Publish straight from the user's machine into the models home, never through the agent's own computer. If that machine is offline, stop and tell the user. On Windows + WSL, write from WSL out to `/mnt/c/...`; never write through `\\wsl.localhost` paths from Windows. If a file must be staged, use a dedicated temp folder outside models (`<cad_staging>/<job>`, from `[paths] cad_staging` / `CAD_STAGING`); only that folder is ever removed.

## Sources and runs
Part build scripts live in the parts home (`~/cad-parts/<job>/src/`). Working outputs live in `~/cad-parts/<job>/runs/<stamp>/`. Do not copy either into the models folder. After a successful publish, regenerable run outputs may be deleted; costly ones go to `~/cad-parts/_archive/<job>/`. Agents clean up their own leftovers there.

## Files others add are expected
Drawings dropped into a job folder are legitimate. Do not add scripts, runs, scans, or working notes. Never edit a rev file this run did not just create. The only deletion is an older rev of that part (step 7).

## Steps
1. Job folder `<subject>_<MMDD>` (first publish date). Reuse it. Parts in it may be at different revs. `tools/rev.py --part <name>` writes the next `<part>-rev<LETTER>.md` card and does not touch other parts. Never edit an existing rev file.
2. Unchanged? Compare the new output model(s) and every file listed in the last rev's manifest. If everything matches, don't make a new rev; report "unchanged". If only drawings changed and fit, form and function are untouched, make a clerical rev (step 3). Different build switches or a different scan input always mean a new letter.
3. Next rev is per part: `<part>-rev<LETTER>` (clerical `<part>-rev<LETTER>.<NN>`, drawing and card only). If the project has its own revision register, those rules win.
   - Letters: A, B, C ... Z, then AA, AB ... Skip I, L, O and Q in every position, first and second letter alike (so ... AG, AH, AJ, AK, AM ...). Lookup table:
     1=A, 2=B, 3=C, 4=D, 5=E, 6=F, 7=G, 8=H, 9=J, 10=K, 11=M, 12=N, 13=P, 14=R, 15=S, 16=T, 17=U, 18=V, 19=W, 20=X, 21=Y, 22=Z, 23=AA, 24=AB, 25=AC, 26=AD, 27=AE, 28=AF, 29=AG, 30=AH.
   - A release is a merged PR that changed that model (moves and render- or trimetric-only PRs don't count) or, going forward where there is no PR (most models-home jobs), the user's explicit approval. Only releases use up a letter. A pending or unapproved candidate gets no letter until it is released; keep it in staging, not in a rev folder.
   - Brand-new model with no earlier folders: starts at A. Rev A is only for brand-new models.
   - The part already has `<part>-rev<LETTER>` files: take the next letter after the highest one for that part only.
   - Old numeric `rev<N>` folders are not converted. Count real releases and pass `--releases N` or `--letter X`.
   - Clerical rev: `<part>-rev<LETTER>.<NN>.md` and the new drawing only. Not listed in REVLOG.md. A model change takes the next letter.
4. Publish only these files into the job folder:
   - One AP242 STEP per designed part or assembly: `<part>-rev<LETTER>.step`. Schema `AP242DIS`. No .f3d, STL, or second copy. Fusion exports to STEP; the .f3d stays in Fusion's cloud. Fusion's own STEP export may bundle every part into one file (unverified); convert that with `tools/step_release.py` before filing.
   - Assembly: the root STEP references each part or subassembly as `Parts/<stem>.stp` (AP242 external references, resolvable on reopen). Write it with `tools/step_release.py`. A made part is one solid. A piece that installs in its own step is its own part. SR fastener bodies may stay inside the assembly STEP; other fasteners are files in `Parts/`.
   - Drawings: `<part>-rev<LETTER>.pdf` (DXF, SVG). Same letter as that part.
   - Data card: `<part>-rev<LETTER>.md` (rev, what changed, made-with). Bought parts listed under `## Bought parts` as `- name: reference/<maker>.stp`.
   - `reference/`: bought maker STEP only, no rev letter. Re-save it as AP242 if the maker file is another schema.
   - Do not publish `src/`, `runs/`, scripts, scans, or review PNGs.
   - Rev log: `<part>.REVLOG.md` beside that part (Rev, Description, By, Date dd/mm/yy). Rev A is "Initial". Clerical revs are not listed. The drawing reads this file.
   - Bought parts: maker's AP242 STEP in `reference/`, supplier part number on the BOM (`skills/primary-source-spec-check`). A missing maker file fails the check.
5. Copy, confirm each file landed (cloud-synced online-only or locked files can fail; let them download, retry if locked), then SHA-256 check every copied file; on Windows + WSL re-check the hashes from Windows, since sync clients can lag. Stop on any mismatch.
6. Copy vs move. From a live project folder always copy. Move only when the user asks; then remove only manifest sources whose hash matched. A source in a git repo is removed with a normal commit via safe-repo-preflight.
7. Retention is per part (Daniel, 2026-11-20). After the release check passes, `tools/rev.py <subject> --prune` deletes only files older than that part's newest letter and the one before it (clerical decimals of those letters stay). It does not delete the job folder or `reference/`. Real changes always go in a new rev file, never into an existing one.
8. Folder notes: run `.venv/bin/python tools/folder_notes.py` so a new job folder, and its parts-home `<job>/`, `src/` and `runs/`, each get a README.md from `templates/notes/` when one is missing. Never edit an existing README.
9. Release check: `.venv/bin/python tools/checks/release_structure.py <job-folder>`. It fails a non-AP242 STEP, a non-STEP model, a duplicate STEP, a multi-solid made part, a bought part with no maker file, an assembly that embeds parts instead of referencing `Parts/`, a reference to an older rev of that part, or a script, run, or scan. Fix and re-file; do not edit the previous rev.
10. Report the rev path, the files and the check result.

## Fusion checklist
This repo cannot open a Fusion document, so these are not in `release_structure.py`. Confirm them before filing:
- Each part and subassembly is a linked component (right-click > Open), not a body fused into the assembly.
- A piece that installs in its own step is its own part.
- SR Fasteners screws, nuts and washers are bodies inside the assembly. Any other fastener is a file in Parts.
- One Fusion assembly and one parts folder, updated in place from the newest parts. No per-rev copy of that assembly.
- Each link is the newest version of that part.

## Notes
- Find a part by its `<part>-rev<LETTER>` file, not by "whatever is in the folder".
- The drawing letter matches that part (clerical: D.01). Redline the drawing, then change the model, then regenerate the drawing.
- In the models home the rev letter is in the file name.
- Filing into a project repo also needs whatever its AGENTS.md asks for (e.g. a README row, a trimetric view).
