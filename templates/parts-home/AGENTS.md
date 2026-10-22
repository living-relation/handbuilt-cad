# cad-parts (owner: handbuilt-cad)

Created by handbuilt-cad (https://github.com/living-relation/handbuilt-cad) setup.

Used by: handbuilt-cad's tools (`tools/paths.py`, `quick_fea.py --job`, `folder_notes.py`) and its `publish-to-models` skill. They find it through HBCAD_PARTS_HOME.
Deleting, moving or renaming this folder breaks those tools and loses the part build scripts kept here.

- `<job>/src/` : part build scripts, inputs, params, interface JSON, notes (the editable source of each part). Job names match the models folder.
- `<job>/runs/<YYYYMMDD-HHMM>/` : working outputs (meshes, solver files, iteration STEPs, topo .npz, renders, interim JSON). Disposable.
- Finished deliverables (final STEP, drawings, review views, final strength summary, SUMMARY.md) are published to the models folder with publish-to-models. STEP only.
- Once a run is published or superseded, delete its regenerable outputs. Keep only costly-to-regenerate results, in `_archive/<job>/`.
- Logs and caches are deleted, not kept.
- `_archive/` : iteration history and superseded versions. Read-only by convention.
- Never commit anything here to a public repo.
