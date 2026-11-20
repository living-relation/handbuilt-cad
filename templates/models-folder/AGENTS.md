# models folder: owned by handbuilt-cad

This folder belongs to the **handbuilt-cad** repo: https://github.com/living-relation/handbuilt-cad
No other repo owns or manages it.

Used by: handbuilt-cad's `publish-to-models` skill (files finished parts here) and its tools (`tools/paths.py` finds this folder).
Deleting, moving or renaming this folder breaks those tools and loses finished parts that may exist nowhere else.

Rules for agents and people:
- Don't move or rename this folder. Scripts find it through `MODELS_DIR`, then `[paths] models_dir` in handbuilt-cad's `local.toml`, then `<Desktop>\models`.
- This folder holds AP242 STEP files and drawings only, plus a short `<part>-rev<LETTER>.md` card and this README. No .f3d (Fusion keeps that in its cloud), scripts, runs, or scans. Those stay in the parts home (`~/cad-parts/<job>/`).
- A job folder is `<subject>_<MMDD>/`. Parts in it can be at different revs: `<part>-rev<LETTER>.step`. An assembly STEP references each part as `Parts/<part>.stp`.
- Keep each part's newest letter and the one before it (and those letters' clerical decimals). Prune deletes only that part's older files. Bought maker STEPs in `reference/` have no rev.
- ST185 jobs live here in the models folder (`st185_*`), not in the st185 repo.
- Publish with the handbuilt-cad `publish-to-models` skill.
- This note is written by handbuilt-cad `tools/folder_notes.py`, run by setup and by publish-to-models. It is written only when missing, never overwritten.
- To change these rules, open a handbuilt-cad PR (`templates/models-folder/`).

## CNC machining rules

Any agent designing CNC-machined parts, even without using the rest of handbuilt-cad, must follow the CNC rules in the handbuilt-cad file [`docs/CNC-MACHINING-RULES.md`](https://github.com/living-relation/handbuilt-cad/blob/main/docs/CNC-MACHINING-RULES.md) the in-repo text conversion [`docs/references/xometry-design-guide-cnc-machining-2025-04-16.md`](https://github.com/living-relation/handbuilt-cad/blob/main/docs/references/xometry-design-guide-cnc-machining-2025-04-16.md), and the source Xometry PDF in this folder at `references/xometry-design-guide-cnc-machining-2025-04-16.pdf`.

