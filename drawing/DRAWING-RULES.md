# Drawing rules (drawing engine)

Rules for every drawing this engine makes. The engine enforces the ones marked **(engine)**.

## Revisions
1. **The model drives the letter and the drawing matches.** The model generates the drawing; model and drawing letters are always the same. **(engine)** the title-block letter must equal the newest rev log entry, or the run fails.
2. **Letters:** A to Z, skipping I, L, O and Q. After Z comes AA, AB ... AZ, BA ... (same skips). **(engine)** `drawing/revs.py` (`next_letter`, `bump_model`, `letter_from_release_count`).
3. **Rev A is for brand-new models only.** An existing model's letter comes from counting its past releases in the repo history: merged PRs that changed that model (moves and render-only PRs do not count). With no repo history, count the saved versions where the model changed. Never convert an old rev number.
4. **Model change** (fit, form or function): bump the letter, reset the decimal (C.02 -> D).
5. **Clerical rev** (drawing-only change to an already-released drawing that doesn't affect fit, form or function): add a decimal, C -> C.01 -> C.02. **(engine)** `bump_clerical`.
6. **Workflow:** redline the drawing first, then fix the model, then regenerate the drawing. Never hand-edit a drawing to differ from the model.
7. **File names:** whether file names carry rev letters is each project's own rule; by default revs live only in title blocks, rev logs and registers.

## Rev log
8. Every drawing has a rev log: a small table in the **top-right corner of sheet 1** with columns **Rev | Description | By | Date** (Date dd/mm/yy; By = agent or person). **(engine)**
9. **One entry per PR or release**, never per edit, so a run of edits in one session doesn't jump A -> Z. **(engine)** `revs.add_release` updates the row if the letter is already logged.
10. **Clerical revs are not listed. Rev A's description is always "Initial".** **(engine)**
11. The table shows the newest 6 rows; when it overflows, the oldest rows drop off the top. **(engine)** (`REVLOG_MAX_ROWS`, spec `revlog_max_rows`).
12. Source of truth is a changelog-style rev log **beside the model's STEP file**, one table row per release: `<step name>.REVLOG.md` (or `<part no>.REVLOG.md`) in folders that hold several models, or plain `REVLOG.md` when the folder holds just one. The engine finds it automatically (or spec `revlog: path`); `revs.add_release()` appends a release. Legacy spec `revs` tuples still work as a fallback.
13. The table must not collide with views or the title block. **(engine)** views keep left of it, the trimetric sits below it, leaders avoid it, and an overlap prints a WARNING.

## Lines and views
14. **Never show hidden lines.** **(engine)** hidden edges are never drawn; spec `hidden` is ignored.
15. Center marks and center lines for holes and radii are OK. **(engine)** marks every visible hole (full circle) and arc of 150 deg or more whose axis is along the view, from exact B-rep circles, in any part orientation (spec `center_marks: False` to turn off, `arc_mark_min_sweep` to tune).
16. **Never show mesh triangles or polygons.** Views come from exact B-rep hidden-line removal (OCCT HLR), never from a tessellated mesh. **(engine)** seam and facet edges (two planes meeting within 8 deg) are always dropped unless they are a silhouette; tangent edges (a blend meeting its neighbours) are dropped from orthographic views.
16a. **Tangent edges show in every trimetric (pictorial) view**, so the corners and shapes can be seen. **(engine)** `project` keeps them in any view that does not look straight down a model axis (`is_pictorial`) and draws them as thinner solid lines (`tan` style); `View(..., tangent=False)` turns them off for one view.
17. Renders are smooth-shaded like machined bodies, no mesh lines or triangles (`render/smooth_render.py`).
18. Name the tool that made the model in parentheses (e.g. "(Fusion)", "(build123d)").

## Edges and walls
19. **Edge breaks are optional.** If the CAD can't model them cleanly, leave them off and add a drawing note, e.g. "BREAK SHARP EDGES 0.2-0.4".
20. Fillets go last; any that fail are skipped and listed.
21. Minimum wall thickness applies to critical or structural features only; anything questionable or unclear is flagged for change or approval.

## Files
22. STEP is the deliverable (no STL unless a print job needs it).

## Sections
23. **Section views are capped.** A section is cut with closed-surface clipping: the kept part is a closed solid whose cut faces are filled (and hatched on drawings). Never show open cut faces (a clipped outer skin reads as a hollow shell). **(engine)** `section_view` refuses a cut that is not a closed solid or that has no cut face on the plane; renders use `tools/render/section.py` / `smooth_render.py --section`, which refuse open meshes.

## Assemblies: balloons, exploded views, labels
24. **A balloon only where its part is clearly visible**, and its leader ends on that part: on a drawn line of the part, not shared with another part, and not hidden behind another solid. **(engine)** `asm.visible_candidates`: edge points every 0.4 mm that sit on a visible line, are not within 0.6 mm of another part's edges, and pass a ray test toward the viewer (`Occluder`); a part needs at least 4 such points over 1.2 mm of page or it is not ballooned in that view and is logged as hidden.
25. **Hidden parts are ballooned in an exploded or alternate view**, never with a leader into a solid. Exploded views (sheet 1 `exploded`, or the `stage_sheets` steps) pull the parts out along their assembly direction and join each to its place with a **dotted** line (`expl` style). **(engine)** every BOM item that has a model must be ballooned in at least one view, else `<pdf>.checks.json` lists it under `not_ballooned` and `ok` is false.
26. **Fully or mostly assembled views balloon only the primary parts** (e.g. the enclosure and its lid). **(engine)** items marked `primary: True` are the only ones ballooned in the assembled trimetric; spec `iso_balloons: {assembled|open|exploded: [items]}` sets a view's list by hand.
27. **Balloons never overlap or crowd.** **(engine)** balloon circles keep 2 mm clear (a second, third ... ring takes the overflow); leader tips are spread at least 4 mm apart where the part allows (`choose_anchors`); any balloon overlap or tips closer than 2.4 mm is counted per view in `<pdf>.checks.json` and makes `ok` false.
28. **A note label beside a balloon** names what that part serves (e.g. a fuse's circuit). **(engine)** spec `label_views`: one sheet per entry with a single view (cover parts hidden) and columns of balloons left and right, each with its note, sorted top to bottom so leaders do not cross; `labels: [{item, index | at, text}]` picks one instance of an item. A labelled instance that is not visible is logged and makes `ok` false.
29. **Wire labels at connection points.** **(engine)** `label_views[].wires: [{at: (x, y, z), text}]` draws a boxed label with a leader to each connection point, in the same columns; the text is the project's own wire-end label (the engine never makes one up).
30. **Every drawing writes a check report**, `<pdf minus .pdf>.checks.json`: the PDF's sha256 (16 hex), the engine rule date, the printed notes and tolerance block, per-view balloon counts (placed / overlaps / crowded / crossings / hidden) and `ok`, so a project's gate can check the drawing without the CAD stack. Spec `tol` replaces the default tolerance block (e.g. without the edge-break line).
