# Drawing rules (SteveCAD drawing engine)

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
16. **Never show mesh triangles or polygons.** Views come from exact B-rep hidden-line removal (OCCT HLR), never from a tessellated mesh. **(engine)** seam, tangent and facet edges (faces meeting within 8 deg) are dropped unless they are a silhouette. A model with many flat facets (polygonised curves) prints a WARNING: rebuild those curves as true arcs.
17. Renders are smooth-shaded like machined bodies, no mesh lines or triangles (`render/smooth_render.py`).
18. Name the tool that made the model in parentheses (e.g. "(Fusion)", "(build123d)").

## Edges and walls
19. **Edge breaks are optional.** If the CAD can't model them cleanly, leave them off and add a drawing note, e.g. "BREAK SHARP EDGES 0.2-0.4".
20. Fillets go last; any that fail are skipped and listed.
21. Minimum wall thickness applies to critical or structural features only; anything questionable or unclear is flagged for change or approval.

## Files
22. STEP is the deliverable (no STL unless a print job needs it).
