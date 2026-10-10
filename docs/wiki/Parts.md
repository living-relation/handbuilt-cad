# Parts index

[← Home](../../README.md)

Numbers are from the notes in each folder; check those for details.

| Part | Folder | Status | Key numbers | Main files |
|---|---|---|---|---|
| Rear knuckle (cast) | `knuckle/` | **v4 approved** (v4b = fixed copy used for FEA; v5 experiment did not beat v4) | Fit to scan: median 0.66 mm; holes, bearing bore steps, bushing eyes and shock mounts measured (`MEASURED.md`) | `knuckle/v4/knuckle.py`, `knuckle.stl` (STEP is ~250 MB, rebuilt from the script, not in git) |
| Billet knuckle — best | `knuckle_billet/final/best/` | Done | 7075, 2.33 kg, weakest SF 2.00× (cornering), ~6 setups; one inside corner needs a hand-blended radius | `it_final_best.step` |
| Billet knuckle — middle (recommended) | `knuckle_billet/final/middle/` | Done | 2.40 kg, SF 2.33×, ~5 setups | `it_final_middle.step` |
| Billet knuckle — full-arm | `knuckle_billet/final/full-arm/` | Done | 2.43 kg, SF 2.43×, 3–4 setups; control-arm eyes/arms fully solid | `it_final_full-arm.step` |
| Billet knuckle — easy | `knuckle_billet/final/easy/` | Done | 2.46 kg, SF 2.23×, 3–4 setups | `it_final_easy.step` |
| Billet knuckle — two-piece | `knuckle_billet/final/two-piece/` | Passes FEA (joint by hand calc) | 2.42 kg Al + ~0.25 kg bolts, SF 2.33×; tongue bolts on with 3× M12 12.9 + friction shim; tongue from 2.25" plate, body still 6.5" | `main.step`, `tongue.step`, `assembled.step`, `TWO_PIECE.md` |
| Knuckle loads | `knuckle_billet/LOADS.md` | Reference | Fast road, slicks, coilovers, solid bushings: ~1.6–1.8 g cornering/braking + bump | `loads.py`, `loads.json` |
| Dash bezel | `bezel/` | v3 latest | ~50% of surface within 0.5 mm of scan; visor lip simplified, small side clips missing | `bezel/v3/` |
| Pedal adapter | `pedal_adapter/` | Done | Fit median 0.16 mm; 9 mm posts, 3.5 mm holes | `pedal_adapter.py`, `.step` |
| PCV pipe (stock) | `pcv_adapter/` | v3 done | Audi EA888 06H103223A; 53.0 mm long, 21.8 mm ends, 13.0 mm bore, 2 O-ring grooves per end | `pcv_adapter.py`, `.step` |
| PCV pipe −10 AN, 35° / 45° | `pcv_an10/` | Done | Stock O-ring end + angled −10 AN male (7/8-14 UNF modelled threads, 37° flare, no hex); 48.8 / 49.4 mm from stock end | `pcv_an10.py`, `pcv_an10_35.step`, `pcv_an10_45.step` |
| Catch-can reference surfaces | `catch_can_refscan/` | Reference | 9 surfaces, most panel points within ~0.07 mm | `40_ref_surfaces.step` |

Safety factors (SF) are against 7075-T651 yield at the load cases in `LOADS.md`, from linear CalculiX FEA.
