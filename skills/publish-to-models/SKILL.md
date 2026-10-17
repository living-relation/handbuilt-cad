---
name: publish-to-models
description: >-
  Use when a CAD part, assembly or scan-to-CAD job is finished (or a new
  revision is ready) and must be filed into Daniel's single models home as a new
  versioned folder with SUMMARY.md, drawings, sources and intermediates, then
  hash-verified. Runs on Daniel's PC.
---
Models home (the only one): `$MODELS_DIR` if set, else `C:\Users\danie\.personal OneDrive\OneDrive\Desktop\models` (from WSL: `"/mnt/c/Users/danie/.personal OneDrive/OneDrive/Desktop/models"`, quoted). Add-only: never archive, move, rename, clean or delete anything already in it.

## Where it runs
Publish straight from WSL/DansPC into models, never through the bot's own computer. If DansPC is offline, stop and tell Daniel. Always write from WSL out to `/mnt/c`; never write through `\\wsl.localhost` paths from Windows. If a file must be staged, use a dedicated temp folder outside models (e.g. `C:\Users\danie\_staging\<job>`); only that folder is ever removed.

## Files others add are expected
Drawings, PDFs, photos or notes dropped into a job or rev folder are legitimate. Never delete, move, rename, overwrite or flag a file this run didn't write, and leave them out of checks.

## Steps
1. Job folder. Existing folders are `<job>_<MMDD>` (e.g. `knuckle_billet_al_1010`); keep them as they are. Reuse the existing folder for the same job even on a later day; MMDD is the first publish date. New multi-assembly projects use `<project>_<assembly>_<MMDD>` (e.g. `st185_csb3_1015`). If the same name exists from a different year, use `_<YYMMDD>`.
2. Unchanged? Compare the new output model(s) and every file listed in the last rev's manifest. If everything matches, don't make a new rev; report "unchanged". If only drawings changed and fit, form and function are untouched, make a clerical rev (step 3). Different build switches (e.g. HD20=1 vs HD16B=1) or a different scan input always mean a new letter.
3. Next rev. In the models home the model's rev letter names the folder: `rev<LETTER>`, e.g. `revD`. If the project has its own rules or record (e.g. st185 AGENTS.md / DRAWING-REVS.md), those win: in a project repo that keeps revs in its title block and register, the letter lives only there (no rev folder) and git history is the record.
   - Letters: A, B, C ... Z, then AA, AB ... Skip I, L, O and Q in every position, first and second letter alike (so ... AG, AH, AJ, AK, AM ...). Lookup table:
     1=A, 2=B, 3=C, 4=D, 5=E, 6=F, 7=G, 8=H, 9=J, 10=K, 11=M, 12=N, 13=P, 14=R, 15=S, 16=T, 17=U, 18=V, 19=W, 20=X, 21=Y, 22=Z, 23=AA, 24=AB, 25=AC, 26=AD, 27=AE, 28=AF, 29=AG, 30=AH.
   - A release is a merged PR that changed that model (moves and render- or trimetric-only PRs don't count) or, going forward where there is no PR (most models-home jobs), Daniel's explicit approval. Only releases use up a letter. A pending or unapproved candidate (e.g. knuckle hdP3) gets no letter until it is released; keep it in staging, not in a rev folder.
   - Brand-new model with no earlier folders: starts at A.
   - Job already has `rev<LETTER>` folders: take the next letter after the highest one.
   - Job has old `rev<number>` folders: don't convert the numbers (many were iterations, not releases). Count the model's real releases in the repo history, skipping I, L, O and Q, and the next letter follows that count. For past history with no repo record, count the saved versions in which the model changed. List those releases as evidence in the revision register and the new SUMMARY.md. Rev A is only for brand-new models. If both numbered and lettered folders exist, the lettered ones win: take the next letter after the highest letter.
   - Old `rev<number>` folders stay exactly as they are (add-only). Never rename or renumber them.
   - Clerical rev (only for a drawing already released; an unreleased drawing keeps its counted letter): a drawing-only change that doesn't affect fit, form or function goes in `rev<LETTER>.<NN>` (e.g. `revD.01`, `revD.02`) under the current model letter. It holds only the new drawings, a SUMMARY.md and a manifest, never a model file. A changed model always means a new letter. Its SUMMARY.md points to the `rev<LETTER>` model folder and is the only place the clerical change is logged (it is not added to REVLOG.md).
   - Create the folder so the step fails if it already exists. If it fails, re-read the folders and recompute; never reuse a letter.
4. Inside the rev folder:
   - primary model file(s) at the top (not in clerical revs): STEP only, plus STL only when a print job needs one
   - `drawings\`: PDF, DXF, SVG
   - `src\`: build scripts (leave it out if there are none)
   - `reference\`: intermediates, native files (.f3d, .FCStd), bought-part STEPs, OEM/reference STEPs, and the scan mesh (or a path to it if it's huge; raw scans stay off GitHub)
   - review views and preview PNGs
   - `SUMMARY.md`: job, rev letter (and clerical decimal, if any), date, source path, primary file(s), made with, mass (with material) and bounding box, check results, what changed, open issues, approval status (FEA not run until approved), and the evidence for the letter (step 3). Scan-to-CAD jobs also give the scan, the Fairsolid commit, the build script and its switches, and deviation from the scan if measured.
   - `MADE-WITH.md`: the tool that made each model file (e.g. Fusion, build123d, fairsolid, CadQuery), plus a version if known. Mark anything you can't confirm as "unconfirmed". Whenever the model is shown in chat, put the same tool name in parentheses after it so the two never disagree. If the project has a register with a Made-with column, update it together with MADE-WITH.md.
   - Rev log: one cumulative changelog per model, one row per release (Rev, Description, By, Date). One model in the folder: `REVLOG.md`; several: one `<part no>.REVLOG.md` per model (what the drawing tool reads). A new rev folder copies the old rows forward and adds one. Dates are dd/mm/yy: day first, then month, then 2-digit year (e.g. 17/10/26 = 17 October 2026). Rev A's description is "Initial". Clerical revs aren't listed (see step 3). The drawing's Rev log table is generated from it.
   - bought parts: part numbers only, no web lookups
   - `MANIFEST.sha256`: every file this run wrote, including SUMMARY.md, but not the manifest itself; written from WSL after the copy
5. Copy, confirm each file landed (OneDrive online-only or locked files can fail under /mnt/c; let them download, retry if locked), then SHA-256 check every copied file; re-check the hashes from Windows, since OneDrive can lag. Stop on any mismatch.
6. Copy vs move. From a live project folder (e.g. `C:\projects\active\...`) always copy. Move only when Daniel asks; then remove only manifest sources whose hash matched. A source in a git repo is removed with a normal commit via safe-repo-preflight.
7. Old revs are add-only: a missing SUMMARY.md or MANIFEST may be added, nothing existing is changed. Real changes go in a new rev.
8. Report the rev path, the files and the check result.

## Notes
- Other tools find "the part" through SUMMARY/MANIFEST, never "whatever's in the folder".
- The model drives the letter, and the drawings in a rev folder always carry the same letter as the model in it (clerical revs: the parent letter plus the decimal, e.g. D.01).
- st185 parts never carry rev letters in file names, whether filed in the st185 repo or in the models home. In the st185 repo the letter is only in the title block and DRAWING-REVS.md; in the models home it's also the folder name. Outside st185, file names may carry the letter if useful.
- Filing into st185 also needs a cad/README.md row and a trimetric, per its AGENTS.md.
