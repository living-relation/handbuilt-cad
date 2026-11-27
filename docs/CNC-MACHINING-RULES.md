# CNC machining design rules

Shop-practice and project rules for CNC machined parts. Source: **Xometry, "Design Guide: CNC Machining"** (38 pages, PDF dated 16 Apr 2025). Page numbers are the guide's own ("N of 38"). The in-repo source is the text conversion [`docs/references/xometry-design-guide-cnc-machining-2025-04-16.md`](references/xometry-design-guide-cnc-machining-2025-04-16.md) (page markers `<!-- pN -->` / `## pN`).

**Scope:** CNC machined parts only. 3D printed parts use the repo's structural-or-critical wall rule, which is never assumed.

**How to use this file.** Keys in the quick-lookup table (`CNC-WALL-METAL`, `CNC-CORNER-R`, …) are the stable names to cite from skills, scripts and reports. One rule per line in the sections below. Inch values are the guide's unless noted as a project rule; mm in brackets are straight conversions unless the guide printed them. Tag anything not confirmed in the PDF as `unverified:`.

**Precedence**
- Project rules in the section below, `AGENTS.md` and `DECISIONS.md` win over the guide.
- These are manufacturability guidelines from one shop, not a standard. The guide's p9 "ISO 2768" label is `unverified:` — the printed table is not ISO 2768-1 medium.
- Rows marked **fail** are failures. Rows marked **flag** are reported for a decision; never auto-fixed, and not an automatic fail.
- The in-repo source is `docs/references/xometry-design-guide-cnc-machining-2025-04-16.md`. The full PDF is not in this repo (files over 1 MB are blocked). It lives in the models folder: `$MODELS_DIR/references/xometry-design-guide-cnc-machining-2025-04-16.pdf`.

## Project rules (the user)

- **CNC-CORNER-R (project):** inside vertical corners are never left sharp. Put the radius in the pocket or profile (tool radius at 1.3× the nearest standard tool, never an exact standard tool size). Do not run a fillet along inside edges or floors unless the function needs a floor radius. (the user, 2026-11-14; guide p14, p36)
- **CNC-THREAD-DEPTH (project):** **1.5× the screw diameter** is the **minimum** thread engagement for tapped holes. Matching holes use the same depth. Under 1.5× is a **flag** in the model check, never a reason to change the drawing. The guide's shop note is thread length **≤ 2× diameter** in metal (p20, p36); the project **never flags** deeper threads. Drawings always call out the actual modeled thread depth on every blind tapped hole, including when it is under 1.5× or over 2×. When the drill/hole is deeper than the thread, both depths are called out. Through holes (plain and tapped) are `THRU` with no depth; depth is only called out for blind holes. If thread depth is unknown, flag it; do not invent a number. No torque or threadlocker notes unless the user asks.
- **CNC-EDGE-BREAK (project):** never auto-apply edge breaks. If chamfers or fillets are already modeled: no prompt and no general note; the drawing annotates their actual dimensions. If they are not modeled and the model has exposed sharp edges that could cut hands, the agent prompts the user. Only if the user approves does the drawing get a leader pointing at those edges: `BREAK ALL EDGES, STD`, or a user-given chamfer length. When breaks are modeled, prefer **45° chamfers**, not fillets. (the user, 2026-11-14; guide p36)
- **CNC-TOL (project):** the drawing title-block defaults in `drawing/dwg.py` (`X ±0.5`, `X.X ±0.2`, `X.XX ±0.05` mm, angles `±0.5°`, Ra 3.2 µm, ASME Y14.5-2018) are the project default. The Xometry table is the shop default if a drawing is silent. A tolerance tighter than **±0.005" (±0.127 mm)** is a **cost flag**, not a fail. Do not call the Xometry table ISO 2768.
- **CNC-INSERT (project):** keep inserts in the assembly and `parts/` model for fit. The STEP sent to the shop is the part without inserts; call out SKU, orientation, depth, face and count on the drawing. (guide p29)

