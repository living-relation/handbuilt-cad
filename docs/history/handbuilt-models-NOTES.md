# Hand-built parametric parts - running notes

Started 2026-10-09. Tools: build123d 0.13 (scratch venv C:\projects\_scratch\pedal-parametric\.venv on the PC;
the same versions were used on the agent box for the heavy work). Scale is never changed. Only rigid moves are used.
Fairsolid: no code changes so far. The checkout stays on main.

## Step 1 - scan list (C:\Users\danie\agent-tools\scan-list.txt)
- Searched C:\project_3D_scans (the Creality save folder), Creality AppData projects, OneDrive (Desktop, Documents),
  Downloads, C:\projects (not shipping), and other C:\ folders. C: is the only drive. Google Drive was skipped (photos and CAD only).
- 5323 hits went down to 485 after dropping compiled ESP32 `.c.obj` files.
- The automatic "CAD export" label is NOT reliable for Creality `Mesh.ply` / exported scan STLs. Decimated scans have large flat
  facets. Judged by hand, anything with more than about 100k triangles from a Creality project is a scan.

Real scans by part (the final mesh, then the raw passes):
| part | final scan mesh (dupes) | raw Fused passes | type |
|---|---|---|---|
| rear knuckle | CrealityScan\Projects\rear knuckle\...\Mesh.ply, 3.02M tri (= Desktop\3D Models\Rear R Knuckle.stl) | 2 | closed part |
| bezel | project_3D_scans\bezel\...\Mesh.ply, 984k (= Desktop\3D Models\bezel.stl) | 3 | closed part |
| dash housing | project_3D_scans\dash housing\...\Mesh.ply, 131k (= Desktop\3D Models\dash housing.stl, + ColorMapping.ply) | 1 | closed part |
| dash bezel and housing | ...\Mesh.ply, 1.35M | 2 (one 462 MB) | closed part (combined scan) |
| fuel pump | ...\Mesh.ply, 1.87M (= Desktop\3D Models\3D Scans\fuel pump.stl) | 3 | closed part |
| pump hanger | ...\Mesh.ply, 1.93M (= ...\3D Scans\pump hanger.stl) | 2 | closed part |
| pedal adapter | ...\Mesh.ply, 1.35M (= Desktop\3D Models\subaru pedal scan.stl) | 3 | DONE (pedal-parametric) |
| Audi oil catch bracket | CrealityScan 4 ...\Mesh.ply, 669k (= ccs catch can audi.stl = Downloads\catch\catch.obj/.ply/.stl) and Documents\Creality Scan\Audi Catch Can Bracket.obj, 214k | 3 | open space (DONE via Fairsolid refscan) |
| Project_26060601 (and _1, a copy) | small part 23x57x30 mm, Mesh.ply 354k/301k | 1 (duplicate) | unknown small part, check with Daniel |

Copies in Fairsolid runs, the _scratch trials, rollback folders, agent-tools and C:\Temp are working copies of the scans above. They are not new scans.

CAD exports (listed only, not hand-built): dash3left.STL, dash3right.STL, esp32 BEZEL MOUNT (left/right/both), esp32 Mount 2.STL,
Grippin-Body (.stl/.obj/.3mf), modified clamp (main / cad mouse stand), gear_selector_bush_v1, Wheel offset tool (x2), Wheel+Size v4,
16mm pipe clamp, Celica Models\catch can.obj, plus the meshmixer sample library (animal parts, not scans).

## Step 2 - parts
### 1. Rear knuckle - IN PROGRESS
- 07:55 knuckle: measured hub, bore steps, holes, 3 eyes (see knuckle\MEASURED.md). Tried smooth lofts/height sheets for the flange: OCC booleans too slow/invalid, dropped. Now building flange as 6 layer prisms (three-view).
- 08:00 knuckle v2 (6 flange layer prisms + arms + exact hub/eyes/holes): median 0.55, p95 5.1, 48% within 0.5 - but jagged steps at the back web and solid flagged invalid. Next: one sloped back-web region instead of layers there.
- 08:20 knuckle DELIVERED AS v2 (first usable version): knuckle\v2\knuckle.py (+knuckle_profiles.py), STEP/STL. Fit: median 0.55 mm, p95 5.1, 28% within 0.2, 48% within 0.5, 63% within 1.0.
  OCC still flags the solid "invalid" (BRepCheck); it is one solid and exports and renders fine. Re-check it in a CAD program before machining from it.
  Tried after v2: a sloped back-web region and one fuzzy multi-fuse. Both lost pieces in the booleans, so they are NOT used (code is in knuckle\build\).
  NEXT STEPS (knuckle): (1) replace the 6 flange layer prisms with fewer, overlapping regions and fuse them one at a time, checking validity after each;
  (2) the back web between the flange and the upper arms (y 40-100) is the biggest error (up to 13 mm); (3) top eye bore is a teardrop, modelled round 40;
  left eye bore is not round, modelled 35; (4) fix validity (ShapeFix), then rerun check.py. Bezel not started.
