# knuckle_billet: working notes

## 2026-10-09 chunk 1 (loads, baseline FEA, plan)

- **Where this ran:** Daniel's PC (WORKSTATION) was offline the whole session, so chunk 1 ran on the agent box in `/workspace/knuckle_billet/`. The PC came back at the end of chunk 1: it was copied to `~/projects/handbuilt-models/knuckle_billet/` in WSL and committed (16f3491). The box copy stays as a backup.
- **Solver:** CalculiX 2.23 (Debian package unpacked into `/opt/ccx`, with a `/usr/local/bin/ccx` wrapper). The PC has 2.21. Gmsh comes from the pip module 4.15 in `/workspace/kbvenv`, ParaView is pvpython 5.13 (Debian).
- **Geometry:** `knuckle/v4b/knuckle.step` (OCC volume 934,760 mm3).
  - Gmsh could not mesh the STEP directly: "1D mesh not closed loop", then "impossible to mesh periodic surface" (lofted cast surfaces). Healing the STEP destroyed the solid.
  - Fallback mesh: v4b STL, MeshFix, isotropic remesh (3.2 mm, adaptive to features), MeshFix again, Gmsh HXT tets, Netgen optimise, 2nd order (C3D10). That gave 219k nodes and 136k tets. 3 zero-volume slivers were dropped (6e-5 mm3 total).
  - The repaired surface encloses about 1.016e6 mm3, about 8 % more than the STEP. MeshFix closed flange holes 1 and 3 and filled some cast recesses, so the baseline is slightly stiffer and stronger than the real v4b. **Mass is reported from the exact STEP volume**, not from the mesh.
  - The hub bore, all 3 eye bores, both strut holes and both ear holes are open in the mesh (checked).
- **Supports and loads:** see `LOADS.md` (all estimates). One linear run serves both alloys: stress is independent of E for these supports, and deflection scales by 68.9/71.7 for 7075.
- **Scripts:** `loads.py` (cases), `mesh_*.py`, `fea_v4b.py` (deck: node sets by geometry from the v4b parameters, rigid bearing ring, caliper torque on the ear holes), `post_v4b.py` (von Mises, SFs, VTU), `render_pv.py`.

## 2026-10-09 chunk 2 (billet iterations 1-3)

- **Build:** `knuckle_billet.py` (build123d) builds the part from primitives: hub tube, bolt-flange ring, solid strut-clamp tongue (clamp faces at x = ±15), H-section arms pocketed from ±Z with r6 pocket corners and r4 long edges, the strut-clamp-to-lateral-eye ribs routed around the drive shaft, and ear and side bosses.
- **Interface:** all 13 v4b interface features (plus the clamp faces) are cut last with the exact v4b numbers. A drive-shaft keep-out (r45 above z66, same as the open column in v4b) is cut too. Every build exports as one valid solid, `iter/itN.step`, which Gmsh meshes directly.
- **Interface check:** `check_interface.py` probes 24 checks against the STL: every hole is open and surrounded by material, the eye end faces sit at ±L/2, and the clamp faces sit at x = ±15. Iterations 1-3 pass 24/24.
- **Junction fillets:** concave edges where arms, lugs and tongue meet the flange faces get an r6 fillet, or r4 where OCC fails, edge by edge. This covers the old braking spike near (-72,10,55) and the it1 spikes at (-26,56,82) and (-63,32,62). It's done one edge at a time, so it's only partial.
- **Pipeline:** `run_iter.sh <stem>` runs mesh_step.py (Gmsh from the STEP, tet10 with straight-sided midnodes; curved ones gave negative Jacobians), then fea_iter.py, CalculiX, post_iter.py and summarize_iter.py, which writes `iterations.csv`. Loads and supports are the same as the baseline (LOADS.md).
- **Renders:** `render_solid.py` makes plain shaded grey images in `renders_iter/` (no stress colours, per Daniel).
- **it2 lesson:** the hub OD must stay > 2 x keep-out radius, and the flange must overlap the hub in z. it2 broke both rules and failed.
- **Results by iteration (7075-T651, robust stress = 99.99th percentile, details in `iterations.csv`):**
  - **it1** (2.36 kg): worst SF is braking at 1.73. Peaks sit at sharp arm-to-flange junctions.
  - **it2** (1.92 kg): failed (hub and flange disconnected, see above).
  - **it3** (2.24 kg): arms 30x38 with 5 mm walls were too weak. Cornering SF 0.81, peak in the left-eye arm.
  - **it4:** it1 sizes plus r6 junction fillets, deep ear lugs tied into the flange (old braking spike), a 48 mm deep left-eye arm, and rib roots moved inside the tongue. The roots moved because the old ones left a sliver face that made Gmsh's surface mesh fail.
- **Script changes during the loop:** before it4 the rib roots were at x = ±12. They are ±4 now, and the it1-it3 STEPs in `iter/` keep the old roots.
- **Mass is still well above the 1.6 kg target.** Next loop: drop the 20 mm full-disc flange for a spoked ring that keeps the 4 bolt bosses, pocket the tongue from below, and give each arm its own size based on its load path.
- **it4 result:** 2.37 kg, worst SF 1.82 (combined). Cornering 1.93, braking 1.89 (it1 was 1.73), bump 6.9, fatigue Goodman 5.8. The new hot spot is the sharp corner where the tongue root meets the flange top, (15,-42,82). It needs an r6-r8 fillet or blend there next.

## 2026-10-09 chunk 3 (iterations 5+)