## Quick lookup

| Key | Rule | Fail / flag | Page |
|---|---|---|---|
| CNC-WALL-METAL | Metal walls **≥ 0.030" (0.762 mm)**. Thicker is better; don't design to the minimum. | **fail** if under | p21, p36 |
| CNC-WALL-PLASTIC | Plastic / composite walls **≥ 0.060" (1.52 mm)**. | **fail** if under | p21, p36 |
| CNC-CORNER-R | Inside corner **> 1/32" (0.79 mm)**, as large as possible; **1.3×** the nearest standard tool radius; **never** an exact standard tool size. | **flag** | p14, p36 |
| CNC-CORNER-DEPTH | Pocket depth **≤ 4×** the corner radius. `unverified:` reading of p14 "1:4" and p36 "R depth ÷ R edge ≤ 4". | **flag** | p14, p36 |
| CNC-FLOOR-FILLET | Avoid floor fillets unless needed; if used, smaller than the wall radius. p15 bull-nose vs p36 ball-nose is `unverified:` (guide disagrees with itself). | **flag** | p15, p36 |
| CNC-HOLE-DEPTH | Hole depth:diameter **under 10:1**; **4:1** is optimal (e.g. Ø0.250" × 1" optimal, 2.5" achievable). | **flag** | p17, p36 |
| CNC-HOLE-WALL | Holes and pockets **≥ 0.030" (1/32", 0.762 mm)** from walls in metal; **≥ 0.060" (1.52 mm)** in plastic / composite. | **flag** | p18 |
| CNC-HOLE-PARTIAL | Keep **≥ 75%** of a partial hole inside the part edge. | **flag** | p18 |
| CNC-HOLE-BLIND | Blind holes: add **25%** extra drill depth for the point and chips. Prefer through holes. | **flag** | p18 |
| CNC-THREAD-DEPTH | Minimum engagement **1.5× screw diameter**; matching holes the same depth. The guide's shop note is **≤ 2×** hole diameter in metal (p20, p36); the project never flags deeper threads. Under 1.5× is a **flag** only — drawings still show the actual depths. | **flag** if under 1.5× | project; p20, p36 |
| CNC-THREAD-RELIEF | Blind tap: unthreaded depth **≥ 0.5× diameter** past the threads. Mark drill relief allowable on the drawing; need not model it. | **flag** | p20, p36 |
| CNC-CAVITY | Ideal cavity depth **< 4× width**; over **6× width** is too deep. Use dog-bones / corner reliefs for a square part in a pocket. | **flag** | p19, p36 |
| CNC-EDGE-BREAK | Never auto-applied. Modeled breaks: annotate actual size, no general note. Unmodeled cut-risk edges: prompt; if approved, leader `BREAK ALL EDGES, STD` or a given length. Prefer 45° chamfers. | see project rule | project; p8, p36 |
| CNC-TEXT | Engrave, don't emboss; **20 pt** (≈ 0.278" / 7.06 mm) or larger, sans-serif. | **flag** | p22, p36 |
| CNC-TOL-SHOP | Shop default if the drawing is silent: size/location **±0.005" (±0.127 mm)**; form/orientation and angularity by part length (table below). Plastic typically **2×** metal. Not ISO 2768. | shop default | p9 |
| CNC-TOL-TIGHT | **±0.001" (±0.025 mm)** is readily achievable; tighter needs reaming / grinding and can more than double cost. Flag project dims tighter than ±0.005" as cost. | **cost flag** | p10 |
| CNC-FINISH | As-machined **125 Ra or better**. `unverified:` unit; 125 µin Ra (≈ 3.2 µm) is the US convention. Project title block: Ra 3.2 µm. | shop default | p8 |
| CNC-SIZE | Milled up to **80 × 48 × 24"** (over 24" height: manual review). Turned up to **32" dia × 62" long**. | **flag** | p11 |

## Shop defaults (if the drawing says nothing)

