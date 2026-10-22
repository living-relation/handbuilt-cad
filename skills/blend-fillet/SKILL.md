---
name: blend-fillet
description: >-
  Use when the CAD kernel's own fillet fails at a junction between two bodies
  (tilted arm on a plate, lofted or multi-face bodies) and a rolling-ball blend
  solid from tools/blend.py is needed instead. Runs on the user's machine.
---
The project's own rules win over this skill. Fillet order, batching and "skip and list failures" are in cnc-part-check (Fillets and edge breaks); this skill is only the fallback for one junction the kernel can't fillet.

## When
After all cuts, as part of the last fillet pass, and only once the kernel fillet on that junction has failed in small batches. If the blend also fails, skip it and list it with the other skipped fillets (build report and drawing notes); never stall the model on it.

## Where it runs
WSL or Linux on the user's machine, with the handbuilt-cad venv (shapely; `compare` also needs scipy). Output to the job's working folder, never into the repo.

## Use
```python
from blend import blend, fuse_blend
res = blend(arm, plate, r=6)              # .pieces, .expected_mm3, .samples, .notes, .skipped
part, rep = fuse_blend(arm + plate, res)  # fused part + checks
```
CLI: `tools/blend.py pair A.step B.step --r 6 [--base body.step] -o out`; `demo` / `compare` try it on a test shape. Method (section loft, adaptive spacing, crease-normal fallback) is in the module docstring.

## Accept only if
- `rep` shows one valid solid, a clean STEP re-import, and added volume within 10 % of `expected_mm3` (an inside-out or fake solid fails this).
- Every entry in `res.skipped` (crease sections left out; wide gaps split the blend) is listed as a skipped fillet.
- cnc-part-check is re-run on the final solid, and you've looked at a smooth render of the blend before sending.
