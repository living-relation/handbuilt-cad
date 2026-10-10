# Two-piece bolted knuckle (chunk 15, tp6)

**Split:** the main body (hub and bearing bore, flange, three solid arms and eyes, ears, side boss, ribs) plus a **bolt-on strut tongue**.
The tongue carries the strut clamp, both strut bolt holes and the tongue pockets, and has a foot plate that sits on the flange top at z 82.
The base geometry is **full-arm** (solid arms, no tilted pockets), with the tongue-root fillet set to r5 and the full disc under the tongue widened to |x| ≤ 40.
All 24 v4b interface features check out on the assembly (**24/24**), and each piece is one valid solid.
tp3, the first pass that failed, is kept in `tp3/` for history.

## Changes from tp3
- **Bolts moved off the tongue-root fillets:** 2× M12 12.9 at (±28, −50.5) on a foot widened to |x| ≤ 40, plus **1× M12 on the centreline at (0, −61), counterbored Ø20 down
  through the tongue** (counterbore floor at z 100, so the head sits inside the tongue). All the holes sit 6.5–10 mm from the drive-shaft keep-out (r45) and the
  flange edge (r71).
- Cleaned up the thin slivers at the joint. The tongue now takes everything above the flange top for y < −28 (the old cut at −38 left a 2 mm sliver between the keep-out and the cut).
  It also takes everything beyond the flange disc edge for y < −72 and z ≥ 60. Wall check: the 0.1 % percentile is ≥ 4.48 mm on both pieces. The only spots under 4 mm are the known feather edge at the left-eye spot face and 2 samples on the tongue.
- **Re-mesh check on the suspect tp3 result:** re-meshing tp3 at 4.5 mm gave braking 261 MPa there, not 627. The 627 MPa at the left-arm root was a bad mesh, not a real stress.

## Pieces, stock, axes
| piece | mass (7075) | envelope X×Y×Z (mm) | stock plate | machine / setups |
|---|---|---|---|---|
| main | 1.984 kg | 198.5 × 274.1 × 152.7 | **6.5"** (165 mm) 7075-T651/-T7351, sawn 8.5" × 11.5" | 3-axis. Op 1 +Z (joint face fly-cut flat, 3 bolt holes, arm tops, keep-out), Op 2 −Z (bore + bearing seat, ears, nut spot-faces). **Plus 1 vise turn** (left eye along X, side boss and X holes) **and 2 angle-block setups** (right eye 13.6°, top eye 8.7°): the eye axes are fixed v4b positions |
| tongue | 0.432 kg | 80 × 138 × 51 | **2.25"** (57 mm) plate, 3.5" × 6" | 3-axis. Op 1 +Z (profile, top pocket, counterbore, bolt holes), Op 2 −Z (bottom pocket, joint face). **Plus 1 vise turn** to drill and ream the 2 strut bolt holes (along X) |
| hardware | about 0.25 kg | 3× M12 12.9 (2 fitted/reamed Ø12 H7 shanks as positive location), hardened Ø24 washers, nuts under the flange, a friction shim (µ ≥ 0.5) in the joint | | |
| **total** | **2.416 kg Al** (+ about 0.25 kg hardware) | | stock about 29 + 2 kg (was 34 kg for the single piece) | no 4/5-axis needed; 3+3 setups + 2 vise turns + 2 angle blocks |

## FEA: CalculiX, 5 cases, robust stress, yield 503 MPa (the joint is modelled bonded: both pieces fused, bolt holes open)
| mesh | bump | cornering | braking | combined | fatigue Goodman / reversed | worst |
|---|---|---|---|---|---|---|
| 5.0 mm (tp6) | 7.40 | 2.33 | 2.75 | 2.54 | 6.83 / 4.22 | **2.33** |
| 4.5 mm (tp6m, re-mesh check) | 6.99 | 2.32 | 2.58 | 2.42 | 6.71 / 4.15 | **2.32** |
Both meshes agree. The governing spot is the main body's arm root at the flange top, (−26.1, 55.6, 82), the same as full-arm, not the joint.
The highest stress at the joint is a braking peak at the outer bolt hole edge, (−34.4, −49.2, 82): robust 183–195 MPa.
(tp4, the same layout with the slivers still in, gave 2.38.)