- **New build parameters** (`knuckle_billet.py`; the it4 script is kept as `iter/knuckle_billet_it4.py`):
  - `flange_style='spoked'`: collar ring of radius `ring_r` plus an r11.5 boss around each of the 4 bolts, replacing the full disc
  - per-arm sizes (`arm_left`, `arm_right`, `arm_top`, `rib_r2`) and movable arm roots
  - `floor_r`: r3 pocket floor fillets, applied where OCC allows
  - `tongue_bottom_pocket`
  - `tongue_junction_r`: an OCC fillet attempt at the tongue/flange top. It never takes, because the edges there are fragments of earlier fillets.
  - `tongue_blend`: a 45 degree fill prism along both tongue side faces at the flange top, the robust stand-in for that fillet
- **it4 per-arm 99.9th percentile stress (MPa):**

  | Case | top arm | ribs | ears | left arm | right arm |
  |---|---|---|---|---|---|
  | corner | – | ≤185 | ≤189 | 153 | 141 |
  | brake | 267 | – | – | – | – |

  For SF 2 the limit is 251 MPa.
- **it5** (spoked ring r56, right arm cut to 28x36, rib_r2 20x26): 2.19 kg but cornering SF fell to 1.16. The hot zone is the right arm and its root at (45..60, 45..75, 75..105), so the right arm needs its it4 section back. Lesson: the full disc was sharing load between the arm roots, so a spoked ring needs the arms kept at full size.
- **it6** (it5 plus tongue blend and tongue z 76-114): built, not run. It was superseded by it7.
- **it7:** it6 with the right arm back to 34x42, ring r60 and rib_r2 24x30.
- **Box memory:** don't run voxel mass-breakdown scripts while ccx runs. The box OOM-killed one at 15.6 GB.
- **it7** (2.22 kg): worst SF 1.53 (cornering). The hot zones are the ring top between the top-arm and right-arm roots, and the right arm near its moved-in root. Braking fell to 1.79 at the tongue bottom side (-14,-68,79), because tongue z 76-114 was too shallow.
- **it8** (2.30 kg): hybrid flange, i.e. a full r71 plate on the arm side (y > -12) and the spoked ring plus bosses on the tongue side, with tongue z back to 72-116. SFs: cornering 1.68, braking 1.78, combined 2.01. The peaks are now in the right arm (47.8,68.6,93.1) and top arm (8,66,99). Moving the roots in (it5-it8) made the arms longer and worse.
- **it9:** it8 with the it4 arm roots restored and the top arm at 34x48.
- **it9** (2.32 kg): cornering 2.32 (first pass), but braking 0.87 and combined 1.21. The peak is at (-29.5,121,105), where the 48 mm-tall top arm meets the trim notch at the top-eye end face. Taller arms run into the eye end-face trim.
- **it10:** it9 with the top arm back to 34x42 and the left arm at 34x48. That is it4's arm set on the hybrid flange.
- **it10, best so far** (2.32 kg): cornering 2.22, combined 2.30, bump 5.5, fatigue Goodman 5.96 (fully reversed 3.68), all passing. Braking 1.84 is the one case short of 2. Its peak is the tongue's lower side edge at (-14.9,-69.1,75), just past the ring on the tongue side. Next fix: add a fill under the tongue's lower side edges where the tongue leaves the ring (like the top-side blend), or keep the full disc under the tongue root.
- **Mass is not converging toward 1.6 kg.** Spoking the flange costs strength faster than it saves mass. To get under 1.6 kg the tongue (about 0.35 kg solid) and hub tube need rethinking (e.g. a C-section tongue with the clamp faces kept as lands), which needs Daniel's answers on the strut-bracket clamp extent.

## 2026-10-09 chunk 4

- **Daniel's answer (strut clamp extent):** the strut clamp bracket covers only the 2 strut bolt holes (y = -147.5 and -79), down to 12 mm below the bottom bolt (the one nearer the hub). I've taken that as y ≈ -67 measured from the bolt centre, with the clamp zone running from the tongue tip (y -166) to y ≈ -67. If he meant 12 mm from the hole edge, it ends at y ≈ -60. This zone stays full solid clamp lands at x = ±15. A C-section is allowed only between the clamp zone and the flange, y ≈ -67 to the ring.
- **Braking fix, option A (it11):** keep the full r71 disc under the tongue root, |x| ≤ 30, y < 0.
- **Braking fix, option B (it12):** a ramp under the tongue from the ring bottom out 24 mm along the tongue bottom, flared 7 mm past each side face.
- **Results:**
  - **it11 (option A) is the pick:** 2.327 kg (+10 g vs it10). SFs: bump 7.43, cornering 2.18, braking 2.00, combined 2.33. Fatigue Goodman 5.97, fully reversed 3.69. Interface 24/24, one valid solid.
  - **it11 margin:** braking only just passes (robust 251 MPa against a 251.5 limit). The peak moved to the patch edge at (-15.1,-69.4,75.8), where the r71 patch ends under the tongue's lower side edge.
  - **it12 (option B):** braking 1.83, rejected. The ramp mostly overlapped the existing under-tongue gusset, and its flare edges at y = -70 added a notch.
- **Next steps:**
  1. Give braking more margin by blending the patch edge into the tongue, e.g. a fillet or a chamfered patch end at r71. Keep it inside |x| ≤ 15 past y -67 so it stays clear of the clamp bracket.
  2. Make the tongue a C-section only between the clamp lands (y ≤ -67, kept solid) and the flange. The free tongue length is short (about y -67 to -60), so the C-section mass gain there is small. Most remaining mass is in the solid clamp zone, which must stay solid. The real mass lever is the hub tube and arms.

