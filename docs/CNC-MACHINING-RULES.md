# CNC machining design rules

Shop-practice rules for CNC machined parts, taken from **Xometry, "Design Guide: CNC Machining"** (38 pages, PDF dated 16 Apr 2025). Page numbers are the guide's own ("N of 38").

**Scope:** CNC machined parts only. 3D printed parts use the repo's own wall rule (critical or structural features only, and never assumed).

- These are the rules for CNC parts. Project rules in `AGENTS.md` and `DECISIONS.md` still win where they're stricter.
- These are manufacturability guidelines from one shop, not a standard.
- Inch values are the guide's; mm in brackets are straight conversions unless the guide printed them.

## Shop defaults (what you get if the drawing says nothing)
- As-machined finish **125 Ra or better** (guide gives no unit; 125 µin Ra is the US convention, about 3.2 µm). Tool marks may leave swirls. (p8)
- Sharp edges are **broken and deburred by default**. Edges that must stay sharp go on the drawing. (p8)
- Clear plastics come out matte or swirled on machined faces; bead blast gives frost. (p8)
- Tolerances on foam / compressible materials can't be guaranteed. (p8)

## Tolerances
- General, features of size and location: **±0.005"** (±0.127 mm). (p9; guide says ISO 2768, values not checked against ISO 2768)
- Orientation and form (parallelism, perpendicularity, flatness, circularity, straightness, cylindricity) by part length (p9):

  | Part length | Form/orientation | Angularity |
  |---|---|---|
  | 0-12" | ±0.005" | ±0.5° |
  | 12-24" | ±0.010" | ±0.5° |
  | 24-36" | ±0.016" (1/64") | ±1.0° |
  | 36-60" | ±0.031" (1/32") | ±1.0° |
  | over 60" | ±0.063" (1/16") | ±1.0° |
- Plastics and composites: typically **double** the metal tolerance. (p9)
- Tight: **±0.001"** is readily achievable; tighter needs reaming / grinding. Can more than double part cost. (p10)
- Put tight or GD&T tolerances **only on critical features**, and call them out on a drawing. (p9, p10)

## Size and stock
- Milled parts up to **80 x 48 x 24"**; over 24" machinable height needs manual review. (p11)
- Turned parts up to **32" dia x 62" long**. (p11)
- Blank (stock) is slightly bigger than the part, e.g. 1" cube part -> **1.125"** cube blank (+0.125"). Prefer small, standard blank sizes. (p11)

## Part complexity (cost)
- Put features on axis planes; avoid unneeded draft; avoid contoured / organic shapes. (p13)
- Minimize variation in inside corner radii and thread sizes. (p13)
- One setup, 3-axis is cheapest; more faces / setups cost more. (p13)

## Inside corner (wall) radii
- Inside vertical corners are never sharp; they get the tool radius. (p14)
- Radius **above 1/32"** (0.79 mm), as large as possible. (p14)
- **Don't match a standard tool size** (e.g. 1/4", 1/8"): the tool has no clearance and chatters. (p14)
- Corner radius = **1.3 x the nearest standard tool radius**. (p14, p36)
- Radius-to-depth **1:4** for pocket radii (p14); poster: "R depth ÷ R edge ≤ 4" (p36). *Ambiguous:* read as pocket depth ≤ 4 x corner radius.
- Cuts deeper than **2 x tool diameter** slow feeds. Tools as small as **0.015"** exist but may be too short for the depth. (p15)
- Note: tools/cnc_check.py currently only requires radius ≥ smallest tool radius (defaults 3/5/6 mm), so an exact r3/r5/r6 corner passes the script but breaks this rule.

## Floor fillets
- Avoid unless needed for form/function. (p15)
- Floor radius **smaller than the wall radius** where they meet. (p15, p36)
- Use a **standard bull-nose** end mill radius (p15); poster says "standard ball nose" (p36). *Inconsistent in the guide.*

## Holes
- Use **standard drill sizes** (fractional inch like 1/8", 1/4", or whole mm); reuse the same size across features. (p16)
- Depth : diameter **under 10:1**; **4:1** is optimal (e.g. Ø0.250" x 1" deep optimal, 2.5" achievable). (p17, p36)
- Partial holes: keep **≥ 75 %** of the hole inside the part edge. (p18)
- Holes and pockets **≥ 0.030" (1/32") from walls** in metal; **double (0.060")** in plastic / composite. (p18)
- Drill perpendicular to the surface; add a flat on curved surfaces. (p18)
- Prefer through holes over blind. (p18)
- Blind holes: add **25 % extra depth** beyond what you need, for the drill point and chips. (p18)
- Avoid holes breaking into cavities; if unavoidable, offset the drill axis from the cavity center. (p18)

## Pockets and cavities
- Ideal depth **< 4 x width**; over **6 x width** is too deep. (p19, p36)
- Deeper: make the cavity wider at the top. (p19)
- Square part into a pocket: use **corner reliefs / dog-bones**, not a small radius. (p19, p36)

## Threads and tapped holes
- Thread length **≤ 2 x hole diameter** in metal. (p20, p36)
- Blind tapped holes: add unthreaded depth **≥ 0.5 x diameter** past the threads. Drill relief need not be modelled, but mark it allowable on the drawing. (p20, p36)
- Use the largest thread the design allows; taps break more **below M2 / #0-80 UNC**. (p20)
- Avoid uncommon / custom threads. (p20)
- Use threaded inserts in soft materials (aluminum, plastics). (p20, p29)
- Drawing gives thread type, hole size, depth, countersinks. (p20)

## Walls
- Minimum **0.030" (0.762 mm) metal**, **0.060" (1.52 mm) plastic / composite** (guide's mm). Thicker is better; don't design to the minimum. (p21, p36)

## Text
- Engrave, don't emboss. Laser mark if it needn't be machined. (p22, p36)
- **20 pt or larger, sans-serif**; inside corners of letters get the tool radius. (p22, p36)
- Logos / special fonts as vector (DXF), not raster. (p31)

## Undercuts
- Size to standard keyseat / form cutters; keep them shallow; make sure the tool can reach them. (p23)

## Edge breaks
- Use **45° chamfers**, not fillets, for edge breaks (cheaper). (p36)

## Materials (cost)
- Stainless machines at **~½** the rate of carbon steel; aluminum **~4 x** faster than carbon steel; plastics faster still. (p25)
- Plastics hold tight tolerances less well and can warp after machining. (p25)

## Inserts
- Follow the insert maker's instructions. Drawing lists SKU, orientation, depth, install face; give insert count per part. (p29)
- **Don't put inserts in the CAD model** sent to the shop; call them out on the drawing. (p29)
- Types: helical (Heli-Coil), key-locking (Keensert), press-fit, heat-set (thermoplastics). (p30)

## Finishes
- Specify by standard, type, class, thickness, color, e.g. "Anodize per MIL-A-8625, Type II, Class 2, Black, 0.0002" thick". (p32)
- For thick finishes say whether tolerances are **before or after** finish; call out masking (threads etc.). (p32)
- Type II anodize **0.0002-0.0012"**; Type III hardcoat **~0.002"**. (p33)
- Chem film **0.00001-0.00004"**; Type I gold/brown (hex chrome), Type II clear. (p33)
- Electroless nickel from **0.0001"**, ASTM B733 Type IV, SC1, Class 1. (p33)

## Files to the shop
- STEP is accepted (also SLDPRT, Parasolid, IPT, CATPart, PRT, SAT...). (p37)
