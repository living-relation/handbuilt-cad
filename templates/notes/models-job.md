# @JOB@

Owner: handbuilt-cad (https://github.com/living-relation/handbuilt-cad). Note written by `tools/folder_notes.py` (setup and publish-to-models), add-only.

Used by: handbuilt-cad's publish-to-models skill, which adds new revs here by this folder's name.
Deleting or moving this folder breaks publish-to-models. It holds AP242 STEP and drawings only (`<part>-rev<LETTER>`). Scripts and runs stay in the parts home. Never edit an existing rev file. Keep each part's newest rev and the one before it.

- Part: `@PART@`
- Paired parts-home folder (build scripts and runs, WSL/Linux): @PAIR@

## Revs
@REVS@

New revs: publish-to-models (next letter for that part and its `<part>-rev<LETTER>.md` card). AP242 STEP only.
