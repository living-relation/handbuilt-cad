# models folder: owned by handbuilt-cad

This folder belongs to the **handbuilt-cad** repo: https://github.com/living-relation/handbuilt-cad
No other repo owns or manages it (the workstation repo has nothing to do with it).

Used by: handbuilt-cad's `publish-to-models` skill (files finished parts here) and its tools (`tools/paths.py` finds this folder).
Deleting, moving or renaming this folder breaks those tools and loses finished parts that may exist nowhere else.

Rules for agents and people:
- Don't move or rename this folder. Scripts find it through `MODELS_DIR`, then `[paths] models_dir` in handbuilt-cad's `local.toml`, then `<Desktop>\models`.
- Add new `<job>_<MMDD>/<rev>/` folders; never overwrite or edit an existing rev.
- Old versions may be deleted (Daniel, 2026-11-04): keep the latest version plus the 2 most recent previous versions of each assembly, and every part those kept assemblies use; parts keep the latest version. Keep at most 2 screenshots/2D renders per model (drawings PDF/DXF/SVG are not screenshots). Never delete 3D scans. Regenerate a rev's MANIFEST.sha256 after removing files from it.
- ST185 jobs live here in the models folder (`st185_*`), not in the st185 repo.
- Publish with the handbuilt-cad `publish-to-models` skill.
- This note is written by handbuilt-cad `tools/folder_notes.py`, run by setup and by publish-to-models. It's add-only: written only when missing, never overwritten.
- To change these rules, open a handbuilt-cad PR (`templates/models-folder/`).
