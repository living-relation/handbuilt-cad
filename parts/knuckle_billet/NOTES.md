# knuckle_billet: working notes

## 2026-10-09 chunk 1 (loads, baseline FEA, plan)

- **Where this ran:** Daniel's PC (WORKSTATION) was offline the whole session, so chunk 1 ran on the agent box in `/workspace/knuckle_billet/`. Copy it to `~/projects/handbuilt-models/knuckle_billet/` in WSL and commit there once the PC is back.
- **Solver:** CalculiX 2.23 (Debian package unpacked into `/opt/ccx`, with a `/usr/local/bin/ccx` wrapper). The PC has 2.21. Gmsh comes from the pip module 4.15 in `/workspace/kbvenv`, ParaView is pvpython 5.13 (Debian).
- **Geometry:** `knuckle/v4b/knuckle.step` (OCC volume 934,760 mm3).
  - Gmsh could not mesh the STEP directly: "1D mesh not closed loop", then "impossible to mesh periodic surface" (lofted cast surfaces). Healing the STEP destroyed the solid.
  - Fallback mesh: v4b STL, MeshFix, isotropic remesh (3.2 mm, adaptive to features), MeshFix again, Gmsh HXT tets, Netgen optimise, 2nd order (C3D10). That gave 219k nodes and 136k tets. 3 zero-volume slivers were dropped (6e-5 mm3 total).
  - The repaired surface encloses about 1.016e6 mm3, about 8 % more than the STEP. MeshFix closed flange holes 1 and 3 and filled some cast recesses, so the baseline is slightly stiffer and stronger than the real v4b. **Mass is reported from the exact STEP volume**, not from the mesh.
  - The hub bore, all 3 eye bores, both strut holes and both ear holes are open in the mesh (checked).
- **Supports and loads:** see `LOADS.md` (all estimates). One linear run serves both alloys: stress is independent of E for these supports, and deflection scales by 68.9/71.7 for 7075.
- **Scripts:** `loads.py` (cases), `mesh_*.py`, `fea_v4b.py` (deck: node sets by geometry from the v4b parameters, rigid bearing ring, caliper torque on the ear holes), `post_v4b.py` (von Mises, SFs, VTU), `render_pv.py`.
