# ST185 rear knuckle, billet 7075-T651: machining notes for the three final variants

All three variants use the it11 layout (hub tube + hybrid flange + solid strut-clamp tongue + three H/solid arms to the
eyes + ear and side bosses), with every interface feature exactly at the v4b numbers (24/24 automatic interface checks).
Each one is a single valid solid: `final/<variant>/it_final_<variant>.step` / `.stl`. Plain grey renders are in the same folder.
FEA: Gmsh second-order tets from the STEP, CalculiX static, 5 load cases from LOADS.md, robust stress (3 mm from loads and supports excluded),
yield 503 MPa. The fatigue case is 1 g + 0.5 g lateral at 10^6 cycles, Goodman R=0.

## Comparison

| | **best** | **middle** | **easy** |
|---|---|---|---|
| mass (7075) | 2.328 kg | **not finished**: 2.37–2.43 kg candidates | 2.462 kg |
| worst SF yield (robust) | 2.00 (cornering, braking 2.03) | 1.96 (web 16) / 1.94 (rib 28×34); rib 30×38 (2.431 kg) still running | 2.23 (cornering) |
| fatigue SF (Goodman / fully reversed) | 5.57 / 3.45 | 5.5–5.8 / 3.4–3.6 | 6.77 / 4.19 |
| arms | H-section, 18 mm pockets each side, 6 mm web, r4 floors | H-section, 13 mm pockets each side, 16 mm web, r4 floors | solid rectangular bars, r6 long edges |
| tongue | pocketed +Z (14 mm) and -Z (12 mm) | pocketed +Z only | solid |
| setups (est.) | 6 (±Z + 4 tilted 3+2) | 5 (±Z + 3 tilted) | 3–4 (±Z + 1–2 tilted for the eye faces) |
| tools | 20/12/8 mm flat + 8 mm (r4) bull, 6 mm ball, drills + boring bar | same as best | 20/12 mm flat, 12 mm r6 bull, drills + boring bar |
| est. complexity / cycle time | high, ~1.0 (reference) | ~0.8 | ~0.55 |

"Easy" came out at 2.46 kg, below the 2.5–2.7 kg Daniel was prepared to accept, because the it11 layout is already lean. Making the arms solid and the tongue solid is what turns the arm pockets into plain profiling.

## What changed from it11 (it_final)
- The 45-degree tongue-root "stand-in" prisms are now **true r10 concave fillets**: a prism with an exact r10 arc profile, tangent to the tongue side face and the flange top. This is built as geometry, not with OCC fillet(), so it never fails.
- Pocket floor corner radius is r4 (it11 used r3). Pocket corners are r6 (pocket_r 6); arm long edges are r4 (easy: r6).
- Flange/arm/lug junction fillets are r6 where OCC can do them (6 of 7 edges on the top face, 8 on the bottom). The edge OCC refuses is
  left sharp in CAD. **Machine it with the r6 bull nose as a blended corner, or break it ≥1 mm.**
- Changes that would drop any case below SF 2: none. best is 2.004 in cornering (robust 251 MPa vs 230.7 in it11). BISECT: fin_bisect (best with the old 45-degree prisms)
  gave 1.91, and best with floor r3 (fin_best3) gave 1.90. So the true fillets *help*, and the cornering value at (45.7, 2.1, 88.5)
  scatters about ±5 % with the mesh. That point is the re-entrant corner where the clamp-to-eye rib passes the Ø90 drive-shaft
  keep-out cut, just above the flange top. best (floor r4 + true fillets) is the passing build: 2.004. **That corner is the one to
  blend by hand (r4–r6 bull nose along the keep-out edge) when machining. It is the part's most critical spot.**

## Minimum wall (wall_check.py, inward ray casting, 40 000 surface samples)
- 99.97 % of samples ≥ 4 mm; the 0.1 % percentile is 4.48 mm in all three variants.
- 8–14 samples come out < 4 mm. They are **not walls**. They are feather edges where the eye end-face spot-face cut (Ø od+12)
  runs out across the bottom of an arm: left eye inner face around (-57…-62, 74, 56) and top eye lower face around (-25, 122, 106).
  In practice that's a 0.2–2 mm sliver along the spot-face edge. **Deburr / 0.5×45° break edge.** (Fix in a later revision: stop the arm 2 mm short
  of the spot-face cylinder.)

## Stock
Part envelope: X 198.5 × Y 330.1 × Z 152.7 mm (Z = hub axis).
- **Stock: 7075-T651 plate, 6.5" (165.1 mm) thick, sawn to 8.5" × 13.5" (216 × 343 mm)**, about 34 kg, so buy-to-fly is about 15:1.
  That leaves ≥6 mm per side for facing and workholding. Tabs and soft-jaw stock come off the tongue end (Y -166) and the top eye end (Y +164).
- Note: 7075-T651 is standard to 6" (152.4 mm) thick, and the part is 152.7 mm in Z. Either use 6.5" plate where available, or 7075-T7351 /
  7050-T7451 thick plate, which has better through-thickness (ST) properties and stress-corrosion resistance and is about 5–10 % lower in yield.
  For 7050-T7451 the SF goes 2.0 → ~1.9 for "best", so best would need re-checking, while easy and middle have margin.
  Orient the plate so the rolling (L) direction runs along Y (tongue to top eye), which is the main bending direction of the arms.

