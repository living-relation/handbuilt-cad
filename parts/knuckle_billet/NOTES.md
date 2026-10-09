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
