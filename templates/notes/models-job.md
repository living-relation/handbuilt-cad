# @JOB@

Owner: handbuilt-cad (https://github.com/living-relation/handbuilt-cad). Note written by `tools/folder_notes.py` (setup and publish-to-models), add-only.

Used by: handbuilt-cad's publish-to-models skill, which adds new revs here by this folder's name.
Deleting or moving this folder breaks publish-to-models. It holds version folders `rev<LETTER>/` with AP242 STEP and drawings only. Scripts and runs stay in the parts home. Never edit an existing version. Keep the 2 latest versions; never delete 3D scans.

- Part: `@PART@`
- Paired parts-home folder (build scripts and runs, WSL/Linux): @PAIR@

## Revs
@REVS@

New versions: publish-to-models (`tools/rev.py` makes the next `rev<LETTER>/` and its SUMMARY.md). AP242 STEP only.
