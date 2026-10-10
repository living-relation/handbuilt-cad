# Two-piece bolted knuckle (chunk 14, first pass: **NOT PASSING YET**, work in progress)

**Split:** main body (hub, bearing bore, flange, 3 solid arms and eyes, ears, side boss, ribs) + **bolt-on strut tongue** (the strut clamp
with both strut bolt holes, the tongue pockets, and a foot plate that sits on the flange top at z 82).
Base geometry = **full-arm** (solid arms, no tilted arm pockets), so neither piece needs 3+2 pocketing.
All 24 v4b interface features are checked on the assembly: **24/24**. Each piece is one valid solid.

| piece | mass (7075) | envelope X×Y×Z (mm) | stock |
|---|---|---|---|
| main | 1.981 kg | 198.5 × 274.1 × 152.7 | 6.5" (165 mm) plate, 8.5" × 11.5" (216 × 292 mm), about 29 kg. **Not ≤ 4"** (see below) |
| tongue | 0.412 kg | 68 × 128 × 50 | **2" (50.8 mm) plate**, 3" × 5.5" (76 × 140 mm), about 1.5 kg |
| aluminium total | **2.393 kg** | | was 34 kg of 6.5" stock for one piece; now about 30.5 kg |
| hardware | about 0.25–0.35 kg | 4× M12 12.9 (inner pair fitted shoulder bolts, reamed Ø13 H7), hardened washers; nuts under the flange, or tapped 7075 + steel thread inserts to save about 70 g | |

**Why the main body is still 6.5":** the Z height runs from the hub face (z 0) to the top of the strut-rod eye (z 152.7). Both are fixed v4b interfaces,
so splitting off the tongue does not reduce the main body's stock thickness. Getting to ≤ 4" needs a further split: either a bolt-on strut-rod
eye arm (top eye is z 107–153) or a horizontal split at the flange top (hub + flange about 82 mm = 3.5" plate, arms/eyes about 71 mm = 3" plate). That is the next step.

## FEA (CalculiX, 5 cases, joint modelled bonded, i.e. the two pieces fused with the bolt holes in)
| run | bolts | mass Al | bump | cornering | braking | combined | fatigue Goodman | status |
|---|---|---|---|---|---|---|---|---|
| tp1 | 4× M10 at (±24,−47), (±24,−62) | 2.406 | 7.5 | 2.30 | 2.62 | **2.01** | 6.18 | passes FEA, **but the outer holes break through the r71 flange edge by 0.75 mm, so it's invalid** |
| tp3 (geometry in this folder) | 4× M12 on an r58 arc | 2.393 | 4.7 | 1.69 | **0.80** | 1.84 | 3.59 | **fails** |

What makes tp3 fail:
1. The outer bolt holes (±28, −50.8) cut into the r10 tongue-root fillets, which run from |x| 15 to 25 on the foot top. That leaves a notch at (−23.4, −55.4, 99), which governs cornering, combined and fatigue.
2. Braking reads 627 MPa robust at (−53.6, 46.1, 69.4), at the left-arm root, far from the joint. Nothing changed there between tp1 and tp3, so it's probably a bad mesh. Re-mesh before trusting it.

Fix for the next pass: put the bolts where they don't touch the fillets. Either use 2 bolts per side at |x| ≥ 34 on a wider foot (this needs the flange disc
patch widened to |x| ≤ 42), or counterbore 2–3 bolts down through the tongue on the centreline (long M12 bolts with heads inside the tongue pocket).

The bonded model gives the parts' stresses. The joint itself is checked by hand below from the actual CalculiX strut-bolt reactions
(run iter/fa2r: full-arm deck with NODE PRINT on STRUTO/STRUTI).

## Joint check (joint_check.py, VDI-2230 style; iter/fa2r_joint_M12.json)
4× M12 12.9 on an r 58 arc at (±10, −57.1), (±28, −50.8). That keeps ≥ 6 mm to the Ø90 drive-shaft keep-out and to the r 71 flange edge.
Assembly preload: Fv,min 44 kN / Fv,max 70 kN. Load factor Φ 0.25.

| case | worst external bolt pull-off (kN) | bolt utilisation (of 1100 MPa) | residual clamp / bolt (kN) | joint-plane shear eq. (kN) | slip SF µ 0.2 (bare Al) | slip SF µ 0.5 (friction shim) |
|---|---|---|---|---|---|---|
| bump | 7.7 | 0.78 | 38.2 | 17.3 | 1.97 | 4.9 |
| cornering | 28.7 | 0.83 | 22.5 | 7.7 | 4.6 | 11.5 |
| braking | 3.1 | 0.76 | 41.7 | 25.5 | 1.36 | 3.4 |
| combined | 21.7 | 0.81 | 27.7 | 23.8 | 1.48 | 3.7 |
| fatigue | 4.0 | 0.77 | 41.0 | 4.6 | 7.6 | 18.9 |

- **No gapping** in any case: the residual clamp stays ≥ 22 kN per bolt. The cornering prying moment, from the strut lateral reaction about the bolt group, is the worst case.
- **Slip:** bare Al-Al (µ 0.2) gives only 1.36 in braking, so **use a friction shim (µ ≥ 0.5, e.g. a diamond-coated steel shim) → slip SF ≥ 3.4**. The fitted inner pair is a
  positive backstop: if all the shear went through 2 fitted Ø12 shanks, τ ≈ 113 MPa (12.9: SF > 4) and bearing on 7075 ≈ 90 MPa (SF > 5).
- Bolt fatigue: the alternating force in the fatigue case is Φ·4.0 kN/2 = 0.5 kN → σa ≈ 6 MPa, against about 50 MPa for rolled threads. OK.
- Bearing under the heads and nuts: use hardened Ø24 washers → about 200 MPa on 7075 (the limit pressure is about 400–500 MPa). OK.
- An M10 version was also checked: no gapping, but residual clamp is down to 8.5 kN in cornering and slip SF is 0.92 bare. Not recommended.
- **Not done yet:** an FE contact model of the joint (frictional contact + pretension). The bonded FEA plus this hand calc is the current evidence.

## Machining: axes and setups
**Tongue (3-axis, 2 setups + 1 vise turn):** the plate lies flat with Z = the knuckle Z. Op 1 (+Z): profile, top pocket, foot top, 4 bolt holes (Z).
Op 2 (−Z): bottom pocket, foot bottom face (the joint face, ground or fly-cut flat to 0.01).
**The 2 strut bolt holes run along X, so they need a vise turn (the part on its side in the vise) and a drill/ream.** That's an off-axis hole op, not a 4/5-axis op.
**Main body (3-axis, 2 setups + 3 fixture ops):** Op 1 (+Z): flange top/joint face, arm tops, the 4 bolt holes, keep-out bore. Op 2 (−Z): bore and bearing seat,
ears and ear holes, nut spot-faces. With solid arms there are no tilted pocket ops. **But the three eyes are on fixed v4b axes: the left eye is along X (vise turn),
the right eye is 13.6° from X (13.6° angle block) and the top eye is 8.7° from Z (8.7° sine plate). The side boss and the 2 lower X holes run along X (vise turn).**
So on a 3-axis mill the main body takes 2 setups + 1 vise turn + 2 angle-block setups. Removing those would mean moving interface axes, which isn't allowed.
