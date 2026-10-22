# models folder: owned by handbuilt-cad

This folder belongs to the **handbuilt-cad** repo: https://github.com/living-relation/handbuilt-cad
No other repo owns or manages it (the workstation repo has nothing to do with it).

Used by: handbuilt-cad's `publish-to-models` skill (files finished parts here) and its tools (`tools/paths.py` finds this folder).
Deleting, moving or renaming this folder, or anything in it, breaks those tools and loses finished parts that may exist nowhere else.

Rules for agents and people:
- Don't move or rename this folder. Scripts find it through `MODELS_DIR`, then `[paths] models_dir` in handbuilt-cad's `local.toml`, then `<Desktop>\models`.
- It's add-only. Add new `<job>_<MMDD>/<rev>/` folders, and never overwrite, edit or delete an existing rev or file.
- Publish with the handbuilt-cad `publish-to-models` skill.
- This note is written by handbuilt-cad `tools/folder_notes.py`, run by setup and by publish-to-models. It's add-only: written only when missing, never overwritten.
- To change these rules, open a handbuilt-cad PR (`templates/models-folder/`).
