# drawing/

- Drawing engine (build123d + OCCT hidden-line removal): `part.py` (part drawings), `asm.py` (assemblies), `dwg.py` (sheet, title block, rev log table), `feat.py`, `hw.py`.
- `revs.py` - rev letters (A..Z skipping I, L, O, Q, then AA ...), clerical decimals, and the per-model `REVLOG.md`. Tests: `tests/test_revs.py`.
- `DRAWING-RULES.md` - the drawing rules this engine enforces (marked "(engine)").
- `templates/` - `REVLOG.md`, `DRAWING-REVS.md` (revision register with Made with and Evidence columns), `MADE-WITH.md`.
