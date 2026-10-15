# Notes for AI assistants running Fairsolid

Fairsolid is Grok Bot's private helper tool (see README). It is not meant for manual use.

- Always run the venv: `.venv\Scripts\fairsolid.exe ...` (or `.venv\Scripts\python.exe -m fairsolid.cli ...`).
  Don't install into the system Python, and don't set PYTHONIOENCODING.
- Put each scan in its own new folder under `runs\`. Never reuse or overwrite an existing run
  folder unless the user asks. `runs\` is not committed.
- Never rescale a scan. If a size or units check stops a run, report it; don't "fix" it with
  a scale factor. `fit --units` only picks the hole-size table.
- Closed part: `prepare SCAN --run runs\X`, show `runs\X\20_previews\*.png`, then `choose N --run runs\X`,
  then `fit --run runs\X`. Use `run SCAN --run runs\X` for unattended runs.
- Open space (reference scan): `prepare SCAN --run runs\X`, then `refscan --run runs\X`
  (`--knit`, `--patch-box x0,y0,z0,x1,y1,z1`, `--no-tidy`, `--cell MM`).
- Which STEP to hand over: the `"primary"` entry in `runs\X\state.json` for parts.
  For reference scans, use `40_ref_surfaces.step` and `40_ref_datums.step`.
- Pictures for the user: shaded result next to a plain grey scan render from the same angles.
  No heat maps or coloured-deviation images. Still report the numbers (median, p95, % within tolerance).
- To picture a part result: tessellate the STEP with cadquery, move `10_clean.ply` into the frame
  (`Frame.load(20_frame.json).to_canonical`), and draw both with `render_pair` from
  `fairsolid.stages.s40_refscan` (grey scan on top, shaded result below, same cameras).
- Large scans (1-3 million faces) take minutes. Run them in the background and check back.
- Tests: `.venv\Scripts\python.exe -m pytest -q` (takes about 8 minutes).
- Don't commit `CLAUDE.local.md` or any memory files.
