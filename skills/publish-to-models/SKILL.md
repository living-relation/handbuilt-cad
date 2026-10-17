---
name: publish-to-models
description: >-
  Use when a CAD part, assembly or scan-to-CAD job is finished (or a new
  revision is ready) and must be filed into the owner's single models home as a new
  versioned folder with SUMMARY.md, drawings, sources and intermediates, then
  hash-verified. Runs on the CAD workstation.
---
Models home (the only one): `$MODELS_DIR` (required; setup creates `<Desktop>/models` and prints the value). If it isn't set, stop and ask; never guess a path. Quote it in WSL, since Desktop paths often contain spaces. Add-only: never archive, move, rename, clean or delete anything already in it.

## Where it runs
Publish straight from WSL on the CAD workstation into models, never through an agent's own computer. If it is offline, stop and tell the owner. Always write from WSL out to `/mnt/c`; never write through `\\wsl.localhost` paths from Windows. If a file must be staged, use a dedicated temp folder outside models (e.g. `$CAD_STAGING/<job>`); only that folder is ever removed.

## Files others add are expected
Drawings, PDFs, photos or notes dropped into a job or rev folder are legitimate. Never delete, move, rename, overwrite or flag a file this run didn't write, and leave them out of checks.

## Steps
1. Job folder. Existing folders are `<job>_<MMDD>` (e.g. `bracket_1010`); keep them as they are. Reuse the existing folder for the same job even on a later day; MMDD is the first publish date. New multi-assembly projects use `<project>_<assembly>_<MMDD>` (e.g. `car_enclosure_1015`). If the same name exists from a different year, use `_<YYMMDD>`.
2. Unchanged? Compare the new output model(s) and every file listed in the last rev's manifest. If everything matches, don't make a new rev; report "unchanged". Different build switches (e.g. HD20=1 vs HD16B=1) or a different scan input always mean a new rev.
3. Next rev. Count only folders named exactly `rev<number>`, use highest + 1, and create it so it fails if it already exists; on failure, retry N+1.
4. Inside revN:
   - primary model file(s) at the top
   - `drawings\`: PDF, DXF, SVG
   - `src\`: build scripts (leave it out if there are none)
   - `reference\`: intermediates, native files (.f3d, .FCStd), bought-part STEPs, OEM/reference STEPs, and the scan mesh (or a path to it if it's huge; raw scans stay off GitHub)
   - review views and preview PNGs
   - `SUMMARY.md`: job, rev, date, source path, primary file(s), mass (with material) and bounding box, check results, what changed, open issues, approval status (FEA not run until approved). Scan-to-CAD jobs also give the scan, the scan-pipeline (`pipelines/fairsolid`) commit, the build script and its switches, and deviation from the scan if measured.
   - bought parts: part numbers only, no web lookups
   - `MANIFEST.sha256`: every file this run wrote, including SUMMARY.md, but not the manifest itself; written from WSL after the copy
5. Copy, confirm each file landed (OneDrive online-only or locked files can fail under /mnt/c; let them download, retry if locked), then SHA-256 check every copied file; re-check the hashes from Windows, since OneDrive can lag. Stop on any mismatch.
6. Copy vs move. From a live project folder (e.g. `C:\projects\active\...`) always copy. Move only when the owner asks; then remove only manifest sources whose hash matched. A source in a git repo is removed with a normal commit via safe-repo-preflight.
7. Old revs are add-only: a missing SUMMARY.md or MANIFEST may be added, nothing existing is changed. Real changes go in a new rev.
8. Report the rev path, the files and the check result.

## Notes
- Other tools find "the part" through SUMMARY/MANIFEST, never "whatever's in the folder".
