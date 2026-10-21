# Chunk 17: finals under the new load geometry (9 in ET-35 at z = -77, RH frame, suspension positions)

Robust von Mises = 99.99th percentile outside the support singular zones, 7075-T651 (Sy 503 MPa). Mesh 3.5 mm C3D10, CalculiX in WSL (~/kb17). Raw results are in loads17/*.json.

| final (mass) | bump @ full bump | cornering @ ride / mid | braking @ ride / droop | combined @ ride / mid | worst yield SF (new) | worst yield SF (legacy loads) | fatigue SF reversed: old 1g+0.5g case / 1 g vertical (scaled from bump) |
|---|---|---|---|---|---|---|---|
| best (2.328) | 3.50 | 2.52 / 2.53 | **2.07** / 2.14 | 2.51 / 2.46 | **2.07** (braking, tongue lower edge -15,-69,77) | 2.00 (cornering) | 9.07 / ~4.7 |
| middle (2.397) | 3.62 | 2.47 / 2.48 | 2.80 / 2.81 | 2.77 / 2.73 | 2.47 (cornering, left-arm root -27,56,82) | 2.33 | 9.87 / ~4.9 |
| full-arm (2.426) | 3.76 | 2.55 / 2.56 | 2.69 / 2.77 | 2.85 / 2.83 | 2.55 (cornering) | 2.43 | 9.69 / ~5.0 |
| easy (2.462) | 3.71 | 2.59 / - | 2.71 / 2.78 | 2.90 / - | 2.59 (cornering) | 2.23 | 9.85 / ~5.0 |

**No final drops below SF 2.** Bump SF fell from about 8 to about 3.6, because the 107 mm vertical-load arm adds a large bearing moment, but bump was never the governing case. Cornering and combined improved, because the outboard vertical load cancels part of the lateral-force moment (Fz*a - Fy*R).

**Hub-face uncertainty is covered.** Stress is linear in the load-point z for each case, so the worst robust stress over any z between the legacy point (+20) and the new one (-77) occurs at one of those two ends. Both ends pass for all four finals (legacy worst 2.00 to 2.43, new worst 2.07 to 2.59). So the Toyota-based hub face (-19, which puts the load point at -54) also passes.

**Fatigue.** The old fatigue case (1 g + 0.5 g lateral) now nearly cancels (13-15 MPa). A 1 g straight-line vertical case is the governing one under the wider wheel. Scaled linearly from the 5 g bump result, it gives about 27-29 MPa, so fully-reversed SF is about 4.7-5.0 (Goodman R0 about 7.7). All are above 1.5.

**One bad run.** The first best/droop run returned nonsense (robust 2267 MPa at the ear-1 boss). An identical rerun gave 234.9 MPa (SF 2.14). It looks like a corrupted solve while three ccx jobs ran at once, and it did not reproduce. Treat any single wild value as suspect and rerun it.

**Not done:** two-piece; mid position for easy.
**Reinforcement if the loads grow further:** best is the only final under about 2.1. Its limit is braking at the tongue lower side edge (-15,-69,77), the same spot as in chunk 4. The fix would be the chunk-14 r8-r10 pad there (padA gave about +10% margin) or keeping the full disc under the tongue root.
