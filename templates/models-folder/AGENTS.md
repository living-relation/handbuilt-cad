# models folder: owned by handbuilt-cad

This folder belongs to the **handbuilt-cad** repo: https://github.com/living-relation/handbuilt-cad
It was set up by that repo's setup, run from the local clone at `@CLONE@`.
No other repo owns or manages it (the workstation repo has nothing to do with it).

Rules for agents and people:
- Don't move or rename this folder. Scripts find it through `MODELS_DIR`, then `[paths] models_dir` in the clone's `local.toml`, then `<Desktop>\models`.
- It's add-only. Add new `<job>_<MMDD>/<rev>/` folders, and never overwrite, edit or delete an existing rev or file.
- Publish with the handbuilt-cad `publish-to-models` skill.
- To change these rules, open a handbuilt-cad PR (`templates/models-folder/`). Setup writes this file only if it's missing.
