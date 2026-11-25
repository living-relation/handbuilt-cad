# STATE (max 30 lines, overwrite only)
Repo: handbuilt-cad
Branch: perf/drawing-render-batch
Last_Verified_SHA: 1aa47cc
Updated: 2026-11-25 -- Claude (claude.ai chat, sr-drawing-pack coordinator)

## Current Goal
- Objective: Faster sheet output in drawing/dwg.py render(): solid lines of one style drawn in one call (big assembly sheet about 25 s to under 1 s); dashed lines unchanged.
- Spec_Ref: none

## Active Blocker
- Status: NONE
- Detail: none

## Next Single Step
- [NEXT] Merge when CI is green; sr-drawing-pack can then drop its own copy of this speed-up.

## Pointers
- Branch_States: none
- Backlog: BACKLOG.md
- Latest_ADR: 2026-11-23 live state in the repo (DECISIONS.md)
