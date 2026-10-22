---
name: cad-drawing
description: >-
  Use when making or regenerating a 2-D part drawing (11x17 PDF, plus DXF for
  machined parts) or an assembly drawing from a finished, checked STEP with the
  handbuilt-cad drawing engine (drawing/part.py, drawing/asm.py). Runs on the
  user's machine.
---
A project's own rules win over this skill, including where it files its CAD and drawings. The repo's CAD and drawing rules are `AGENTS.md` "CAD and drawing rules" and `drawing/DRAWING-RULES.md`; this skill only says how to run the engine and what to look at. Model checks are cnc-part-check; filing is publish-to-models.

## Where it runs
- WSL or Linux on the user's machine, with the handbuilt-cad venv (`[python] cad_py` in `local.toml`, empty = the repo's `.venv`). Shared venvs are read-only for agents.
- From another project: set `HANDBUILT_CAD` to a handbuilt-cad checkout and put `drawing`, `tools/render`, `tools/checks` and `tools` on `sys.path` (`drawing/README.md`). The project keeps its own specs and run scripts in its own repo; never copy the engine into it.
- Output goes to the job's working folder (`<cad_staging>/<job>/`), never into the toolkit repo.

## Inputs
- A STEP that passed cnc-part-check. The model drives the drawing: redline the drawing, change the model, then regenerate. Never make a drawing differ from its model.
- A spec dict per part. Required: `file`, `pn`, `title`, `material`, `process`. Common: `views`, `iso`, `scale`, `dims`, `ordinates`, `holes`/`threads`, `section`, `details`, `notes`, `center_marks`. `project` and `drawn` come from the spec, then `DRAWING_PROJECT` / `DRAWING_DRAWN`, then `local.toml` `[drawing]`.
- `<part no>.REVLOG.md` beside the model (template `drawing/templates/REVLOG.md`); the engine draws it as the Rev log table at the top right of sheet 1. Letters come from `drawing/revs.py` only. Initials come from `~/.drawing-initials` / `DRAWING_INITIALS`; if missing, ask the user for the requester's initials (AGENTS.md "Initials, never agent names").
- Notes the model can't carry: skipped fillets from the build report, edge breaks left out of the model (BREAK SHARP EDGES note), approved thin spots if the drawing should show them.

## Steps
1. `part.make_part(spec, out_pdf, out_dxf, png_prefix)` per part; `asm.make_assembly(spec, out_pdf, png_prefix)` for assemblies (balloons, BOM).
2. Open every PNG sheet yourself and check:
   - no hidden lines; center marks and center lines present on holes and bosses;
   - each feature dimensioned once, in the ASME/ISO-correct view, repeats as one dimension with (xN); no duplicate or overlapping dims or text;
   - section views capped (solid cut faces); the engine refuses an open cut, never work around it;
   - title block filled; rev letter, Rev log and revision triangles match the model's rev;
   - skipped-fillet and edge-break notes present where needed.
3. Fix problems in the spec (or the model, via the redline order), regenerate, re-check. Don't hand-edit the PDF/DXF.
4. Report: the files and an image of each sheet, the tool in parentheses after the part (e.g. "FH-103 Rev F (build123d)"). Raise only real problems. Report and ask as cnc-part-check "Asking the user" says.
5. After approval, file it: publish-to-models (`drawings/` in the rev folder), or the project's own filing rule and a PR.

## Notes
- Tests: `tests/test_revs.py`, `tests/test_drawing_settings.py`, `tests/test_sections.py`.