## 2026-10-09 chunk 5: topology optimisation

- **Tool:** my own voxel SIMP code, `topo_simp.py`, on the box in `/workspace/kbvenv`. It uses hex8 elements, multi-load compliance minimisation with a volume constraint, a density filter (rmin = 2h), OC updates with move limit 0.15, penalty p = 3, and pypardiso (MKL) direct solves for all 5 load cases at once. Each case's compliance is normalised by its initial value.
  - **Why not BESO / ToOptix on CalculiX:** they would need 5 CalculiX solves per iteration on a re-meshed part (about 3-4 min per iteration here). The voxel solver does one iteration in about 1-15 s.
  - **Supports and loads:** they mirror `fea_v4b.py` exactly. The bearing seat is a rigid ring carrying the tyre force and moment, distributed through the inverse polar inertia so the resultant is exact. Strut bolts are fixed xyz, the lateral eyes fixed in z, the top eye fixed in x, and brake torque goes into the 2 ear holes. Material is 7075-T651, E = 71.7 GPa.
- **Design space:** voxels inside it11 or the repaired v4b, closed twice and dilated by 1 voxel, minus these:
  - the drive-shaft column (r < 45 above z 66)
  - the bore
  - every hole
  - the eye end-face zones
  - the clamp-bracket zone (|x| > 15 for y ≤ -67, from Daniel's answer)
- **Non-design (forced solid):**
  - hub tube r ≤ 46
  - r11.5 bosses around the 4 flange bolts
  - r12 ear bosses
  - r15 side boss
  - full eye tubes (OD × length)
  - solid strut clamp lands, |x| ≤ 15, y -166..-67, z 72-116
- **Runs** (launched detached with setsid nohup, logs in `topo/*.out`):
  - `m18_h3`: 1.8 kg, h = 3 mm
  - `m16_h4`: 1.6 kg, h = 4 mm
  - `m20_h4`: 2.0 kg, h = 4 mm
- **Machinability bias:** none in this pass. A two-sided milling (±Z no-undercut) projection would be next. Minimum member size comes from the filter radius (2h = 6-8 mm), which meets the ≥ 4 mm rule.
- **Post-processing:** `topo_post.py` makes the iso-surface (rho = 0.5) STL and a read-out of material by region against it11.
- **Topo results** (full read-out in `topo/READOUT.md`):

  | Run | Target | rho > 0.5 mass | Grey fraction | Iterations |
  |---|---|---|---|---|
  | m16_h4 | 1.6 kg | 1.38 kg | 0.31 | 70 |
  | m18_h3 | 1.8 kg | 1.68 kg | 0.34 | 70, about 15 min |
  | m20_h4 | 2.0 kg | 1.84 kg | 0.41 | 70 |

  All three show the same layout:
  - the tongue root blends broadly into the tongue-side flange ring
  - the ribs over the drive shaft are removed
  - the arm-side plate is mostly removed
  - a closed frame ties left eye, top eye and right eye together, with 2 struts back to the flange and hub
  - the ear-2 lug stays and the ear-1 lug slims down
- **Renders:** `renders_iter/topo_m16|m18|m20_{iso,back}.png`, plain grey rho = 0.5 iso-surfaces.
- **Memory:** `trimesh.contains` on about 100k points got OOM-killed while the h3 run was going, so `topo_post.py` uses voxelisation now.
- **Next:** it13 rebuild in build123d (frame layout, see `READOUT.md`), then verify with CalculiX. Ideas for the next topo run:
  - a stress-aware pass (p-norm) or a higher volume fraction, so struts come out strength-sized
  - a ±Z milling (no-undercut) projection for machinability
  - p-continuation and Heaviside projection to cut the 31-41% grey
- **Not done:** it13 wasn't started (time).

## 2026-10-09 chunk 6: it13 frame layout (from the topology read-out)

- **New options in `knuckle_billet.py`** (the it11 script is kept as `iter/knuckle_billet_it11.py`):
  - `layout='frame'`: struts from the flange to the left and right lateral eyes, plus a closed I-beam frame, left eye → strut-rod (top) eye → right eye. The separate top-eye arm is gone.
  - radial strips under the 2 strut roots, at flange depth
  - `ribs=False`: drops the strut-clamp ribs over the drive shaft
  - `ear1_link_w`: makes ear 1 a slim link with no deep lug. Ear 2 keeps the deep lug, which is the hub web toward ear 2.
  - Flange: the spoked ring r60 with 4 bolt bosses comes back, and the arm-side plate is removed.
  - Tongue root: the broad blend is the full disc patch widened to ±40 plus the 12 mm 45° side blend.
- **it13 starting sizes:**
  - struts: left 34x44, right 34x42
  - frame members: 30x36
  - strips: 26 wide
  - ear 1 link: 16 wide
- **it13 build:** 1.90 kg (7075), one valid solid, interface 24/24.
- **it13** (1.90 kg): bump 4.75, cornering 0.99, braking 0.51, combined 0.69. The ear-1 slim link failed under braking (robust 983 MPa at (-55,23,42)): the brake torque reaction needs the deep ear-1 lug, even though compliance-based topology called it removable. Cornering hot spots are at the left strut root and ear-1 corner (-75..-60, 15..45, 60..82) and at the right strut root (30..45, 45..60, 75).
- **it14** (2.01 kg): ear-1 deep lug back, strips 40 wide, ring r63, left strut 34x48. Braking recovered to 1.84, but cornering is 0.96 and combined 1.07, with the hot spot at the left strut root (-75..-60, 30..45, 60..82).
  - The first it14 build (strips 44, ring r63→64) came out as 3 solids and was invalid. The interface check caught it before any FEA ran.
- **it15** (2.05 kg): hybrid arm-side plate instead of strips. Cornering 1.11, and braking 0.78 at the frame/top-eye junction (18,137,137), so the 30x36 frame members are too small for the strut-rod braking load.
- **it16:** it14 plus a second left strut (26x32) from the flange/ear-1 corner to the left eye, which is it11's old rib-2 path, and frame members at 34x40.
- **it16** (2.08 kg): worse, not better. Cornering 0.65 and braking 0.61, with peaks at (-65.6,57.9,75.9) and (-35,53,80) where the second left strut, the left strut and the frame meet. It is probably a junction notch from overlapping H-pockets or partial fillets. I didn't have time to debug it.
- **Frame layout conclusion so far:** none of it13-it16 reaches SF 2. The compliance-only topology result under-sizes the strength-critical paths: the ear-1 lug, the left-eye root, and the strut-rod braking path into the frame. Turning the frame into a build123d model needs solid gusseted nodes at the eyes and roots (not H-pocketed bars just overlapping), or a stress-constrained topology run.
- **it17:** it11 with `ribs=False` only, i.e. the topology run's clearest finding applied to the proven design. 2.05 kg (-0.28 kg vs it11), interface 24/24.
- **it17 result:** cornering 1.31, braking 1.70, combined 1.38, bump 5.4, fatigue Goodman 4.5. Removing the drive-shaft ribs costs a lot of strength: cornering drops from it11's 2.18 to 1.31. So the compliance-only topology run's "ribs removable" finding is wrong for strength. The ribs carry the cornering moment from the left/top arm roots (-26,56,82) round to the strut tongue.
- **Status after chunk 6:** it11 (2.33 kg) is still the only design with SF ≥ 2 in every case. Best frame candidate: it14, 2.01 kg, worst SF 0.96.
- **Next:** a stress-constrained (p-norm von Mises) topology run, or SIMP with the it11 ribs and the ear-1 lug as non-design. Then either rebuild the frame with solid gusseted nodes and verify, or lighten it11 locally (pockets in the ribs instead of removing them).

## 2026-10-09 chunk 7: lighten it11 (track B) + stress-aware topology (track A)

- **B: new options in `knuckle_billet.py`:**
  - `rib_size`: makes the clamp-to-eye ribs pocketed I-sections
  - `rib_inner_solid`: keeps the 2 inner rib segments solid. They skirt the r45 drive-shaft keep-out, so a pocket there opens into the keep-out and leaves slivers.
  - `hybrid_pockets`: top pockets in the arm-side plate. The pocket is now 20x10 r4.5; 20x9 failed because it was not more than 2r.
- **it19** (2.25 kg): ribs 28x34 pocketed on all 4 segments, plate pockets at 72/118/182°, and 5 mm walls/webs everywhere. Braking collapsed to 0.34 (robust 1490 MPa at (-37,-32,83), where the inner-rib pocket breaks into the keep-out). Cornering fell to 1.63 at the left-arm underside (-64,58,76) from the 5 mm walls. Rejected.
- **it18** (it19 with 6 mm walls): its ccx was OOM-killed while the topology run was going. It was superseded by it20.
- **it20:** it18 with the inner rib segments kept solid, so only the outer rib segments (to the eyes) are pocketed 28x34. 2.30 kg (-25 g vs it11).
- **A: `topo_simp_v2.py`:**
  - The it11 ribs (4 segments, 24x30) and the ear-1 deep lug are locked as non-design solid.
  - It adds a stress-aware heuristic: per-case weights scale with the p-norm (p = 8) relaxed von Mises from element-centre stresses, raised to the power 2, and the sensitivities are amplified by (1 + (σ/251)²).
  - Run `s21_h4`: 2.1 kg target, 4 mm voxels, 60 iterations. rho > 0.5 mass is 1.82 kg, grey 0.37, and the change never settled (it stayed at 0.15 because the weights move every iteration).
  - At rho = 0.5 the strut-rod eye ends up disconnected, so the heuristic isn't reliable. A real p-norm stress constraint with adjoint sensitivities (MMA) is needed.
  - What it still shows: the arm-side plate is mostly removable (16% kept), and once the ribs are locked the tongue-side ring and ear-2 lug carry little (2-14%).
  - Render: `renders_iter/topo_s21_{iso,back}.png`
- **it20 result** (2.30 kg): cornering 1.58, braking 1.94, combined 1.85, bump 6.7, fatigue Goodman 5.2. The cornering peak at (-64.5,57.3,75.8) is where the pocketed outer left rib (L2) merges into the left arm underside. It's the same spot as it16's second left strut. Pocketing L2 makes a notch at its pocket-floor edge, so L2 stays solid.
- **it21** (it20 plus hub OD90 and ring r58): stopped. It still had the L2 notch.
- **it22:** it11 with plate pockets 72/118/182°, hub OD 90 (5.4 mm wall at the 79.2 seat) and ring r58. Ribs unchanged. 2.267 kg (-60 g vs it11).
- **it22 result** (2.267 kg): cornering 1.71 (peak (16.2,68.8,82), where the 72° plate pocket notches the top-arm root), braking 1.90 (tongue patch edge; the smaller ring/hub costs margin there), combined 2.24. Rejected.
- **it23:** it11 with hub OD 90 and plate pockets at 118/182° only. The 72° pocket is dropped and the ring stays r60.
- **it23 result** (2.274 kg): cornering 1.84, braking 1.89, combined 1.98, bump 7.25, fatigue Goodman 5.4. Not passing. The thinner hub (OD 90) takes margin from braking at the tongue patch edge (-15,-69,76) and from cornering at the top-arm root (-24,52,82).
- **Chunk 7 conclusion:** it11 (2.327 kg) is still the lightest design with SF ≥ 2 robust in all cases. Every local lightening tried here (pocketed ribs, plate pockets, thinner hub, smaller ring, 5 mm walls) dropped at least one case below 2. it11's margins are only 2.00 (braking) and 2.18 (cornering), so there is almost no slack to trade.
- **Next:**
  1. Add strength before cutting weight. Fillet the tongue patch edge at (-15,-69,76) and the top-arm root at (-26,56,82); they are the two governing spots in every variant.
  2. Then retry the hub OD90 and plate-pocket savings (about 0.05-0.06 kg) on top.
  3. A proper stress-constrained topology run (p-norm with adjoint sensitivities and MMA) is still the route to a step change in mass.

## 2026-10-09 chunk 8: stress-constrained topology optimisation (multi-session)

- **Code:** `topo_stress.py`. It reuses `topo_simp.py`'s setup (grid, design space, non-design solids, supports, loads) by exec'ing its setup section.
  - Problem: minimise design volume subject to a stress constraint in each of the 5 cases.
  - Stress measure: qp-relaxed von Mises (σ_e = x̄^0.5 · σ0_e), aggregated per case with a p-norm (p = 8) and adaptively normalised so it tracks the maximum (c_k = max/PN, re-set every 10 evaluations, damped 50/50).
  - Sensitivities: adjoint (one extra solve per case, sharing the pardiso factorisation).
  - Filter and projection: density filter (rmin = 2h = 8 mm, which meets the ≥ 4 mm minimum member) and Heaviside projection with β = 1 → 2 → 4 → 8.
  - Optimiser: MMA from nlopt (LD_MMA).
  - Non-design: as in topo_simp. The ribs and the ear-1 lug are not locked, so the optimiser decides.
  - Elements touching support or load node sets (+1 voxel) are excluded from the stress measure, like the robust 3 mm exclusion in the CalculiX post-processing.
- **Validation against CalculiX on it11** (h = 4 mm voxels, `topo/validate_h4.json`), as the voxel 99.99th percentile divided by the CalculiX robust value:

  | Stress location | bump | corner | brake | combined | fatigue |
  |---|---|---|---|---|---|
  | element centre | 0.54 | 0.49 | 0.44 | 0.49 | 0.41 |
  | Gauss points | 0.82 | 0.76 | 0.66 | 0.66 | 0.60 |
  | element corners (SPT=1) | 1.03 | 1.02 | 0.89 | 0.80 | 0.80 |

  - With corner stresses, the voxel maximum vs CalculiX robust is 1.43, 1.06, 1.04, 0.93 and 0.82.
  - Adopted: corner stress, maximum over the 8 corners, with the governing corner used in the adjoint. The allowable is 230 MPa instead of 251, which covers the 8-20% under-prediction on combined/fatigue.
  - Bump, corner and brake are within 15% at the 99.99th percentile; combined and fatigue are about 20% low.
  - Linear hex8 elements are stiff in bending (shear locking) and centre stress is averaged, hence the low ratios in the first two rows.
- **Run `sc_h4`:** h = 4 mm, 20 evaluations per β stage, detached on the box. The log is `topo/sc_h4.out`; its "smax/251" column is actually divided by S_ALLOW = 230.
- **Run 1 (`sc_h4`)** started all densities at 0.7 and restarted MMA every 10 evaluations, 80 evaluations in all (5 min).
  - Not converged. Each restart resets the MMA asymptotes, so mass jumps between about 2.0 and 2.6 kg. At the evaluations near 2.09 kg all stress ratios were ≤ 0.85 of the 230 allowable, so the constraint never became active.
  - Saved result: rho > 0.5 mass 2.016 kg including the 1.01 kg non-design. Grey fraction is still 0.56, so it is not crisp.
  - Connectivity (`topo_connect.py`, 26-connected): 2 components, the main one holds 99.8% of the material and 100% of the non-design. The other is a 3 g island.
- **Where run 1 puts material** (`topo/sc_h4_readout.json`, it11 kept fraction):
  - hub-tube outer web toward the ears: 82%, plus a lower frame through the 3 eyes (as in the compliance runs)
  - tongue root: 28%; tongue-side ring: 36%; arm-side plate: 30%
  - ear 1: 28%; ear 2: 23%
  - clamp-to-eye ribs over the drive shaft: 2-3%, i.e. removed again
- **Caution:** this contradicts the CalculiX it17 result, where removing the ribs dropped cornering to SF 1.31. The voxel model under-resolves notch stresses at junctions, so any rebuilt solid must be verified in CalculiX.
- **Render:** `renders_iter/topo_sc_h4_{iso,back}.png`
- **Run 2 (`sc2_h4`, started 21:20 on the box, detached):** densities start at 0.5, one MMA run of 40 evaluations per β stage (c_k fixed within a stage), 160 evaluations total (about 11 min). Log `topo/sc2_h4.out`; it saves `topo/sc2_h4.npz` every 3 evaluations.
- **Plan for the next chunk:**
  1. Check sc2 convergence, i.e. whether the stress constraint is active at about 1.0 of the allowable. If not, give MMA more evaluations per stage and raise β to 16-32 for a crisp 0/1 result. Consider h = 3 on WSL, whose memory is separate from the box.
  2. Recalibrate the allowable after a CalculiX check of the first rebuilt solid.
  3. Optionally add a ±Z milling (no-undercut) projection.
  4. Rebuild the converged layout as a build123d solid (it24) with solid gusseted nodes and ≥ 6 mm fillets at junctions, then verify with the 5-case CalculiX loop and the 24 interface checks.

## 2026-10-09 chunk 9

- **sc2_h4 (box):** stalled after 27 evaluations, with the log frozen for several minutes under box memory pressure (the balloon driver reported "Out of puff"). I killed it.
  - Last saved state: β = 1, rho > 0.5 mass 1.90 kg, all cases ≤ 0.8 of the 230 allowable. Not converged and still grey, so not rendered (renders are for crisp results only).
- **sc3_h4 (WSL, detached, about 3 s per evaluation):**
  - Setup: `topo_stress.py` with β stages 1, 2, 4, 8, 16, 50 MMA evaluations per stage, densities starting at 0.45.
  - Fix: `x̄^(q-1)` became NaN at x̄ = 0, so the explicit sensitivity now uses `max(x̄, 1e-6)`. The box copy has the same fix.
  - Environment: pypardiso, nlopt, trimesh, rtree and scikit-image installed into `~/simvenv` (the first pip attempt hit an SSL error; the retry worked). `baseline/v4b_fixed.stl` and `iter/it11.stl` were copied to WSL for the design space.
  - Status at report: β = 1 stage, evaluation 42, 1.75 kg, all cases ≤ 0.87. Log `topo/sc3_h4.out`, saved every 3 evaluations to `topo/sc3_h4.npz` (WSL only). Expected to finish about 10 minutes after the report.
- **it24 / it25 (frame layout from the topology runs):** it14 frame plus solid gusset ties closing both strut-frame triangles, frame members 34x42, and a thicker hub web. Hub OD is 100 for it24 and 94 for it25.
  - Gmsh's default 2D algorithm failed on overlapping boundary facets (surfaces 122/132). Meshing with `ALG2D=1` (MeshAdapt) plus HXT works; `run_iter.sh` passes the env through.
  - **it25** (2.098 kg): bump 4.64, cornering 0.95, braking 1.56, combined 0.91, fatigue Goodman 3.12 (fully reversed 1.93). It fails at the ear-1 lug / flange-ring top corner (-64.7,31.3,82), the same frame-layout weak spot as it14/it15.
  - **it24** (2.25 kg): CalculiX was still running on the box at report time.
- **it26** (it25 plus the left ribs back via the new `ribs_left` option): the boolean fails (3 solids, invalid), with and without the left tie. Not run.
- **Conclusion so far:** the frame layout needs the left rib path. It is the load path from the left strut root to the ear-1 lug corner. Every topology run removes it, and CalculiX says it is needed.
- **Next chunk:**
  1. Take sc3's crisp result (β 16) and render it.
  2. Fix the it26 boolean, e.g. by moving the L2 rib end off the strut axis, or by building the left rib as one merged gusset plate.
  3. Then verify with CalculiX.
  4. Or recalibrate the voxel allowable around this junction, e.g. a junction stress-concentration factor of about 1.5, so the optimiser keeps the rib.
- **it24 result** (2.247 kg, hub OD 100): bump 5.19, cornering 1.07, braking 1.52, combined 0.95, fatigue Goodman 3.43. It fails at the same ear-1 lug / flange-top corner as it25.

## Chunk 10 (2026-10-09 evening)
- **sc3_h4** (stress-constrained SIMP, h=4, betas 1-16): converged and feasible at beta 8 (≈1.47 kg thresholded, voxel smax/251 ≈0.82 in all cases), then the first MMA step at beta 16 went NaN (ev 203) and the final npz is NaN. **Not crisp, not rendered.** Fix added to topo_stress.py: NaN guard (revert the step and end the stage) and a snapshot per beta stage (`<out>_b<beta>.npz`).
- **Junction SCF**: topo_stress.py now takes `KT` and `KT_R` env vars: design voxels within KT_R voxels of any non-design interface solid get stress ×KT (in both the explicit and the adjoint terms). Run **sc4_h4_kt** (KT=1.5, r=2, betas 1-8, SALLOW 230, SPT=1): 1.49-1.53 kg, one connected component, about 33 % grey, so not crisp and not rendered. It did **not** keep the left rib path: the left-gusset zone holds 0.042 kg of solid against 0.071 kg in sc2. Conclusion: a uniform junction SCF doesn't bring the left rib back. The next try is to lock the it26 gusset zone as non-design, or to use a stress limit that varies by region.
- **it26 fixed**: replaced ribs_left with one merged gusset plate (`left_gusset`: polygon tongue root -> ear-1 corner -> left strut root -> left eye, z78-96, 10 mm top pocket, 6 mm walls, r6 vertical edges). Result: 1 valid solid, 24/24 interface checks, 2.171 kg, worst SF 1.40 (it25 was 0.91).
- Sizing loop: it27 (gusset z70-100) 1.56; it28/it29 (bigger left frame, left arm, right arm) 1.45/1.58; it30 (right arm 38x52) 1.64; it31 (38x58) 1.65. The cornering peak doesn't move: it sits at (31.8,54.4,82) on the spoked ring (r=63) at the flange top, next to the right-arm root, so making the arm bigger doesn't help.
- Booleans are fragile: frame_lt at 40 wide, any tie into the flange top, moving right_root, and hybrid with sector_y -12 each give multiple solids. it33 = it30 + hybrid flange plate for y>25.
- it33 (it30 + hybrid flange y>25): worst SF 1.45. The cornering peak just moves to the plate edge at (52.7,23.7,82). This variant is worse.
- **Best of chunk 10: it30, 2.301 kg, worst SF 1.64 (cornering). No passing design yet.** it11 (2.327 kg, SF 2.0) is still the lightest design that passes.
- **Next**: the cornering peak sits on the spoked-ring flange top at r=63 between the right-arm root and the spokes. Thicken the ring locally (a boss or pad on the flange top, from about 20 to 60 deg) or increase floor_r/junction_r at the ring/arm junction. Keep the it26 gusset, which fixed the left side. If the ring pad gets it30 to SF 2, the mass should come out around 2.32 kg, roughly the same as it11. That means the frame layout gains nothing over it11, so the better path for weight is to lighten it11 further.

## Chunk 11 (final variants)
- Stopped: no topology runs were still going; killed the two hidden `wsl.exe -e sleep 7200` keep-alives and two stray wsl shells.
- New build options: `blend_mode='fillet'` (true r10 concave tongue-root fillet prisms in place of the 45-degree prisms) and `arm_pockets` (False = solid arms).
- final/best (it11 + true fillets + floor r4): 2.328 kg, worst SF 2.00 (cornering 251 MPa robust, braking 2.03), Goodman 5.57. PASS, 24/24.
- final/easy (solid arms, solid tongue, edge r6, true fillets): 2.462 kg, worst SF 2.23, Goodman 6.77. PASS, 24/24.
- final/middle: not finished. web 16 → 1.96; floor r3 → 1.99; + rib 28×34 → 1.94 (2.390 kg, peak moves to (-65.7,59.5,71) on the left arm under the eye); rib 30×38 (2.431 kg) was OOM-killed and rerun.
- The cornering spot (45.7,2.1,88.5) scatters ±5 % with the mesh (bisect: old prisms 1.91, floor r3 1.90). Next for middle: make the arms solid (as in easy) but keep the tongue pocket, or take easy and pocket only the tongue.
- wall_check.py: the 0.1 % percentile is 4.48 mm on all three; <0.05 % of samples fall below 4 mm, and those are feather edges at the eye spot-face run-outs (deburr).
- midB (rib 30x38, 2.431 kg) reran: worst SF 1.69. The braking peak is back at the tongue lower edge (-15,-70,76), so a bigger rib pulls load into the tongue root. Middle is still open.

## Chunk 12 (middle variant)
- Build options: hbar(pockets=...), `rib_pockets` and `lug_pockets` (no change for the it11 ribs and lugs, which were already unpocketed).
- From easy + tongue +Z pocket 14 + floor r4 + arm pockets: web 22 → 2.370 kg (not run), web 26 (M2) → 2.383 kg SF 1.97 (cornering at (-11,65.8,84.4)), **web 30 (M5) → 2.397 kg, SF bump 8.40 / cornering 2.33 / braking 2.73 / combined 2.75, Goodman 6.96, 24/24 → final/middle.**

## Chunk 13: other methods for a lighter passing knuckle
Saved: best, middle and easy (STEP, STL, renders) and MACHINING.md committed on **main** in WSL handbuilt-models. **No git remote is configured, so nothing was pushed.**
Backup: C:\projects\_archive\knuckle_billet_final_2026-10-09.zip (31 entries, 2.94 MB).

Methods considered (never loosening the loads or SF targets):
- **a. Parameter optimisation driving the real Gmsh + CalculiX** (picked this chunk). Start with one-at-a-time sensitivities from best
  (wall 5, smaller top/right arms, hybrid-plate pockets, smaller outer rib), then combine the ones that pass. Next: a Nelder-Mead /
  Bayesian (scikit-optimize gp_minimize) loop over about 8 parameters, using the 7 mm mesh for screening and confirming at 5 mm.
  Robust stress scatters about ±5 % with the mesh, so screen with a margin (accept SF >= 2.1 at screening).
- **b. BESO on the CalculiX mesh**: remove elements under about 15 % of the allowable stress, 2 % per step, across all 5 cases. True FE stress, but the result
  needs re-interpreting as pockets, the same way the SIMP results did. That's the medium-term option.
- **c. Topology with a milling (±Z extrusion) constraint**: add a column-wise density projection to topo_stress.py (one variable per (x, y)
  column per side, depth-from-face parameterisation). It maps straight to 2.5D pockets. Voxel stress calibration is still the weak link.
- **d. Two-piece layout**: a bolt-on strut tongue, a 30 × 44 × 126 mm block with 2-4 M10 12.9 bolts into the flange top. Main body Z height drops from
  153 to about 110 mm, so the stock goes from 6.5" plate to 4.5" plate (about 34 kg → 24 kg). The tongue can be a 7075 bar with L along the bending axis. Costs: bolted joint
  mass (+60-90 g of bosses and bolts), joint slip and fatigue (needs preload and a dowel or shear key), and one more interface to tolerance. That's a real option
  if stock and machine envelope matter more than the last 100 g.
- **e. Local pads plus lightening**: an r8-r10 pad at the two known hot spots (rib/keep-out corner (45.7,2.1,88.5), tongue lower edge
  (-15,-69,76)) to buy margin, then spend it on deeper pockets elsewhere (arms with SF > 3 in all but cornering).
Results this chunk (real Gmsh + CalculiX, 5 mm mesh, one change at a time from final best, 2.328 kg):
- P1 wall 5 (all pockets wider): 2.225 kg, SF **0.86** (left arm under the eye at (-66,60,71) gives way). P2 top arm 30×40 + right arm 32×40: 2.301 kg, SF 0.26
  (braking robust 1937 MPa at (-58,16,95): something degenerates locally; investigate). P3 four hybrid-plate pockets: the STEP won't mesh (HXT overlapping facets, also in WSL gmsh 4.15).
  P4 outer rib 22×26: 2.310 kg, SF 1.90. P5 top-arm wall 5: 2.319 kg, SF 0.85 (braking peak at the right eye). P6 right-arm wall 5: no geometric change (that arm is too short to pocket).
  **Conclusion: best sits on a sharp optimum. Every one-parameter step that saves mass fails. The robust stress also scatters about ±5 % with the mesh, so a
  derivative-free optimiser (method a) needs a 2.1 screening margin and will find at most about 20-40 g.**
- **full-arm** (Daniel): fa2 = easy + tongue pockets 14/12 + floor r4 → 2.426 kg, SF 2.43, fatigue 7.07 → final/full-arm. fa3 (junction r8) → 2.26.
  fa4 (deeper tongue pockets, narrower tongue patch, plate from y 0) → 2.402 kg, SF 2.27, but it leaves a 2 mm overhanging flap, so it's rejected (fix: trim the fillet prism).
- WSL detached FEA: run_wsl.sh works, but gmsh 4.15.2 there failed HXT on P3. The box gmsh with ALG2D=1 also failed on P3, so it's a geometry problem, not a WSL problem.
**Recommendation for next:** (e) local pads + (b) BESO. Specifically: 1) put r8-r10 pads at the two hot spots on best
  (rib/keep-out corner (45.7,2.1,88.5) and tongue lower edge) to buy ~10-15 % margin; 2) run BESO in CalculiX on that padded mesh to find which
  pocket regions can deepen; 3) turn those into 2.5D pockets in build123d. (d) two-piece (bolt-on tongue) is the way to cut stock (6.5" → 4.5" plate),
  not mass. Method (a) is only worth running as a final polish with the 2.1 screening margin.