## Joint check (joint_check.py → joint_M12.json; VDI-2230-style hand calc using the real CalculiX strut-bolt reactions from iter/fa2r)
3× M12 12.9: Fv,min 44 kN / Fv,max 70 kN, load factor Φ 0.25. Prying is modelled with the foot pivoting on its compressed edge.
The centroid model, which is more pessimistic, is also in the JSON.
| case | worst bolt pull-off (kN) | bolt utilisation | residual clamp / bolt (kN) | joint shear eq. (kN) | slip SF µ 0.2 (bare) | slip SF µ 0.5 (shim) |
|---|---|---|---|---|---|---|
| bump | 4.3 | 0.77 | 40.7 | 17.2 | 1.47 | 3.69 |
| cornering | 5.5 | 0.77 | 39.9 | 7.6 | 3.47 | 8.69 |
| braking | 2.4 | 0.76 | 42.2 | 24.5 | **1.06** | 2.64 |
| combined | 4.8 | 0.77 | 40.4 | 23.1 | 1.14 | 2.86 |
| fatigue | 1.0 | 0.76 | 43.3 | 4.6 | 5.74 | 14.3 |
- No gapping in any case: the residual clamp stays ≥ 39.9 kN per bolt.
- **Bare aluminium does not hold against slip in braking or combined** (SF 1.06 and 1.14). **Use a friction shim (µ ≥ 0.5) for slip SF ≥ 2.6.**
  Two fitted Ø12 H7 shanks act as a positive backstop: if they took all the shear, τ = 24.5 kN / (2 × 113 mm²) = 108 MPa (12.9 shear strength about 700 → SF 6.5),
  and bearing on the 7075 = 24.5 / 2 / (12 × 16) = 64 MPa (SF > 7).
- Bolt fatigue: Φ·1.0 kN / 2 / 84 mm² ≈ 1.5 MPa alternating, against about 50 MPa allowed. OK.
- Under the heads and nuts: hardened Ø24 washers give ≤ 220 MPa on 7075. OK. Counterbore floor: 5 mm walls either side of the Ø20 counterbore.
- **Not done yet:** an FE contact model (bolt pretension plus frictional contact, µ 0.2 and µ 0.5). It's the next step.
  Plan: mesh main and tongue separately, *CONTACT PAIR (surface-to-surface, penalty) on the foot and flange faces with *FRICTION µ, bolts as B31 beams with *PRE-TENSION SECTION, step 1 preload, then the 5 load steps.

## Getting each piece to ≤ 4" plate
The main body's Z height comes from fixed interfaces. The hub face is at z 0. The strut-rod (top) eye reaches z 152.7, the right eye about z 138, the left eye about z 106, and the tongue z 116.
So **no 2-piece split gets the main body under about 4.2"**. Options:
1. **Horizontal split at the flange top (z 82):** a lower hub + flange + ears piece (z 0–82, **3.5" plate**, 3-axis 2 setups + a vise turn for the side-boss X hole)
   and an upper "frame" piece (arms + eyes + tongue, z 82–153 = 71 mm, **3" plate**, but its eyes still need the vise turn and 2 angle blocks).
   **Problem:** the left eye (z 60–106) and the side boss (z 56–89) straddle z 82, so both would have to move into one piece. That shifts the split plane to z ≥ 106,
   which puts the lower piece back at 4.2–4.5". The joint would also carry *all* of the wheel loads (much more than the tongue joint), with a large bolted flange ring needed.
2. **Bolt-on eye arms (4–5 pieces):** take off the top-eye arm and the right-eye arm as bolted links, each machined lying on its side from about 2" plate with its eye bore
   along that piece's own Z. That gets rid of the angle blocks. The main body then ends at the left eye top (z 106): **4.5" plate**. Taking the left-eye arm off too gives
   hub + flange + ears at about z 82 → **3.5" plate**, which is ≤ 4" for every piece.
   Each piece is then 3-axis, 2 setups, with eye bores straight down Z, plus a vise turn only where a hole truly runs crosswise. The cost is 3–4 extra bolted joints, each needing the same check as the tongue joint.
   That probably adds +0.3–0.5 kg of bosses and bolts, and the eye positions then depend on joint tolerances (they'd need dowels).
**Recommendation:** keep the 2-piece tp6 as the build candidate. Only go to option 2 if plate cost or the angle-block setups matter more than about 0.4 kg and the extra joints.
