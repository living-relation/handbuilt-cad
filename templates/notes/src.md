# @JOB@ / src

Owner: handbuilt-cad layout (setup.sh, tools/folder_notes.py). Agent note.

- The build scripts of this part: the editable source, plus its inputs, params, interface JSON and notes. Edit a named size, rebuild.
- Run with the handbuilt-cad venv from this folder, e.g. `$CAD_HOME/.venv/bin/python <part>.py`. Part scripts find other parts and tools through handbuilt-cad `tools/paths.py`.
- Working outputs go to `../runs/<YYYYMMDD-HHMM>/`, never here.
- Finished results are published with publish-to-models to the paired models folder: `@MODELS@`.
- Old versions: `../../_archive/@JOB@/`.
