---
name: cad-drawing
description: >-
  Use when making or regenerating an assembly drawing package (11x17 PDF) from a
  finished, checked STEP with the handbuilt-cad drawing engine (drawing/part.py,
  drawing/asm.py). Assembly-only standard: build order and installation, no
  separate part drawings or DXF. Includes the printed-parts list. Runs on the
  user's machine.
---
A project's own rules win over this skill, including where it files its CAD and drawings. The repo's CAD and drawing rules are `AGENTS.md` "CAD and drawing rules" and `drawing/DRAWING-RULES.md`; this skill only says how to run the engine and what to look at. Model checks are cnc-part-check; filing is publish-to-models.

## When to use
A finished, checked STEP, using the handbuilt-cad drawing engine (`drawing/part.py`, `drawing/asm.py`). Runs on the user's machine.

## Models and drawing scope
- Full, accurate CAD models remain required for every part and every subassembly, including unmodified off-the-shelf hardware used in the design (maker model, primary-source-spec-check). The assembly-only rule covers drawings, never deletion or omission of models.
- An assembly is any model with more than one part. Produce only assembly drawing packages: as many 11x17 sheets as needed to communicate build order, where each item installs, and assembly-critical interfaces.
- No separate part engineering drawings or DXFs for machined, modified-OTS, printed, or any other parts. Fabrication-critical details such as grooves belong in dimensioned assembly sections/details, not standalone part sheets.
- Completed subassemblies appear as one installation item in their parent package. Give each subassembly its own assembly package when needed; do not explode it again in the parent.
- Unmodified bought hardware stays in the model-driven BOM.
- For any assembly containing 3D-printed parts, include one single-page printed parts list: every printed part with a thumbnail, part number, name, quantity, and material. It is a supporting list, not an engineering drawing.

## Where it runs
- WSL or Linux on the user's machine, with the handbuilt-cad venv (`[python] cad_py` in `local.toml`, empty = the repo's `.venv`). Shared venvs are read-only for agents.
- From another project: set `HANDBUILT_CAD` to a handbuilt-cad checkout and put `drawing`, `tools/render`, `tools/checks` and `tools` on `sys.path` (`drawing/README.md`). The project keeps its own specs and run scripts in its own repo; never copy the engine into it.
- Output goes to the job's run folder in the parts home (`~/cad-parts/<job>/runs/<stamp>/`, `tools/paths.py`), never into the toolkit repo or the models folder.

## Inputs
- Full component and assembly STEPs that passed cnc-part-check and the other applicable checks. The model drives the drawing: redline the drawing, change the model if required, then regenerate. Never make a drawing differ from its model.
- Assembly and subassembly spec dicts. Common fields: `file`, `pn`, `title`, `material`, `process`, `views`, `iso`, `scale`, `dims`, `ordinates`, `holes`/`threads`, `section`, `details`, `notes`, `center_marks`; BOM hierarchy and build sequence are also required. `project` and `drawn` come from the spec, then `DRAWING_PROJECT` / `DRAWING_DRAWN`, then `local.toml` `[drawing]`.
- `REVLOG.md` beside the assembly model (template `drawing/templates/REVLOG.md`); the engine draws it as the Rev log table at the top right of sheet 1. Letters come from `drawing/revs.py` only. Initials come from `~/.drawing-initials` / `DRAWING_INITIALS`; if missing, ask the user for the requester's initials (AGENTS.md "Initials, never agent names").
- Use real fastener-tool hardware models and real specifications, never placeholder fasteners or guessed dimensions. Verify numerical values and normative ISO syntax against authoritative sources; mark unconfirmed items TBD.
- Notes the model cannot carry: skipped fillets from the build report, approved assembly procedures, verified torque/threadlocker requirements (only when the user asks for them), approved edge-break leaders (`BREAK ALL EDGES, STD` or a user-given length; only after the user approves, never a default title-block note and never an auto-applied general note), approved thin spots if the drawing should show them, and unresolved fabrication holds. Never present an impossible interface as approved.
- BOM with process/material per part so printed vs machined vs OTS is not guessed. One model-driven identity for every BOM line and balloon across all sheets.

