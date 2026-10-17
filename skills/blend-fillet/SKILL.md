---
name: blend-fillet
description: >-
  Use when a kernel fillet fails at a junction between two bodies (tilted
  arm on a plate, lofted or multi-face bodies) and a rolling-ball blend solid
  is needed instead (tools/blend.py). Runs on the user's machine.
---
> Draft by Grok Bot (17/10/26). Owner: SteveCAD, who will refine it. Changes go through a PR he reviews.

The project's own rules win over this skill wherever they differ. Fillets still come last (after all cuts), as cnc-part-check says. Use this only when the CAD's own fillet fails.

## Where it runs
On the user's machine, with the handbuilt-cad venv (needs shapely; the `compare` mode also needs scipy). Write output to the job's working folder, never into the repo.

## Use
```python
from blend import blend, fuse_blend
res = blend(arm, plate, r=6)              # .pieces, .expected_mm3, .samples, .notes, .skipped
part, rep = fuse_blend(arm + plate, res)  # fused part + checks
```
Command line: `tools/blend.py pair A.step B.step --r 6 [--base body.step] -o out`, or `demo` / `compare` to try it on a test shape.

## Before calling it done
- `rep` must show a valid single solid, a clean STEP re-import and the added volume within 10 % of the expected volume. A fake or inside-out solid fails the volume check. Never ship one that fails.
- `res.skipped` lists any crease sections left out (logged as warnings). Report them. Wide gaps split the blend into separate runs.
- Then re-run cnc-part-check on the final solid (walls, fits, round-trip). Look at a smooth render of the blend yourself before sending.

## Notes
- How it works (section loft, adaptive spacing, crease-normal fallback) is in the module docstring.
- Fillets in small batches with chamfer/fillet batch tools are still the first choice when the kernel handles them.