## Setup sequence (all variants; Z = hub/wheel axis, +Z = drive-shaft side)
1. **Op 1, -Z face down (vise or fixture plate on the raw stock):** face +Z; rough the +Z side profile and +Z pockets (arm tops,
   tongue +Z pocket, hybrid flange top, flange-top junction fillets r6 with the 12 mm r6 bull); hub OD and drive-shaft keep-out
   (Ø90 above z66); spot drill and drill the 4 flange bolt holes Ø10.5 through; rough the hub bore. Leave 2 mm on the eye bosses.
2. **Op 2, flip onto soft jaws / a dowelled fixture through 2 of the flange bolt holes:** face -Z to the bore datum; -Z pockets (arm
   undersides, tongue -Z pocket (best only), ear lugs); ear bosses and ear holes Ø10.0 / Ø9.0 (Z direction).
   **Finish-bore the bearing bore and steps in this op** (single setup with the flange face = bearing datum).
3. **Op 3, tombstone / 5-axis 3+2, located on the bore + 1 flange hole:** strut clamp tongue faces (x = ±15.0) and the 2 strut bolt holes,
   X direction, plus the side boss Ø17 hole and the two lower X holes (Ø14.3, Ø14.0).
4. **Ops 4–6 (3+2 tilts, same fixture):** each eye end face spot-face and bore. Left eye: axis X. Right eye: axis tilted 13.6° from X in XZ.
   Top eye: axis tilted 8.7° from Z. The arm H-pockets of best/middle sit in each arm's local frame, so each arm's pockets are cut in that arm's
   tilt. Easy has no arm pockets, so the arm tilts disappear and only the eye spot-face/bore tilts remain: 3–4 setups in total.
- **Undercuts: none.** Every pocket is open to its own ±local-Z face. The drive-shaft keep-out is a plain cylinder from +Z. The tongue-root
  fillets are reachable from +Z with the r10 corner of a 20 mm bull nose, or a 20 mm ball.
- Deep features: arm pockets 18 mm deep × 22 mm wide (best), 13 mm (middle) → 3:1 / 2:1 for a 12 mm tool, OK. Tongue +Z pocket 14 mm in a 18 mm slot.

### Tool list
- 20 mm 3-flute flat end mill (facing/roughing, aluminium HSM); 12 mm 3-flute flat (pocket walls, r6 corners = pocket_r 6)
- 12 mm bull nose r4 (pocket floors r4) and r6 (junction fillets r6, easy-variant edges); 20 mm ball or r10 bull for the tongue-root fillets
- 6 mm ball (edge breaks, deburr); chamfer mill 90°
- Drills: Ø10.5 (flange bolts), Ø10.0 / Ø9.0 (ears), Ø17 / Ø14.3 / Ø14.0 (X holes), with reamer or interpolate if fits matter
- Boring head / fine boring bar for the bearing bore and the eye bores

## Critical tolerances (v4b numbers; bearing and bushing fits are suggestions, confirm against the bearing/bushing part numbers)
| feature | nominal (v4b) | suggested tolerance | datum |
|---|---|---|---|
| bearing seat bore | Ø74.0 (z 13.5–46.0) | **Ø74.0 −0.030/−0.060 (interference for the press-fit outer race; confirm against bearing spec, typ. N7/P7)**, cylindricity 0.01 | A (bore axis) |
| bore steps | Ø75.0 (z −1–10.5), Ø78.0 (10.5–13.5), Ø67.0 (46–50.5), Ø75.0 (50.5–58.5), Ø79.2 (58.5–66), Ø67.0 (66–85) | ±0.05, step faces ⟂ A 0.02 | A |
| bearing shoulder (z 46.0 step face) | z 46.0 | ±0.02, ⟂ A 0.01 | A |
| flange bolt holes ×4 | Ø10.5 at (-55.8,18.1) (-47.5,-34.8) (53.7,-25.1) (51.8,28.9), z 38–82 | Ø10.5 +0.1/0, position Ø0.1 to A/B | A, B (flange face z 82) |
| left eye | c (-79.15, 86.0, 83.0), axis X, Ø35.0 bore, OD 46, length 26 | bore Ø35.0 H7 (spherical / press bush), position Ø0.1, end faces ±0.05 | A, B |
| right eye | c (65.9, 73.9, 112.6), axis 13.6° from X, Ø35.5, OD 46.5, length 26 | as left | A, B |
| top (strut rod) eye | c (-6.6, 138.1, 129.0), axis 8.7° from Z, Ø40.0, OD 52, length 40 | bore Ø40.0 H7, position Ø0.1 | A, B |
| ear holes | Ø10.0 at (-101.5, 29.0) z 40–64; Ø9.0 at (-41.0, -97.0) z 39–70 | +0.1/0, position Ø0.15 | A, B |
| X holes | Ø17.0 at (y 0.9, z 72.5) x 38–72; Ø14.3 at (y -147.5, z 96.2); Ø14.0 at (y -79.0, z 93.7), x -30…25 | +0.1/0, position Ø0.15 | A, B |
| strut clamp faces | x = −15.0 / +15.0, solid clamp lands down to 12 mm below the lower strut bolt | ±0.05, parallel 0.03 | A |
| drive-shaft keep-out | Ø90 above z 66 | ≥ Ø90 (clearance, rough OK) | A |

Finish: Type II hard-coat or chromate conversion after machining. Shot-peen the arm roots and the tongue-root fillets if possible (fatigue).
Inspect: CMM against the STEP. Dye-penetrant check the junction fillets.