## Chunk 14: pads + BESO map, then the two-piece design (Daniel's new priority)
- (e) Pads on best. A `pads` option adds frustum pads, trimmed by the interface cuts.
  - pad1 (rib/keep-out cone r14→5 + tongue-edge cones r9→3): SF 1.82. pad2 (r18→6 + r12→3 cones): SF 0.96.
  - The horizontal cones at the tongue lower edges stick below the tongue (z ~60-65) and make a **new braking notch** at (-15,-72,65). Rejected.
  - The rib/keep-out cone alone (padA) does lower cornering about 5 % (238 vs 251 MPa in pad2).
- (b) BESO step-0 map (beso_map.py): element envelope over the 5 cases, below 15 % of 251 MPa, interfaces kept.
  - 0.42 kg of low-stress material outside the interfaces: ribs about 0.12 kg (inner rib over the hub), flange/plate 0.09, left-arm root 0.06, tongue root 0.04, ears 0.04, right arm 0.03.
  - **Mistake caught:** the first map treated the strut clamp zone as y < -90. The real lower strut bolt is at y -79 (d14), so the clamp lands run to about y -60.
    bs1-bs4 (tongue-root pockets at y -90…-52) cut into the clamp land, so they were deleted unrun or stopped.
  - bs6 (padA + 2.5D +Z tongue-root pocket y -60…-45, depth 22, outside the clamp zone): 2.316 kg, **SF 1.96** (braking at the tongue lower edge 257 MPa). A near miss; not passed.
  - The WSL padA run used the stale WSL post_iter.py (no robust/singular exclusion), so its numbers aren't comparable. Re-run padA on the box before using it.
- **Two-piece** → final/two-piece/ (see TWO_PIECE.md): full-arm main body + bolt-on tongue on a Z-bolted foot (flange top z 82), 4× M12 12.9 on an r58 arc.
  - Mass: main 1.981 + tongue 0.412 = 2.393 kg Al. **Not passing yet.** tp1 (M10, old positions) SF 2.01, but its holes break through the r71 flange edge. tp3 (M12 on an r58 arc) SF 0.80: the holes notch the tongue-root fillets, plus a suspect braking result at the left-arm root (re-mesh). See TWO_PIECE.md.
  - Joint hand calc from the real strut-bolt reactions (iter/fa2r): no gapping, slip SF ≥ 3.4 with a µ0.5 friction shim.
  - Tongue: 2" plate, 2 setups + a vise turn for the X strut holes. The main body is still 6.5" plate, set by the fixed hub-to-top-eye height.
- Next: (1) FE contact model of the joint (pretension + friction, CalculiX *PRE-TENSION SECTION / *CONTACT PAIR).
  (2) Horizontal split or a bolt-on top-eye arm to get each piece ≤ 4" plate.
  (3) Fix bs6's braking edge with a straight 45° chamfer pad *inside* the tongue envelope (not a cone), then re-screen.
