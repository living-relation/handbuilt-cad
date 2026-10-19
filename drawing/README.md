# drawing/

- Drawing engine (build123d + OCCT hidden-line removal): `part.py` (part drawings), `asm.py` (assemblies), `dwg.py` (sheet, title block, rev log table), `feat.py`, `hw.py`.
- `revs.py` - rev letters (A..Z skipping I, L, O, Q, then AA ...), clerical decimals, and the per-model `REVLOG.md`. Tests: `tests/test_revs.py`.
- `DRAWING-RULES.md` - the drawing rules this engine enforces (marked "(engine)").
- `templates/` - `REVLOG.md`, `DRAWING-REVS.md` (revision register with Made with and Evidence columns), `MADE-WITH.md`.
- `settings.py` - title-block `project` (spec, then `DRAWING_PROJECT`, then `local.toml` `[drawing]`, then `PROJECT`) and the initials rule (DRAWING-RULES 32): `requester_initials()` reads env `DRAWING_INITIALS` / `~/.drawing-initials`, prompts a human once, stops an agent. Tests: `tests/test_drawing_settings.py`, `tests/test_initials.py`.

## Using the engine from another project
A project repo keeps its own job specs and run scripts and imports the engine from a handbuilt-cad checkout:
```python
import os, sys
HB = os.environ['HANDBUILT_CAD']            # path to a handbuilt-cad checkout
for d in ('drawing', 'tools/render', 'tools/checks', 'tools'):
    sys.path.insert(0, os.path.join(HB, d))
import part, asm, revs                      # part.make_part(spec, pdf, dxf, preview_prefix)
```
Put `project` in each spec (or in `local.toml` `[drawing]`) for the title block. DRAWN is not set in a spec: it is the Rev A BY of the rev log (new log: `revs.add_release(...)` with no `by` uses the requester's initials). The engine's rules (no hidden lines, center marks kept, rev log table top right of sheet 1 from `<part no>.REVLOG.md`, model/drawing letters match, letters skip I/L/O/Q then AA, AB ...) are in `DRAWING-RULES.md`. Renders: `tools/render/smooth_render.py` (smooth shading, no mesh lines).

Assembly spec keys for the balloon, exploded-view and label rules (DRAWING-RULES 24-30): item `primary`, `no_balloon`; spec `iso_balloons`, `exploded`, `label_views` (`labels`, `wires`, `text_h`), `tol`; part specs `stage_sheets`, `stage_items`, `stage_notes` (DRAWING-RULES 31). Every run writes `<pdf>.checks.json` beside the PDF. Tests: `tests/test_drawing_rules.py`.
