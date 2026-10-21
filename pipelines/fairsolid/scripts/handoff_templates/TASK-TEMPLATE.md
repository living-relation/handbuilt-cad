# TASK: <short job name>

The owner fills this in for each new CAD job and gives it to Grok Bot with the reference files.
Copy this file to `runs\<job>_<MMDD>\TASK.md` and fill every section. Leave a line as `none` if it does not apply.
Read `HANDOFF.md` and `RULES.md` first.

**Date:** YYYY-MM-DD
**Job folder:** `runs\<job>_<MMDD>\`
**Revision to make:** `rev1` (new job) / `revN` (a new version of an existing job: never overwrite the old one)
**Based on revision (if any):** `runs\...\revN`

## 1. Goal

One or two plain sentences. What is the part for, what must it do, where does it go on the car.

>

## 2. Reference photos, scans and dimensions

| What | File path | Notes (what to take from it) |
|---|---|---|
| Scan (STL/PLY) | `C:\...` | e.g. keep flange OD and bolt circle |
| Photo | `C:\...` | e.g. shows the mounting side |
| Drawing / datasheet | `C:\...` or link | |

Dimensions the owner knows are true (mm, say if they are inches). Never rescale a scan to fit these; report a mismatch.

| Dimension | Value | How sure (measured / from datasheet / guess) |
|---|---|---|
| | | |

Interfaces that must not change (mounting holes, bolt circle, connector position, envelope / keep-out):

>

## 3. Parts, with part numbers

Every purchased part must be a real, buyable part number with a live link (RULES 1). List what the owner already has.

| Part | Part number | Maker / source link | Qty | On hand? | Notes |
|---|---|---|---|---|---|
| | | | | | |

Parts Grok should pick (give the need, Grok proposes real options with links, A / B / C, recommendation marked):

>

## 4. Rules that apply

Tick the ones this job must meet (all of `RULES.md` always applies; these are the ones to check hardest).

- [ ] Real buyable parts only (1)
- [ ] New version, nothing overwritten (2)
- [ ] Every part with true file path + trimetric (3)
- [ ] Output = 2D renders: bottom view + trimetric (4)
- [ ] Printed in PA12 powder-bed: one solid per part, wall / cavity / no printed threads (6, 7)
- [ ] Stress test at 2x the part's weight load: weight carried = ____ kg, load directions = ____ (8)
- [ ] Sealing faces / through-holes vs threads (9, 10): sealing faces are ____
- [ ] 3 mm live-to-live clearance (11)
- [ ] Crimp-sized terminal holes (12): terminals / wires = ____
- [ ] Bend radius on cables (13): cables = ____
- [ ] Machined from: ____ (material / stock size) / Printed in: ____

Anything else the owner wants that is not in `RULES.md`:

>

## 5. Deliverables

- [ ] `revN\` folder with the build script (named numbers at the top)
- [ ] One STEP + one STL per part, plus the assembly
- [ ] `hanger_report`-style JSON (mass, clearances)
- [ ] `2d_bottom_view.png` and `2d_trimetric.png` (extra drawings: ____)
- [ ] `SUMMARY.md`: what was built, how each rule was met with numbers, checks, open questions (A / B / C)
- [ ] Parts list with real part numbers + links, and the true path of every model file
- [ ] Other: ____

**Hand back to:** (path / person)
**Needed by:** (date, or "no rush")

## 6. Open questions from the owner to Grok (optional)

>