- 08:30 v3 started in knuckle\v3: flange = 2 overlapping regions (z37-60, z56-81) + one sloped back web (y40-104, z37-100); pieces joined one at a time with is_valid check (plain -> fuzzy -> ShapeFix -> skip).
- 08:48 v3 run: valid, but back_web join failed (coplanar box faces) -> 4 loose solids; low_arm piece invalid. Retrying with back_web/low_arm boxes nudged off shared planes.
- 08:56 v3 RESULT: valid = yes (BRepCheck passes), but 4 separate solids. The back-web region (the one sloped piece) failed to build or join, so the upper arms and eyes float.
  Fit is WORSE than v2: median 0.73 mm, p95 17.9 (v2: 0.55 / 5.1). v2 stays the best version. Renders: /workspace/handbuilt/knuckle/renders_v3/ (box).
  Flange is now 2 overlapping regions instead of 6 layers (fewer steps, still blocky). No fillets or drafts yet.
  NEXT: (1) debug hull_piece("back_web") after the box nudge (why it comes out empty); join it right after plate_high; this reconnects the arms.
        (2) then fillet the plate/web edges; (3) re-measure. STEP of v3 is built on the PC by a detached job (see below).
- 08:44 v4 started in knuckle\v4 (copy of v3). Step 1: debug back_web.
- 08:57 v4: back_web fixed (prisms overrun the box by 1-2 mm, different per view, so no shared end faces) -> builds valid, 271k mm3. Flange halves kept as v3 (overrun made them fail/slow). Full build running.
- 09:04 v4 RESULT: ONE solid, valid = yes (count checked after every join; pieces that would split the solid are retried after the others).
  Back web builds and joins right after the lower flange half. Join order: plate_low, back_web, left_ear, plate_high, low arm, top arm, webs, eyes.
  Fit: median 0.66, p95 6.4, max 19, 25/44/58% within 0.2/0.5/1.0. Does NOT beat v2 (0.55 / 5.1), mainly because the back web is a blocky
  three-view block. Biggest misses: under the back web (y 12-92, up to 15 mm), under the front flange (y -108..-12, z 39-58, up to 10 mm),
  top-arm root (up to 19 mm). No fillets yet. STEP on the box is 247 MB (heavy spline faces); the PC job writes v4\knuckle.step.
  NEXT: loft the back web along Y from a few smoothed sections instead of the three-view block; split the flange halves front/back;
  fillets after that. Renders: /workspace/handbuilt/knuckle/renders_v4/.
- 08:58 PC job started: v3 STEP/STL -> C:\projects\_scratch\handbuilt\knuckle\v3\knuckle.step (log v3\step_job.log / .err, pid 10664). Expect about 1-2 min.
- 09:03 v3 STEP job finished OK on the PC: v3\knuckle.step (65 MB) + .stl. Same 4-solid geometry as the box build. v2 remains the best knuckle.
- PC job started for v4 STEP/STL -> C:\projects\_scratch\handbuilt\knuckle\v4\knuckle.step (log v4\step_job.log/.err, pid 25240); about 2 min; expect a very large STEP (about 250 MB).
- 09:07 v5 started in knuckle\v5 (from v4): back web as loft, flange halves split front/back, lighter outlines for a smaller STEP.
- 09:07 v5: back web loft = 7 Y-stations (12 mm apart), ruled, simplified outlines -> valid, 193k mm3 (v4 block 271k). Full build running.
- 09:10 v5: whole-web loft would not join the top arm (bad booleans). Now web = loft (z 38-80, sloped part) + three-view block (z 76-100, where the arms start). Building.
- v5 RESULT (FAILED): 1 valid solid, but the top arm, left web, left eye and top eye would not join (the kernel gives invalid or volume-wrong results
  where the loft / three-view pieces meet). It is missing those parts, so it is not usable. STEP on the box is 92 MB even after clean().
  No PC STEP job was started for v5. Front/back flange split and the lower web loft built fine.
  Best versions are still v2 (best fit, flagged invalid) and v4 (one valid solid, median 0.66 / p95 6.4).
  NEXT: stop stacking spline-prism booleans. Rebuild the upper arms + eyes as one connected group first (join them to each other),
  then join that group to the web/flange once; or move to a plain-geometry model (planes, cylinders, simple fillets) for the cast body.
- v5 fit check ran out of memory on the box (27 MB STL); no fit numbers or renders for v5.

## 2026-10-09 16:20 ET - knuckle v4 feature check (new home: C:\projects\active\handbuilt-models\)
- Older history is in C:\projects\_scratch\handbuilt\NOTES.md (left untouched).
- Feature check done: knuckle\feature_check\feature_table.md (+ overlay_top/right/iso/bottom.png, feature_check.py).
  Hub OD, all 6 bore steps, the 4 flange bolt holes, the 2 ear holes, the side boss hole, the 3 eye bores/ODs and the eye end faces all within about 1 mm and 1 deg (most within 0.3 mm).
  Real error: the 2 lower-arm X holes (the shock/link mount) were 2.2 and 3.8 mm off in z. Re-fitted: outer y-147.5 z96.2 d14.3, inner y-79.0 z93.7 d14.0.
  Top eye bore looks 41.3 on the scan vs 40.0 in the model (rough surface, rms 0.67): unconfirmed.
- v4 STEP on the PC (_scratch\handbuilt\knuckle\v4\knuckle.step, 247 MB): opens in 16 s, valid, 1 solid, 407 faces, 934 cm3.
- v4b = v4 with the two corrected shock-mount holes; building on the box (/workspace/handbuilt/knuckle/v4b).
