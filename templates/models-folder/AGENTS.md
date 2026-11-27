# models folder: owned by handbuilt-cad

This folder belongs to the **handbuilt-cad** repo: https://github.com/living-relation/handbuilt-cad
No other repo owns or manages it.

Used by: handbuilt-cad's `publish-to-models` skill (files finished parts here) and its tools (`tools/paths.py` finds this folder).
Deleting, moving or renaming this folder breaks those tools and loses finished parts that may exist nowhere else.

Rules for agents and people:
- Don't move or rename this folder. Scripts find it through `MODELS_DIR`, then `[paths] models_dir` in handbuilt-cad's `local.toml`, then `<Desktop>\models`.
- This folder holds usable AP242 STEP models and drawings only, plus each version's `SUMMARY.md`, `REVLOG.md` and these notes. No .f3d (Fusion keeps that in its cloud), STL, scripts, runs, scans, backup ZIPs or purge copies. Working files stay in the parts home (`~/cad-parts/<job>/`).
- A job folder holds version folders `rev<LETTER>/` (clerical `rev<LETTER>.<NN>/`). Existing job folder names are kept as they are. A version holds the assembly STEP at its root, `Parts/` beside it (every part, subassembly and bought maker STEP, referenced by the assembly), `drawings/`, `SUMMARY.md` and `REVLOG.md`. Never edit an existing version.
- Keep the 2 latest versions of each assembly (with their parts); older versions are deleted after the new one is filed and checked. Never delete or alter a 3D scan.
- Publish with the handbuilt-cad `publish-to-models` skill.
- This note is written by handbuilt-cad `tools/folder_notes.py`, run by setup and by publish-to-models. It is written only when missing, never overwritten.
- To change these rules, open a handbuilt-cad PR (`templates/models-folder/`).

## CNC machining rules

Any agent designing CNC-machined parts, even without using the rest of handbuilt-cad, must follow the CNC rules in the handbuilt-cad file [`docs/CNC-MACHINING-RULES.md`](https://github.com/living-relation/handbuilt-cad/blob/main/docs/CNC-MACHINING-RULES.md) the in-repo text conversion [`docs/references/xometry-design-guide-cnc-machining-2025-04-16.md`](https://github.com/living-relation/handbuilt-cad/blob/main/docs/references/xometry-design-guide-cnc-machining-2025-04-16.md), and the source Xometry PDF in this folder at `references/xometry-design-guide-cnc-machining-2025-04-16.pdf`.

