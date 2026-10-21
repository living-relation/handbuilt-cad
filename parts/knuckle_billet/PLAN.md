# Billet knuckle: design plan (chunk 2 onward)

## Goal

A rear knuckle for the ST185, machined from aluminium plate, that bolts on exactly where the v4b knuckle does. It should be lighter than the v4b shape machined solid, and at least as safe for slicks, coilovers and solid joints (see `LOADS.md`).

## Fixed interface (copied from `knuckle/v4b/knuckle.py`, never moved)

- **Hub bore:** 75.0 z0-10.5, **circlip groove 78.0 z10.5-13.5**, bearing seat 74.0 z13.5-46, stop lip 67.0 z46-50.5, 75.0 z50.5-58.5, 79.2 z58.5-66. Hub OD 88 / 94.
- **4 flange bolt holes** 10.5 at (-55.8,18.1) (-47.5,-34.8) (53.7,-25.1) (51.8,28.9).
- **3 eyes** (bore / OD / length / axis), exactly as v4b:
  - left: X axis, (-79.15,86,83), 35 / 46 / 26
  - right: 13.6 deg tilt, (65.9,73.9,112.6), 35.5 / 46.5 / 26
  - strut-rod: 8.7 deg tilt, (-6.6,138.1,129), 40 / 52 / 40
- **Strut clamp holes** (v4b corrected): 14.3 at (y-147.5, z96.2) and 14.0 at (y-79.0, z93.7), X axis.
- **Ear holes** 10.0 at (-101.5,29), 9.0 at (-41,-97). **Side boss hole** 17.0, X axis, (y0.9, z72.5).
- **Contact faces:** eye end faces and the strut clamp faces keep their v4b positions and widths, so the bolt stack-ups don't change.

## Machining concept

- **Stock:** one 7075-T651 plate about 160 mm thick (the hub axis is the plate normal), 210 x 340 mm blank. Order it with certified properties. 6061-T651 is the cheaper fallback, but at the cost of mass (see the baseline).
- **Setups:** 3+2 on a 3-axis mill with a tombstone or a 4th axis:
  - **Op 1 (outboard face, +Z down):** face, outer profile, the outboard pockets and the bearing bore, finished in this setup for concentricity.
  - **Op 2 (inboard face):** flip on soft jaws or a fixture plate that locates on the bore. Do the inboard pockets, the flange holes and the ear holes.
  - **Op 3 (side, X axis):** the strut clamp bolt holes, the side boss, and the lateral-arm eye bores and end faces.
  - **Op 4 (tilted):** the 8.7 deg and 13.6 deg eye axes, using a 4th-axis index or an angle plate.
- **Body:**
  - **Hub ring:** a constant 7-8 mm wall around the bearing seat, with a 10 mm flange ring carrying the 4 holes.
  - **Arms:** I-beam arms from the hub ring to each attachment, with 6-8 mm webs and 8-10 mm flanges. These are the strut clamp (the main vertical and bending path), the two lateral-arm eyes and the strut-rod eye.
  - **Triangle:** a triangulating rib between the strut clamp and the lateral eyes, the main load path in cornering.
  - **Pockets:** blind pockets from both faces with a 4-5 mm floor, so the part stays one piece with no thin skins.
- **Tooling rules:**
  - inside corner radius >= 4 mm (8 mm end mill), >= 6 mm wherever FEA stress > 50 % of the allowable
  - floor-to-wall fillet 2-3 mm (bull nose)
  - pocket depth <= 4 x tool diameter
  - min wall 4 mm, min web 5 mm
  - no undercuts except the circlip groove (turned or thread-milled)
  - break and deburr every edge (fatigue)

## Targets

| Item | Target |
|---|---|
| Mass (7075) | **<= 1.6 kg** (v4b solid 7075 = 2.63 kg; aim about 40 % lighter). Stretch goal 1.4 kg. |
| Static safety factor on yield | **>= 2.0** in the worst case (bump, cornering, braking, combined), ignoring point singularities at the constrained hole edges |
| Fatigue (10^6 cycles, 1 g + 0.5 g lateral, R = 0, Goodman) | **>= 1.5** vs the 0.85-knocked-down allowable |
| Stiffness | bearing-seat tilt under cornering no worse than the v4b solid in 6061 (keeps the bearing, pads and alignment happy) |
| Interface | every feature in the list above within 0.01 mm of v4b (checked automatically from the build script) |

## Iteration loop

1. Build the billet shape in build123d (`knuckle_billet.py`) from the interface list plus a few named body parameters: web/flange thicknesses, pocket depths, corner radii, rib positions.
2. Mesh it with Gmsh (2nd-order tets, refined at the fillets and holes) and run all 5 load cases in CalculiX with the same supports and loads as the baseline (`fea_v4b.py`, reused).
3. Read the stress per region: hub ring, each arm, ribs, pocket floors.
   - Regions above 50 % of allowable: thicken (+1-2 mm web or flange) or grow the fillet radius.
   - Regions below 20 %: pocket deeper or open a window.
4. Repeat until all targets are met, about 4-6 loops. Each loop writes `iterations.csv` (mass, worst SF, fatigue SF, tilt).
5. Check that every interface feature still matches v4b, render the result and send it next to v4b.
6. Before it goes on the car, get a proper engineering review of the real loads, and test a sample of the plate material.

## HARD DESIGN RULES (owner, chunk 17 markup reference/owner_ref_3.jpg). These apply to every future variant and to the smooth remodel.
1. **Strut clamp tongue WIDTH = OEM v4b exactly.** v4b measured the clamp faces at x -14.4..15.2 (one zone) and -16.5..17.0 (the other); the billet currently uses TONGUE_X = (-15, 15). Re-take the exact v4b face positions per zone from knuckle/v4b/knuckle.py / MEASURED.md and add the clamp face x positions to check_interface.py.
2. **More space for the strut.** The rib/block at the tongue root on the flange top (where the clamp-to-eye rib meets the tongue base, around x -25..-5, y -45..-60, z 82-100) intrudes on the strut tube. Cut it back and add a strut-tube keep-out to the builder. Estimate: strut tube OD about 52 mm (to be confirmed from the clamp bracket), centreline over the tongue (x about 0, z about 94), axis about along -Y with the strut inclination, starting above the clamp bracket. Keep-out = tube OD/2 + 5 mm clearance (r about 31) along the tube axis, plus the bracket envelope (two ears either side of the tongue in X over the clamp zone, down to 12 mm below the lower bolt). Nothing may enter it.
3. **ABS sensor mount = OEM exactly.** This is the 17 mm X-axis side hole at (y 0.9, z 72.5) with its boss (billet side_boss_d 32, x 38..72). The mount face position, orientation (normal along X), boss size and the hole must match v4b. Today the interface check covers only the hole; add the face plane x position, its flatness/extent (boss d) and orientation to check_interface.py (needs the v4b face x from the scan model).
4. **No weird cuts.** Remove the odd notch/cut near the right control-arm eye (eye end-face trim notch) and the slot/notch between the lower arms near the trailing-arm eye root. Use continuous smooth shapes (lofted/filleted members, no keep-out notches showing).
