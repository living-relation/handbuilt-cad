# models folder: owned by handbuilt-cad

This folder belongs to the **handbuilt-cad** repo: https://github.com/living-relation/handbuilt-cad
No other repo owns or manages it.

Used by: handbuilt-cad's `publish-to-models` skill (files finished parts here) and its tools (`tools/paths.py` finds this folder).
Deleting, moving or renaming this folder breaks those tools and loses finished parts that may exist nowhere else.

Rules for agents and people:
- Don't move or rename this folder. Scripts find it through `MODELS_DIR`, then `[paths] models_dir` in handbuilt-cad's `local.toml`, then `<Desktop>\models`.
- Layout is `<subject>-rev<current>/rev<LETTER>/` (clerical `rev<LETTER>.<NN>`). The top folder is renamed to the current rev when a new one is filed. Never edit an existing rev folder.
- Keep the newest model letter and the one before it, plus the clerical decimals of those letters (Daniel, 2026-11-20). Delete the oldest after the new rev is hash-checked. Never delete 3D scans. Regenerate a rev's MANIFEST.sha256 after removing files from it.
- One part is one solid. A separate install step is its own part. Several pieces are an assembly of linked files in `Parts` (STEP: assembly STEP at the rev root, `Parts\` beside it), never one fused body. SR Fasteners stay as bodies inside the assembly; other fasteners are files. One assembly, built from the newest parts.
- ST185 jobs live here in the models folder (`st185_*`), not in the st185 repo.
- Publish with the handbuilt-cad `publish-to-models` skill.
- This note is written by handbuilt-cad `tools/folder_notes.py`, run by setup and by publish-to-models. It is written only when missing, never overwritten.
- To change these rules, open a handbuilt-cad PR (`templates/models-folder/`).

## CNC machining rules

Any agent designing CNC-machined parts, even without using the rest of handbuilt-cad, must follow the CNC rules in the handbuilt-cad file [`docs/CNC-MACHINING-RULES.md`](https://github.com/living-relation/handbuilt-cad/blob/main/docs/CNC-MACHINING-RULES.md) the in-repo text conversion [`docs/references/xometry-design-guide-cnc-machining-2025-04-16.md`](https://github.com/living-relation/handbuilt-cad/blob/main/docs/references/xometry-design-guide-cnc-machining-2025-04-16.md), and the source Xometry PDF in this folder at `references/xometry-design-guide-cnc-machining-2025-04-16.pdf`.

