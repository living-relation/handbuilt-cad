# Fabricated knuckle concepts (RH rear, ST185) - geometry stage

owner's rule (2026-10-10 12:10): he approves/changes new versions BEFORE any stress testing or material optimisation.
So this folder holds geometry + interface checks + plain grey renders + fab notes only. **No FEA or sizing has been run.**
Wall/tube sizes below are first-guess proportions (scaled from the billet "middle" section moduli for 4130 with welded
allowables), not checked numbers.

Script: `fab.py A|B|C <stem>` (build123d). Interface constants are read verbatim from ../knuckle_billet.py (OEM v4b),
and the same interface cuts are applied, so all OEM features sit at the v4b positions.

## Concepts
- **A - all-welded 4130 box upright.** Turned housing (OD88 tube + r56 flange ring with 4 bolt bosses), turned eyes,
  ear and ABS bosses. Closed box arms from 3 mm sheet (2 press-braked channels seam-welded), 2.5 mm box ties between
  the eyes, 6 mm bottom closing plate, 8 mm ear webs, plate tongue with crush sleeves, keel gusset under the tongue.
- **B - tube + plate.** Same turned housing/bosses with an 8 mm plate wing flush with the flange top; round 4130
  tubes to the eyes (1.50x0.120 legs, 1.00x0.095 ties and wing-tip braces); same plate tongue and keel.
- **C - hybrid.** Welded 4130 core (housing, wing, ear webs, tongue, keel) + one bolt-on machined 7075-T651 lower
  eye carrier (all 3 eyes + H-section arms + ties on a 14 mm base pad), 6x M10 12.9 into weld nuts under the wing.
  No aluminium is welded.

## Common rules applied
- Strut tongue: 7 mm cheeks whose outer faces are the OEM clamp faces x = +/-15 (faced after welding), 2 crush sleeves
  at the OEM bolt holes. Nothing outside |x| = 15 between y -166 and -60 (bracket ends at y -67), so >= 7 mm
  clearance to the strut bracket envelope at the tongue root; the old billet rib into the tongue root is gone.
- ABS boss: OEM d32 slug, face x = 72 and 17 mm bore at the v4b position, nothing else touches its face.
- Weld assumptions for later FEA (not run): 4130 normalized Sy 435 / UTS 670 MPa; within ~10 mm of a weld use
  0.65 x Sy = 283 MPa; weld toes IIW FAT 71 (fillet) / FAT 80 (full-pen butt) at 2e6 cycles, m = 3.
  Housing bore, eye bores, ear holes, ABS face and tongue faces are all machined AFTER welding (and after
  stress relief if used) in a fixture referenced off the bore.

## Round 1 results (2026-10-10, geometry only)
| | A welded box | B tube + plate | C hybrid |
|---|---|---|---|
| Mass | 4.63 kg 4130 | 4.46 kg 4130 | 3.30 kg 4130 + 0.67 kg 7075 = 3.98 kg |
| vs billet 2.33-2.46 kg 7075 | +2.2 kg | +2.0 kg | +1.5 kg |
| Interface check (27, incl. chunk-18 OEM tongue faces x -13.8/+14.9, ABS face x 67, strut keep-out, clamp envelope) | 27/27 | 27/27 | 27/27 (assembly) |
| Solid | 1 valid solid (welded assy fused) | 1 solid, STL watertight, but OCC is_valid = False (comes from the boolean cuts, not any one part; fix before FEA) | steel core 1 valid solid + carrier 1 valid solid (bolted) |
Renders: fab_<X>_iso / _back / _inboard / _below.png. STEP/STL per concept (C also _steel / _7075 separately).

Mass driver: the turned 4130 housing (OD88 x 66 + r56 flange ring) is ~1.4 kg alone; the steel eyes ~0.6 kg;
the plate tongue ~0.6 kg. Thinning the housing to the bearing-seat minimum is the first thing sizing would attack.

## Fabrication notes (first pass, not sized)
- 4130 normalized plate/sheet: 3 mm (box arms, A), 2.5 mm (ties, A), 4 mm (tongue web/caps, centre web), 6 mm (A closing
  plate), 7 mm (tongue cheeks, faced to the OEM clamp faces after welding), 8 mm (wing B/C, ear webs, keel).
  Tube (B): 1.50 x 0.120 legs (3), 1.00 x 0.095 ties/braces (4). Turned parts: housing (from ~120 mm bar or a
  forged ring), 3 eyes, 2 ear bosses, ABS slug, 2 tongue crush sleeves, 6 weld nuts (C).
- Rough weld length: A ~2.4 m, B ~1.9 m (fishmouthed tube joints), C ~1.4 m. TIG, ER70S-2 (or ER80S-D2), preheat
  ~150 C for >6 mm sections, stress relieve ~620 C if the part is not normalised after welding.
- Jig: fixture plate with a bore mandrel (z axis) + 3 eye-location pins on their OEM axes + 2 pins through the strut
  holes + ear pins. Tack everything on the jig, weld in balanced sequence, then:
- Machine after welding (one fixture, referenced off rough bore + eyes): bearing bore steps and grooves, flange face and
  4 holes, eye bores and end faces, ear holes, ABS face x 67 + 17 mm bore, tongue cheeks to x -13.8/+14.9 and the 2
  strut holes. That holds OEM fitment regardless of weld distortion.
- C: the carrier is a 3-axis part from 2.25" 7075 plate (top/bottom + angle block for the tilted eyes); 6x M10 12.9
  into weld nuts under the wing; needs a friction shim / fitted bolts like the billet two-piece. No Al welding.

## Known shape issues to fix in round 2 (before any FEA)
- A: the two box ties between the eyes are opened by the eye-bore cuts (box interiors show; they need end caps);
  the left-arm-to-eye junction is abrupt; the ear-2 web is long and thin-looking.
- All: the tongue is a plain rectangular box (only its outer edges are radiused); it could taper/flare into the hub.
- B: fix the OCC validity flag. Tubes into the left/right eyes come in at an angle and show trimmed ends.
- No FEA, no sizing: waiting on owner's pick.
