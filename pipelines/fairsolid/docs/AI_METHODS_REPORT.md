# LLM/VLM scan-to-CAD methods — verified availability and feasibility

> **History only (2026-10-08).** The optional AI stage this report describes
> (stage 40, run in WSL2 from `~/cadenv`) has been removed from Fairsolid. It
> measured worse than the deterministic path on every real scan tested (see
> below). The setup and operating steps here no longer apply and are kept only
> as a record. See `docs/SURFACE_FIT_PLAN.md`, part 11.

Every claim here was checked against the live repository, model card, or paper
in September 2026. Where the source document was wrong, that is stated.

## Verdict table

| Method | Venue | Code | Weights | License | Commercial | Verdict |
|---|---|---|---|---|---|---|
| **CADReasoner** | CVPR 2026 | [zhemdi/CADReasoner](https://github.com/zhemdi/CADReasoner) | `kulibinai/cadreasoner{,-pc,-cm}` | **Apache-2.0** | **yes** | **Primary pick** |
| **cadrille** | ICLR 2026 | [col14m/cadrille](https://github.com/col14m/cadrille) | `maksimko123/cadrille{,-rl}` | **Apache-2.0** | **yes** | **Secondary / ensemble** |
| **CAD-Recode** | ICCV 2025 | [filaPro/cad-recode](https://github.com/filaPro/cad-recode) | `filapro/cad-recode-v1.5` | CC BY-NC 4.0 | no | Fast baseline |
| **CADFit** | ICML 2026 | [ghadinehme/CADFit](https://github.com/ghadinehme/CADFit) | — | CC BY-NC 4.0 | no | Richest operator set |
| **Point2CAD** | CVPR 2024 | [prs-eth/point2cad](https://github.com/prs-eth/point2cad) | ParseNet | CC BY-NC 4.0 | no | **Skip** |
| **MiCADangelo** | NeurIPS 2025 | none found | — | — | — | **Skip — paper only** |

## Errors in the source document

1. **`meshStep` runs the wrong direction.** The document describes it as
   mesh → STEP. [CNCKitchen/meshStep](https://github.com/CNCKitchen/meshStep)
   is STEP → mesh: it tessellates B-Rep into watertight triangle meshes. It is
   AGPL-3.0 TypeScript and is of no use for reverse engineering.

2. **Point2CAD is oversold.** It is real and it is good work, but it
   **requires an already-segmented point cloud** in `(x, y, z, surface_id)`
   form, and it **has no STEP export** — it emits surfaces, edges and corners.
   It cannot be dropped into a scan-to-STEP pipeline.

3. **MiCADangelo has no public code.** The paper is real (NeurIPS 2025,
   arXiv 2510.23429); no repository was found under any author's account.

4. **Instant Meshes is scriptable.** The document implies GUI-only. Passing
   `-o/--output` puts it in batch mode (`src/batch.h`), with `-f/--faces`,
   `-v/--vertices`, `-S/--smooth`, `-t/--threads`, `-d/--deterministic`.

## The omission that matters most

**Every one of these models normalises the input into a unit cube and emits
dimensionless code.** CAD-Recode's own demo does exactly this:

```python
mesh.apply_translation(-(mesh.bounds[0] + mesh.bounds[1]) / 2.0)
mesh.apply_scale(2.0 / max(mesh.extents))
```

The benchmarks are IoU-based, and IoU is scale-invariant, so the loss never
appears in a published number — but a STEP file at unknown scale is not
manufacturable. **No paper in this list solves it.** Fairsolid solves it in
`geom.Frame`: the forward normalisation is recorded before inference and
inverted after, so the exported solid is at true millimetres.

## Honest feasibility

CADReasoner sees **128 points and 8 renders at 238×238**. CAD-Recode sees
**256 points**. They recover *design intent and gross topology*, not
metrology. Reported scan-track IoU:

| Dataset | IoU | What it means |
|---|---|---|
| DeepCAD | 88.8% | simple sketch-extrude parts |
| Fusion360 | 83.3% | moderate mechanical parts |
| **MCB** | **51.3%** | **real machined parts** |

Used alone, none of these will give a workable STEP from an arbitrary scan of
a real part. Used as a **proposer whose parameters are then refit against
primitives measured from the full-density scan**, they become useful. That
hybrid is what Fairsolid implements, and it is the part no paper ships.

For reference, the deterministic path in this repo — no ML at all — recovers
these from a scan with 0.04 mm noise and 17% occlusion:

| Feature | Nominal | Recovered | Error |
|---|---|---|---|
| Plate length | 80.000 | 79.983 | 0.017 mm |
| Plate thickness | 12.000 | 11.985 | 0.015 mm |
| Boss height | 10.000 | 9.997 | 0.003 mm |
| Bore diameter | 16.000 | 15.995 | 0.005 mm |
| Boss diameter | 26.000 | 25.996 | 0.004 mm |
| Corner holes | 6.000 | 5.996–5.997 | 0.004 mm |

That is the bar the AI stage has to clear to be worth adding.

---

## Operating instructions per model

All three run in **WSL2 Ubuntu** (already installed on this machine) rather
than Windows, because `flash-attn` has no reliable Windows wheels. The RTX
3060 is Ampere, which satisfies CADReasoner's requirement.

### Shared environment

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12 ~/cadenv && source ~/cadenv/bin/activate
uv pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124
uv pip install transformers==4.50.3 tokenizers==0.21.0 accelerate==0.34.2 \
    cadquery==2.5.2 cadquery-ocp==7.7.2 trimesh==4.5.3 pyvista==0.46.3 \
    manifold3d==3.0.0 numpy==2.2.0 scipy==1.14.1 qwen-vl-utils==0.0.10 \
    safetensors==0.4.5 pillow==11.3.0 opencv-python rtree
# prebuilt wheel - do NOT compile flash-attn from source
uv pip install https://github.com/mjun0812/flash-attention-prebuild-wheels/releases/download/v0.0.0/flash_attn-2.6.3+cu124torch2.5-cp312-cp312-linux_x86_64.whl
```

If the wheel misbehaves, drop `attn_implementation="flash_attention_2"` and
use `"sdpa"`. Slower, no accuracy change.

### CADReasoner — best quality, closed loop

**Correction to this section**, found only by actually running it (2026-09-09):
the command above is the ROOT `test.py`, which drives the **image-only**
model (`kulibinai/cadreasoner`, multi-view renders, no points). The checkpoint
named here, `kulibinai/cadreasoner-cm`, is a **`pc_cm/`** checkpoint (point
cloud + renders) and is not loadable through the root script at all - see
`pc_cm/README.md` in the live repo. Fairsolid integrates the plain
point-cloud sibling instead:

```bash
git clone https://github.com/zhemdi/CADReasoner && cd CADReasoner/pc_cm
python3 test.py --dataset <dir-of-stl> --checkpoint kulibinai/cadreasoner-pc \
    --use_pc true --use_img false --n_points 128 --n_iters 3 --outdir out/
```

`-pc` over `-cm` on purpose: `-cm` needs `pc_cm/visualization.py`'s renderer
(pyvista/VTK), which failed to import in cadenv (`VTKVersionError`) and isn't
worth fixing to run a model this project doesn't yet use. `-pc`'s own
unconditional `import pyvista as pv` at module scope is satisfied with an
on-disk stub instead (see `scripts/wsl_cadreasoner.py`) - it is never
constructed on this path.

Loads as `pc_cm/cadrille.py`'s `Cadrille` class - **a different file from the
plain `cadrille` repo's own `cadrille.py`**, despite the identical class name;
do not put both on `sys.path` in the same process. `--n_iters 3` is `pc_cm`'s
own default (the paper's `--n_iters 5` headline number is for `-cm`, not
`-pc`); `test.py` also hardcodes `attn_implementation="flash_attention_2"`
with no override, so the prebuilt wheel (below) has to be installed even
though plain cadrille skips it.

**What "iterative" means for `-pc` is not what it sounds like.** Each
iteration doesn't refine a rendered image - `pc_cm/pc_utils.py::make_pc_far`
rebuilds the *point cloud itself* from the geometric discrepancy between the
target mesh and the current best prediction (128 points GT→pred, 128
pred→GT), and `n_samples` resamples per iteration are re-scored by chamfer
distance against the target to pick what survives. This needs the full
target mesh at every iteration, not a fixed point cloud computed once, and
`cadquery` inside cadenv to mesh every candidate for scoring - a dependency
plain cadrille's inference never needed there.

**Two normalisations, not one - single `Frame.from_unit()` is not enough.**
`pc_cm/dataset.py::normalize_to_unit_cube` derives its own centre/scale from
whatever mesh file it is handed, independent of any `Frame`. Fairsolid feeds
it `frame.to_unit(mesh)` (not real mm) for a separate reason - see below - so
the model's output must be un-normalised through THAT mesh's own
centre/scale first, and only then through the stage-20 `Frame`. Both steps
reuse `s80_export.place_solid`, called twice.

**The GT-vs-prediction chamfer score is scale-blind, and it decides what
survives every iteration.** `test.py::get_cd` rescales the *predicted* mesh
to a unit cube but loads the GT mesh **raw**. Their own benchmark datasets
store GT meshes pre-normalised, so this never shows up on their numbers -
but handed an 80 mm real part it returned a chamfer distance of ~968 (a
sane run scores well under 1), silently making the refinement loop keep
whatever candidate happened to be closest in raw scale, not shape. Fixed
without touching vendored code by feeding `pc_cm` a mesh already close to
unit scale (`frame.to_unit`), which makes its internal re-normalisation
~identity and the comparison meaningful again.

**Grid convention is a point value (÷100), not cadrille's full-span
convention (÷200).** `pc_cm/dataset.py::normalize_pred_mesh` divides raw
predicted coordinates by exactly 100 to reach the `[-1, 1]` cube. Reusing
cadrille's `MODEL_GRID = 200` constant here is a silent, exact 2x scale
error - caught only by checking the reconstructed bounding box against the
synthetic fixture's known dimensions, not by anything the run itself
reports as an error.

**Measured, on the synthetic fixture** (`tests/data/nominal.stl`,
`--n_iters 3 --n_samples 4`, once the above was fixed): reconstructed
bounding box 50.40 x 80.00 x 22.00 mm against the frame's own measured
aligned extents of 50.00 x 80.00 x 22.00 mm - under 1% error on all three
axes, and a noticeably closer match than plain cadrille's per-feature errors
on the same fixture (recorded in the commit history). The exported solid
failed `BRepCheck_Analyzer` validity on this run; the real-scan runs below
all report `is_valid: true`, so this looks fixture-specific rather than
systemic, but it was never chased further.

**Measured, on all five real scans** (`--n_iters 3 --n_samples 4`), scored
the same way the deterministic path already is - `s70_deviate` against the
cleaned scan, 0.5 mm tolerance:

| Scan | bbox error (worst axis) | deterministic median | cadreasoner-pc median | ratio |
|---|---|---|---|---|
| dash_housing | 1.5% | 3.614 mm | 21.40 mm | 5.9x worse |
| pedal_adapter | 29.4% (Z) | no-param | 2.93 mm | n/a - only one produced a result |
| fuel_pump | 38.0% (Y) | 1.032 mm | 2.02 mm | 2.0x worse |
| bezel | 65.0% (Y) | 0.571 mm | 3.92 mm | 6.9x worse |
| oil_catch | 16.6% (X) | 5.900 mm | 31.14 mm | 5.3x worse |

Two separate, independently-verified findings, not one:

1. **Bounding-box accuracy tracks aspect ratio, not part identity.**
   dash_housing (extents ratio ~1.6:1, boxy) reconstructs its bounding box to
   under 1.5% on all three axes. bezel (a 405 mm trim panel, ~6:1) and
   fuel_pump (~3.2:1) both badly undershoot their own longest axis (-65%,
   -38%). Verified by instrumenting the pipeline stage-by-stage on bezel:
   `unit_mesh` and `inner_scale` (1.0, exactly as constructed) are correct:
   the *raw generated solid* itself has a longest-axis extent of only 70 of
   a possible ~200 model-grid units. This is the model under-reconstructing
   an extreme aspect ratio, not an integration bug - the transform math was
   independently confirmed correct on the same case.

2. **Even where the bounding box is close, the interior shape is not.**
   oil_catch has the *best* bbox match of the batch (worst axis 16.6% off)
   and by far the *worst* deviation score (31.14 mm median - the part is
   ~336 mm on its longest axis, so this is ~9% of part size, with the wrong
   internal topology). The envelope being right says nothing about the
   arms/webbing/bosses inside it being right.

**Bottom line: on real scans, once correctly plumbed, cadreasoner-pc is
worse than the deterministic path on every single part tested - not
marginally, mostly 5-7x worse on median deviation.** This directly
contradicts the "primary pick" recommendation above, which was reading
published IoU numbers on clean synthetic benchmarks (DeepCAD 88.8%,
Fusion360 83.3%) rather than measuring real, occluded, cast scans - exactly
the gap "Honest feasibility" already flagged (MCB: 51.3% IoU) before any of
this was run. A tighter tolerance than 0.5 mm was never going to be the
right acceptance bar for a deliberately smooth-faced simplification of a
cast part, but the median-deviation *comparison* is still apples-to-apples
against the deterministic path's own numbers on the same scans, and that
comparison is the one that matters here.

### cadrille — multi-modal, good ensemble partner

```bash
git clone https://github.com/col14m/cadrille && cd cadrille
python test.py --split deepcad_test_mesh --mode pc   # or img, or pc_img
```

Checkpoints `maksimko123/cadrille` (SFT) and `maksimko123/cadrille-rl` (RL,
better). RL fine-tuning code is not released; use the checkpoint. Being
multi-modal, it can take renders as well as points — useful when a scan is too
occluded for the point encoder alone.

### CAD-Recode — fastest, weakest

```bash
git clone https://github.com/filaPro/cad-recode
# run demo.ipynb; preprocessing is 8192 surface samples -> 256 via FPS
```

1.5B, single-shot, no refinement. Good for a quick first guess or as a third
vote in an ensemble. **CC BY-NC 4.0 — personal and research use only.**

### Ensembling them

All three emit executable CadQuery. Run all three, execute each program,
measure each result against the scan with `fairsolid.stages.s70_deviate`, and
keep the best. Costs three inferences and removes most single-model failures,
since they fail on different parts.
