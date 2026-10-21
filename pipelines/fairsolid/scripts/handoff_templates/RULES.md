# The owner's binding CAD rules

These rules are the owner's. Follow all of them on every CAD job. If a job's TASK file seems to break one,
stop and ask Dan; do not quietly work around it.

Where a rule has a written source it is named ("decision log" = a numbered binding rule in the project
repo's decision log, given to make_handoff.py with --rules-repo / --rules-file). The verbatim text of the
CAD-related lines is in `reference/project-DECISIONS-cad-rules.md`. Rules marked **(the owner, handoff request)**
are stated by the owner when this zip was ordered (2026-10-15); no matching line was found in the repos, so
the nearest written evidence is named instead.

## 1. Parts and versions

1. **Real buyable parts only.** Every part on a parts list is a real part number the owner can buy, with a live
   source link. No "TBD", no "or equivalent", no generic placeholder. If a part cannot be found, do not
   invent one: report it with a multiple-choice fix (A / B / C, your recommendation marked). The one
   exception: the 3D-printed parts themselves, which are listed as the STL / STEP file + material, no buy
   link. (decision log). Prefer parts the owner already has on hand, then TE Connectivity (free samples where possible),
   then the owner's approved suppliers (decision log).
2. **New variants = a new version, never an overwrite.** A different design or a revision goes in its own
   new folder (`rev8\`, `runs\<new job>\`), with its own files. Never edit or overwrite an earlier revision's
   files. Mark which version is the one selected for build. (the owner, handoff request; practice in
   earlier jobs' `rev2 ... rev7` folders; the owner's "separate new version", decision log selected-for-build flag;
   AGENTS.md: never reuse a `runs\` folder.)
3. **Every part is listed with its true file path and a trimetric picture.** Every model gets one row in
   the job's parts list: what it is, status / rev, the full real path of its STEP / STL, and one trimetric
   PNG (same camera and style for all models). the owner must be able to find the file any time he builds it.
   (decision log, decision log.)
4. **Output for the owner = 2D renders: a bottom view and a trimetric view** (PNG), shaded, plus the numbers.
   Not a link to a CAD program, not a screenshot of an unopened file. See `tools/render_views.py`.
   (the owner, handoff request; the rev 7 hanger deliverable `2d_bottom_view.png` + `2d_trimetric.png`.)
5. **Fusion is not used.** Models are build123d scripts. Do not create Fusion documents (the owner has a 10
   editable-document limit, decision log). Keep each job's files inside its own folder; nothing loose at the
   projects root (decision log).

## 2. Printed parts (PA12 powder-bed: HP MJF / SLS)

6. **A printed part is ONE solid. No floating pieces.** Every printed part exports as its own STL + STEP
   and `tools/check_step.py` must report `solids=1 valid=True` for each. Parts that are separate
   physical things are separate files, not extra bodies hiding inside one file. (the owner, handoff request;
   decision log "each printed part is exported as its own STL + STEP".)
7. **PA12 powder-bed rules (decision log):**
   - walls >= 2.0 mm (>= 2.5 to 3 mm where loaded); ribs instead of thick solids;
   - no closed cavity without a powder-escape hole of >= 5 mm;
   - 0.4 to 0.5 mm gap between printed parts that fit together;
   - **no printed threads**: use brass heat-set inserts or captured nuts;
   - every stud / bar / pad joint carries its torque and clamp into metal (studs threaded into the metal,
     hold-downs through brass compression limiters);
   - keep metal parts below the PA12 heat limit (HDT 95 C at 1.82 MPa); keep creepage / clearance between
     live parts.
8. **Stress test = 2x the part's weight load.** Check each load-carrying part for a load of twice the weight
   it carries, applied in every direction that matters, and report peak stress, safety factor and deflection
   in a small table. (the owner, handoff request; rev 7 hanger `SUMMARY.md` section 3: "design load = 2 x pump
   weight = 8.7 N", safety factors 11.3 / 74 / 248.) Do not substitute a harsher or softer load without
   asking.

## 3. Holes, threads, sealing

9. **Through-holes vs threads.**
   - Never cut a hole through a sealing face unless it is a clearance hole for a fitting that seals on it.
   - Tapped holes are blind, tapped from the side that is not a sealing face, and leave wall behind them
     (the hanger leaves 1.8 mm to the outside face). the owner's rule on the hanger: "nothing machined through".
   - In printed parts: no printed threads (rule 7); clearance hole + heat-set insert or captured nut.
   - Machined parts: blind pockets only unless a through feature is truly needed and the owner agreed.
   (Hanger rev 7 `SUMMARY.md` sections 1-2; decision log.)
10. **Sealing faces.** A face that seals (gasket, O-ring, sealing washer) is flat, at least as large as the
    sealing washer, Ra 1.6 or better, on BOTH sides of a pass-through, with the hole edges broken 0.3 mm
    max and no burrs. Leave enough thickness for the fitting's grip range (hanger: 0.4 mm spot faces leave
    7.0 mm). Say on the drawing which faces are sealing faces. (Hanger `hanger_billet.py` header and
    `top_plate_ports.pdf`.)

## 4. Electrical

11. **3 mm live-to-live clearance (decision log).** No two bare live metal parts of DIFFERENT circuits closer than
    3.0 mm, or put a printed barrier between them. Two live parts of ONE circuit are reported but not
    failed (decision log). Live part to plastic or to wire insulation is reported, not failed. Add a gate that
    measures every pair and fails under 3.0 mm.
12. **Crimp-sized terminal holes (decision log).** Every hole a wire and crimped terminal passes through takes the
    crimp barrel: barrel = the larger of the wire insulation OD and the smallest insulation OD the
    terminal is made for, plus the metal on both sides, plus 0.4 mm per side, from the maker's product
    page data. Two holes with less than 2.0 mm of wall between them become ONE slot. Short guide walls
    (2.0 x 3.5 mm) between neighbouring holes help wires leave straight. One wire per terminal unless the
    single terminal and wire are rated for the COMBINED current.
13. **Bend radius (decision log).** Every cable meets a minimum bend radius at every lug, stud and terminal. No
    maker publishes one for these wires, so use FAA AC 43.13-1B paragraph 11-96 aa: **3 x cable OD** where
    the wire is supported at a terminal breakout, **10 x OD** for a bundle. Show the check in a table
    (cable, OD, required radius, radius in the model, pass / fail).
14. **Tinned copper bars are bought as stock** and only cut and drilled (decision log); no milled bars. Every
    mount point uses the listed limiters (decision log). Parts lists cover the box itself, not mount bolts (decision log).

## 5. Fairsolid working rules (AGENTS.md)

15. Always run inside the venv. Never install into the system Python. Do not set `PYTHONIOENCODING`.
16. One new folder under `runs\` per scan or job. Never reuse or overwrite an existing run folder unless the owner
    asks. `runs\` is not committed to git.
17. **Never rescale a scan.** If a size or units check stops a run, report it; do not fix it with a scale
    factor. `fit --units` only picks the hole-size table.
18. Pictures for Dan: the shaded result next to a plain grey scan render from the same angles. No heat maps
    or coloured-deviation images. Still report the numbers (median, p95, % within tolerance).
19. Do not commit memory files or `CLAUDE.local.md`. Do not delete project files unless the owner asks.