## Holes and threads
Hole and thread callouts go in capped assembly sections/details, not standalone part sheets (`drawing/part.py` `hole_callouts`, DRAWING-RULES 21a, `docs/CNC-MACHINING-RULES.md` CNC-THREAD-DEPTH):
- Through holes (plain or tapped) are `THRU` with no depth. Depth is only for blind holes.
- Blind taps use the actual `spec['thread_depth']` (or a modeled thread). When the hole is deeper than the thread, both are called out, e.g. `M4x0.7-6H ↧6` and `⌀3.3 ↧8`.
- If thread depth is unknown, flag it; do not invent a depth from 1.5×D. Only under-1.5×D engagement is a model-check flag, and it must not change the drawing text. Deeper than 2×D is never flagged.

## Steps
1. Storyboard the real build before making views. For each step identify what is already fitted, what moves, the true insertion path, final seating and tool access. Reverse a realistic disassembly sequence; use multiple restrained steps instead of one crowded explosion.
2. Use `asm.make_assembly(spec, out_pdf, png_prefix)` for the assembly package (balloons, BOM). `part.make_part` remains engine code but its standalone PDF/DXF outputs are not part of this drawing standard. Put necessary groove, hole and hidden-interface information in capped assembly sections/details with verified ISO callouts and dimensions (THRU / actual blind depths as above).
3. Keep finished subassemblies intact in the parent package. Move related groups first, then separate only what the step needs. Connect explode lines to actual mating features along insertion axes; use intermediate holes where required, never through solid material. Manually verify every automatically generated line.
4. If the assembly has printed parts, make the one-page printed parts list (PDF) with a thumbnail of each printed part from its STEP, plus pn/title/qty/material.
5. Open every exported PNG sheet yourself and check at intended print scale:
   - build order, installation locations, dimensions and access are clear and uncrowded;
   - no hidden lines and no mesh lines; center marks and center lines present on holes and bosses;
   - each key dimension appears once, in the ASME/ISO-correct view, repeats as one dimension with (xN); no overlapping text, dims or balloons;
   - section views are capped (solid cut faces); the engine refuses an open cut, never work around it;
   - groove and hole details have verified dimensions, tolerances and callouts (THRU with no depth for through holes; actual thread and hole depths for blind holes, both when the hole is deeper than the thread);
   - explode routes agree with real insertion/removal paths and do not cross solids;
   - construction sketches, planes, stale circles, superseded hole marks, dangling annotations and obsolete views are absent;
   - title block filled; rev letter, Rev log and revision triangles match the model's rev;
   - one consistent BOM/balloon identity agrees with all sheet quantities and the actual assembly;
   - printed parts list is one page and every printed part has a readable thumbnail;
   - skipped-fillet notes present where needed; if chamfers or fillets are modeled, their actual dimensions are annotated, with no general edge-break note; approved unmodeled cut-risk edges use a leader `BREAK ALL EDGES, STD` or the user-given length, never a default title-block note.
6. Fix problems in the spec (or the model, via the redline order), regenerate and recheck every sheet. Never hand-edit PDFs or DXFs. Log the problem/reason, source revision and output revision; review dependency changes model, then assembly, then drawing, then PDF.
7. Report the package files and an image of each sheet, with the tool in parentheses after the model (e.g. "<assembly> Rev F (build123d)"), preserving any real unresolved fabrication holds as explicit holds. Raise only real problems. Report and ask as cnc-part-check "Asking the user" says.
8. After approval, file the models plus package with publish-to-models (the package and printed parts list go in `drawings/` of the new version folder), or follow the project's own filing rule and a PR.

## Notes
- Tests: `tests/test_revs.py`, `tests/test_drawing_settings.py`, `tests/test_sections.py`, `tests/test_hole_callouts.py`.
- CNC wall floors (0.030" / 0.762 mm metal, 0.060" / 1.52 mm plastic), 1.3x inside-corner radius, edge-break policy, and thread rules are in `docs/CNC-MACHINING-RULES.md`. The in-repo Xometry guide text is `docs/references/xometry-design-guide-cnc-machining-2025-04-16.md` (the PDF stays in the models folder, `references/`).
