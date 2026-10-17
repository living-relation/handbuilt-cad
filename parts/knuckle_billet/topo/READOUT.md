# Topology optimisation read-out (chunk 5)

**Tool:** `topo_simp.py`, my own voxel SIMP code. It minimises multi-load compliance under a volume constraint, using all 5 LOADS.md cases with each case's compliance normalised by its initial value. It uses a density filter (rmin = 2h), OC updates, p = 3, 7075-T651, and pypardiso solves.

**Supports and loads:** the same as the CalculiX runs.

**Design space:** it11 ∪ v4b, closed twice and dilated by 1 voxel, minus these:
- the drive-shaft column
- the bore and every hole
- the eye end-face zones
- the clamp-bracket zone (|x| > 15 for y ≤ -67)

**Non-design solid:**
- hub tube r ≤ 46
- flange bolt bosses r11.5
- ear bosses r12
- side boss r15
- eye tubes
- clamp lands (|x| ≤ 15, y -166..-67, z 72-116)

The non-design solid alone is about 1.01 kg. Interface features are cut into the non-design regions, so a rebuild that keeps these regions keeps the 24 interface checks valid.

## Runs

| Run | Target | Voxel | rho > 0.5 mass | Grey fraction |
|---|---|---|---|---|
| m16_h4 | 1.6 kg | 4 mm | 1.38 kg | 0.31 |
| m20_h4 | 2.0 kg | 4 mm | 1.84 kg | 0.41 |
| m18_h3 | 1.8 kg | 3 mm | 1.68 kg | 0.34 |

The target counts grey material, so the rho > 0.5 mass sits below the target. Compliance optimisation also has no stress limit, so struts that look thin here still need sizing for strength.

The 3 mm, 1.8 kg run is the best-resolved result. It confirms the same layout as the 2.0 kg run. Region by region it keeps:
- 62% of the tongue-side ring, plus a 0.14 kg tongue-root blend
- 25% of the arm-side plate
- 6-10% of the ribs over the drive shaft
- 16-21% of the separate eye arms, with the eye-to-eye frame tie added
- 36% of the ear 2 lug and 16% of the ear 1 lug

## Where material stays vs it11 (design voxels only, 2.0 kg run)

The 1.6 kg run follows the same pattern, just thinner.

- **Tongue root to hub and flange ring on the tongue side: strongly kept.** About 71% of it11's tongue-side ring stays, plus about 0.05 kg of material outside it11 that widens the tongue root into the flange. This matches the it10/it11 braking hot spot: the root needs a broad, smooth blend into the ring.
- **Hub tube outside z < 60: about half kept.** It forms a web from the hub down to ear 2 and the tongue.
- **Lower closed frame: the main new feature.** A continuous tie runs through the left lateral eye, the strut-rod (top) eye and the right lateral eye, with two struts back to the flange and hub. it11 instead has three separate cantilever arms from the flange. The topology run wants a triangle or frame linking the eyes to each other.
- **Ear 2 lug: kept (41%).** Ear 1 lug: mostly removable (19% kept). Ear 1 only needs a slim link.

## Where material can go
- **Ribs from the strut clamp to the lateral eyes over the drive shaft: about 0.22 kg in it11, removed completely (0-1% kept).**
- **Arm-side flange plate: 76% removable.** Only the strips under the arm roots carry load. This is the plate added in it8-it11, which the frame layout makes redundant.
- **Right-eye arm: 86% removable** as a separate cantilever. It's replaced by the eye-to-eye tie.
- **Top-eye arm:** about 83% of the it11 arm goes. The run reroutes it as a strut to the left eye and the hub instead.

## Next step: it13 rebuild in build123d
1. Remove both ribs over the drive shaft.
2. Replace the three cantilever arms with a closed I-beam frame: left eye → top eye → right eye, plus 2 struts back to the flange near the bolt bosses.
3. Shrink the arm-side flange plate to strips under the struts.
4. Blend the tongue root broadly into the flange ring on the tongue side.
5. Slim the ear-1 lug.

Then verify the rebuild with the CalculiX loop, since stress is not constrained here.
