# @JOB@ (parts home)

Owner: handbuilt-cad (https://github.com/living-relation/handbuilt-cad). Note written by `tools/folder_notes.py` (setup and publish-to-models), add-only.

Used by: handbuilt-cad's tools (`tools/paths.py`, `quick_fea.py --job`) and publish-to-models, which find this job by its folder name.
Deleting, moving or renaming this folder breaks those tools and loses this part's build scripts.

- `src/`: build scripts, inputs, params, notes (the editable source of the part).
- `runs/<YYYYMMDD-HHMM>/`: working outputs, regenerable.
- Paired models folder (finished deliverables, publish-to-models): `@MODELS@`.
- History: `../_archive/@JOB@/`.
