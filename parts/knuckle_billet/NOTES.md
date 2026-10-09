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
