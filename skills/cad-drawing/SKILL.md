---
name: cad-drawing
description: >-
  Use when making or regenerating a 2-D drawing (11x17 PDF, DXF for machined
  parts) or an assembly drawing from a finished STEP with the handbuilt-cad
  drawing engine (drawing/part.py, asm.py). Runs on the user's machine.
---
> Draft by Grok Bot (17/10/26). Owner: SteveCAD, who will refine it. Changes go through a PR he reviews.

The project's own rules (AGENTS.md, decision log, revision register) win over this skill wherever they differ. The drawing rules the engine enforces are in `drawing/DRAWING-RULES.md`.

## Where it runs
- On the user's machine, in WSL or Linux, with the handbuilt-cad venv (`[python] cad_py` in `local.toml`, empty = the repo's `.venv`). Shared venvs are read-only for agents.
- From another project: set `HANDBUILT_CAD` to a handbuilt-cad checkout and put `drawing`, `tools/render`, `tools/checks` and `tools` on `sys.path` (see `drawing/README.md`). The project keeps its own specs and run scripts. Never copy the engine into the project.
- Write output to the job's working folder (`<cad_staging>/<job>/`), never into the toolkit repo.

## Inputs
- A finished, checked STEP (run cnc-part-check first). The model drives the drawing: redline the drawing, change the model, then regenerate. Never edit a drawing to differ from its model.
- A spec dict per part. Required: `file` (STEP path), `pn`, `title`, `material`, `process`. Common options: `views`, `iso`, `scale`, `dims`, `ordinates`, `holes`/`threads`, `section`, `details`, `notes`, `center_marks`. `project` and `drawn` come from the spec, then `DRAWING_PROJECT` / `DRAWING_DRAWN`, then `local.toml` `[drawing]`, then neutral defaults.
- Rev log: `<part no>.REVLOG.md` beside the model (template in `drawing/templates/`). The engine draws the Rev log table at the top right of sheet 1. Model and drawing letters always match. Letters come from `drawing/revs.py` (A..Z skipping I, L, O, Q, then AA; clerical `.NN`).

## Steps
1. `part.make_part(spec, out_pdf, out_dxf, png_prefix)` for each part; `asm.make_assembly(spec, out_pdf, png_prefix)` for assemblies (balloons and BOM table).
2. Look at every sheet yourself (the PNG previews): no hidden lines, center marks kept, no overlapping dims or text, title block filled, Rev letter matches the model.
3. Section views must be capped (solid cut faces). The engine refuses an open cut (`section_view` raises if the cut leaves no faces). Never work around that.
4. Report the files, then walk the user through any problems one decision at a time (see the project's rules for how to ask).
5. File with publish-to-models (`drawings\` in the rev folder) after the user approves.

## Notes
- Renders for review: `tools/render/smooth_render.py` (smooth shading, no mesh lines; `--section` for a capped cut view).
- Tests: `tests/test_revs.py`, `tests/test_drawing_settings.py`, `tests/test_sections.py`.