- As-machined finish **125 Ra or better** (`unverified:` unit; treat as 125 µin ≈ 3.2 µm). Tool marks may leave swirls. (p8)
- Sharp edges are **broken and deburred by default**. Edges that must stay sharp go on the drawing. This is the shop's default, not a reason to auto-model breaks or to print a general title-block note. (p8; project rule CNC-EDGE-BREAK)
- Clear plastics come out matte or swirled on machined faces; bead blast gives frost. (p8)
- Tolerances on foam / compressible materials can't be guaranteed. (p8)

### CNC-TOL-SHOP — Xometry table (not ISO 2768)

General, features of size and location: **±0.005" (±0.127 mm)**. (p9; `unverified:` as ISO 2768)

Orientation and form (parallelism, perpendicularity, flatness, circularity, straightness, cylindricity) by part length (p9):

| Part length | Form/orientation | Angularity |
|---|---|---|
| 0–12" (0–305 mm) | ±0.005" (±0.127 mm) | ±0.5° |
| 12–24" (305–610 mm) | ±0.010" (±0.254 mm) | ±0.5° |
| 24–36" (610–914 mm) | ±0.016" (1/64", ±0.406 mm) | ±1.0° |
| 36–60" (914–1524 mm) | ±0.031" (1/32", ±0.787 mm) | ±1.0° |
| over 60" (>1524 mm) | ±0.063" (1/16", ±1.60 mm) | ±1.0° |

Plastics and composites: typically **double** the metal tolerance. (p9)

The project title block stays as in `drawing/dwg.py` (`X ±0.5`, `X.X ±0.2`, `X.XX ±0.05` mm, angles ±0.5°). That is tighter than the shop on two-place dims and looser on integer-mm dims. Put tight or GD&T callouts only on critical features. (p9, p10; project CNC-TOL)

## Size and stock

- Milled parts up to **80 × 48 × 24"** (2032 × 1219 × 610 mm); over 24" (610 mm) machinable height needs manual review. (p11)
- Turned parts up to **32" dia × 62" long** (813 × 1575 mm). (p11)
- Blank (stock) is slightly bigger than the part, e.g. 1" cube → **1.125"** (28.58 mm) cube blank (+0.125" / 3.18 mm). Prefer small, standard blank sizes. (p11)

## Part complexity (cost)

- Put features on axis planes; avoid unneeded draft; avoid contoured / organic shapes. (p13)
- Minimize variation in inside corner radii and thread sizes. (p13)
- One setup, 3-axis is cheapest; more faces / setups cost more. (p13)

## CNC-CORNER-R — inside corner (wall) radii

- Inside vertical corners are never sharp; they get the tool radius. Put that radius in the pocket or profile. Do not fillet inside edges after the fact. (p14; project rule)
- Radius **above 1/32" (0.79 mm)**, as large as possible. (p14)
- **Don't match a standard tool size** (e.g. tool diameter 1/4" or 1/8", or a configured tool radius of 3, 5 or 6 mm): the tool has no clearance and chatters. (p14)
- Corner radius = **1.3× the nearest standard tool radius**. (p14, p36)
- Radius-to-depth **1:4** for pocket radii (p14); poster: "R depth ÷ R edge ≤ 4" (p36). `unverified:` interpretive reading: pocket depth ≤ 4× corner radius.
- Cuts deeper than **2× tool diameter** slow feeds. Tools as small as **0.015" (0.38 mm)** exist but may be too short for the depth. (p15)
- `tools/cnc_check.py` flags concave corners under 1.3× the nearest standard (or configured) tool radius, and corners that exactly match a standard tool size.

## CNC-FLOOR-FILLET — floor fillets

- Avoid unless needed for form/function. Prefer leaving floors sharp. (p15; project rule)
- Floor radius **smaller than the wall radius** where they meet. (p15, p36)
- Use a **standard bull-nose** end mill radius (p15); poster says "standard ball nose" (p36). `unverified:` the guide is inconsistent.

## Holes

- Use **standard drill sizes** (fractional inch like 1/8", 1/4", or whole mm); reuse the same size across features. (p16)
- **CNC-HOLE-DEPTH:** depth:diameter **under 10:1**; **4:1** is optimal. The guide's "diameter-to-depth 1:10" wording is inverted; the 0.250" × 1" / 2.5" example is the authority. (p17, p36)
- **CNC-HOLE-PARTIAL:** keep **≥ 75%** of the hole inside the part edge. (p18)
- **CNC-HOLE-WALL:** holes and pockets **≥ 0.030" (0.762 mm)** from walls in metal; **double (0.060" / 1.52 mm)** in plastic / composite. (p18)
- Drill perpendicular to the surface; add a flat on curved surfaces. (p18)
- Prefer through holes over blind. (p18)
- **CNC-HOLE-BLIND:** add **25% extra depth** beyond what you need, for the drill point and chips. (p18)
- Avoid holes breaking into cavities; if unavoidable, offset the drill axis from the cavity center. (p18)

## Pockets and cavities

- **CNC-CAVITY:** ideal depth **< 4× width**; over **6× width** is too deep. (p19, p36)
- Deeper: make the cavity wider at the top. (p19)
- Square part into a pocket: use **corner reliefs / dog-bones**, not a small radius. (p19, p36)

## Threads and tapped holes

- **CNC-THREAD-DEPTH (project):** **1.5× the screw diameter** is the **minimum** thread engagement. Matching holes are the same depth. Under 1.5× is a **flag** in the model check (`drawing/part.py` `hole_flags`, and the skill). The guide's shop note is thread length **≤ 2× hole diameter** in metal (p20, p36); the project **never flags** deeper threads. Drawings always report actual geometry: every blind tapped hole is called out at its real thread depth (from the modeled thread or `spec['thread_depth']`), even if it is under 1.5× or over 2×. When the hole/drill is deeper than the thread, both are called out, e.g. `M4x0.7-6H ↧6` and `⌀3.3 ↧8`. Through holes, plain or tapped, are `THRU` with no depth. Depth is only called out for blind holes. If `thread_depth` is missing and no modeled thread length is available, flag the user; do not invent a depth from the bore or from 1.5×D.
- **CNC-THREAD-RELIEF:** blind tapped holes add unthreaded depth **≥ 0.5× diameter** past the threads. Combined with 1.5× engagement, drill depth is at least **2.0× diameter**, plus the 25% chip/point allowance on the drill (CNC-HOLE-BLIND). Drill relief need not be modelled, but mark it allowable on the drawing. (p18, p20, p36)
- Use the largest thread the design allows; taps break more **below M2 / #0-80 UNC**. (p20)
- Avoid uncommon / custom threads. (p20)
- Use threaded inserts in soft materials (aluminum, plastics). (p20, p29)
- Drawing gives thread type, hole size, depth, countersinks. (p20)
- Never add torque or threadlocker notes unless the user asks.

## Walls

- **CNC-WALL-METAL:** minimum **0.030" (0.762 mm)**. A thinner metal CNC wall **fails**. (p21, p36; the user, 2026-11-14)
- **CNC-WALL-PLASTIC:** minimum **0.060" (1.52 mm)** (guide's mm). A thinner plastic/composite CNC wall **fails**. (p21, p36)
- Thicker is better; don't design to the minimum. (p36)
- Project rules may set a **stricter** (thicker) minimum; they may not set a looser one. 3D printed walls stay on the structural-or-critical, never-assumed rule in `AGENTS.md` item 7.

## Text

- **CNC-TEXT:** engrave, don't emboss. Laser mark if it needn't be machined. (p22, p36)
- **20 pt or larger, sans-serif** (20 pt ≈ 0.278" / 7.06 mm). Inside corners of letters get the tool radius. (p22, p36)
- Logos / special fonts as vector (DXF), not raster. (p31)
- This is part engraving, not drawing text (`drawing/dwg.py` title-block text height is separate).

## Undercuts

- Size to standard keyseat / form cutters; keep them shallow; make sure the tool can reach them. (p23)

## CNC-EDGE-BREAK — edge breaks

- Never auto-applied by a check, skill, or default pipeline. Tools that add chamfers (`tools/chamfer_batch.py`, `tools/checks/edgebreak.py`, `tools/edge_break.py`) run only when the user explicitly asks to model breaks. (project rule)
- Prefer **45° chamfers**, not fillets. (p36)
- If chamfers or fillets are already in the model: no prompt, no general note; dimension the actual feature.
- If they are not modeled and exposed sharp edges could cut hands: prompt the user (multiple choice). Only after approval, add a leader to those edges: `BREAK ALL EDGES, STD`, or the chamfer length the user gave.
- The shop still deburrs by default if the drawing is silent (p8); that does not add a title-block line.

## Materials (cost)

- Stainless machines at **~½** the rate of carbon steel; aluminum **~4×** faster than carbon steel; plastics faster still. (p25)
- Plastics hold tight tolerances less well and can warp after machining. (p25)

## Inserts

- Follow the insert maker's instructions. Drawing lists SKU, orientation, depth, install face; give insert count per part. (p29)
- **CNC-INSERT:** keep inserts in the assembly / `parts/` model for fit. The shop STEP does not include inserts; call them out on the drawing. (p29; project rule)
- Types: helical (Heli-Coil), key-locking (Keensert), press-fit, heat-set (thermoplastics). (p30)

## Finishes

- Specify by standard, type, class, thickness, color, e.g. `Anodize per MIL-A-8625, Type II, Class 2, Black, 0.0002" thick`. (p32)
- For thick finishes say whether tolerances are **before or after** finish; call out masking (threads etc.). (p32)
- Type II anodize **0.0002–0.0012" (0.005–0.030 mm)**; Type III hardcoat **~0.002" (0.051 mm)**. (p33)
- Chem film **0.00001–0.00004" (0.00025–0.0010 mm)**; Type I gold/brown (hex chrome), Type II clear. (p33)
- Electroless nickel from **0.0001" (0.0025 mm)**, ASTM B733 Type IV, SC1, Class 1. (p33)

## Files to the shop

- STEP is accepted (also SLDPRT, Parasolid, IPT, CATPart, PRT, SAT…). (p37)
- Send the finished part without inserts in the shop STEP (CNC-INSERT).

## What the scripts and skills actually check

| Check | Enforced now | Documented only (flag in the skill / this file) |
|---|---|---|
| `tools/cnc_check.py` (process `machined`, default) | CNC wall floor (metal 0.762 mm / plastic 1.52 mm, or a stricter `--min-wall`); inside corners under 1.3× nearest standard/configured tool radius; exact standard tool sizes; sharp concave corners; setups | hole and cavity ratios, hole-to-wall, thread depth, 45° edge breaks, text, undercuts |
| `tools/cnc_check.py` (process `printed`) | no default wall; `--min-wall` / spec / walls config required or walls are "not checked"; thin spots are candidates to classify | same geometric screen otherwise |
| `skills/cnc-part-check` | CNC walls under the floor **fail**; printed structural/critical walls fail, others flagged; judge the part against this file in step 6 | — |
| `drawing/part.py` `hole_callouts` | actual thread and hole depths on the drawing; through = `THRU` with no depth; missing `thread_depth` flagged, not invented; under 1.5×D recorded in `hole_flags` / `<pdf>.checks.json` | matching-hole same-depth is an agent/project rule; over 2×D is never flagged |
| `tools/checks/holefix.py`, `skills/scan-to-parametric` | thread engagement ≥ 1.5×D | the guide's ≤ 2×D shop note is quoted only; the project never flags deeper threads |

`--strict` still makes `cnc_check.py` exit 1 when anything is flagged or failed. Failures are labelled FAIL in the report even without `--strict`.
