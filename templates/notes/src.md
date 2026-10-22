# @JOB@ / src

Owner: handbuilt-cad (https://github.com/living-relation/handbuilt-cad). Note written by `tools/folder_notes.py` (setup and publish-to-models), add-only.

Used by: handbuilt-cad's tools (`tools/paths.py`) and publish-to-models, which read the build scripts here.
Deleting, moving or renaming this folder breaks those tools and loses the editable source of this part.

- The build scripts of this part: the editable source, plus its inputs, params, interface JSON and notes. Edit a named size, rebuild.
- Run with the handbuilt-cad venv from this folder, e.g. `$CAD_HOME/.venv/bin/python <part>.py`. Part scripts find other parts and tools through handbuilt-cad `tools/paths.py`.
- Working outputs go to `../runs/<YYYYMMDD-HHMM>/`, never here.
- Finished results are published with publish-to-models to the paired models folder: `@MODELS@`.
- Old versions: `../../_archive/@JOB@/`.
