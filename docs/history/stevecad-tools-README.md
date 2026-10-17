# stevecad-tools
SteveCAD's CAD toolkit (moved from the box to DansPC WSL, 2026-10-16). Local git only, no remote.

## Setup
```bash
source /home/daniel/projects/handbuilt-models/.venv/bin/activate   # has everything in requirements.txt; do not install into it
# or: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
Fonts: uses DejaVu (system or matplotlib's bundled copy). Extra fonts: `STEVECAD_FONTS=/path/a.ttf:/path/b.ttf`.

## Tools
| Path | What it does |
|---|---|
| `drawing/dwg.py` | Drawing engine: exact B-rep (OCCT HLR) visible-line views -> 11x17 (ANSI B) sheets -> PDF + DXF, title block, rev log table (top right, sheet 1), auto center marks. No hidden lines, no facet/seam lines. |
| `drawing/revs.py` | Rev letters (A-Z skipping I/L/O/Q, then AA...), clerical decimals, `REVLOG.md` read/write. Tests: `tests/test_revs.py`. |
| `drawing/part.py` | `make_part(spec, pdf, dxf, preview_prefix)`: part drawing with auto hole callouts, dims, sections, details. |
| `drawing/asm.py` | `make_assembly(spec, pdf, preview_prefix)`: assembly sheets, balloons, BOM. `load_children()` reads STEP assembly tree. |
| `drawing/feat.py` | Hole/feature recognition (cylinders, cones, counterbores, radii). |
| `drawing/hw.py` | Simple hardware solids (csk/pan screws) for assembly views. |
| `render/smooth_render.py` | Smooth-shaded STEP/STL PNG (no triangle lines, optional feature edges). |
| `render/secplot.py` | 2D section plots of a solid on a plane (matplotlib). |
| `checks/mesh_check.py` | Print-file check: valid solids, tiny faces, open/non-manifold edges, body count. Exit 1 on fail. |
| `checks/check_printed_walls.py`, `walls_any.py` | Min-wall thickness check for printed parts. |
| `checks/roundtrip.py` | STEP export/re-import volume + body check. |
| `checks/intf.py` | Interference check between assembly bodies. |
| `checks/holefix.py`, `fxlib.py`, `edgebreak.py` | Hole correction (ISO tap drills, >=1.5D thread) and fix helpers. |
| `checks/plane_dump.py` | List planar faces by axis/level (for dimensioning). |
| `examples/st185/` | ST185 job specs and run scripts. See NOTE.md. |
| `skills/` | SteveCAD skill SKILL.md files (copies; source of truth is the workflows store). |

## Examples
```bash
python render/smooth_render.py part.step out.png --view iso --edges
python checks/mesh_check.py base.step
ST185_WORK=~/work/st185 python examples/st185/run_one.py csb3_body
```
Drawing rules: see [DRAWING-RULES.md](DRAWING-RULES.md). Each model folder gets a `REVLOG.md` (one row per release) that feeds the drawing's rev log.
Rules: STEP is the deliverable (no STL unless a print job needs it). The model drives the drawing: regenerate after every model change. Run heavy CAD on DansPC, not the box.
