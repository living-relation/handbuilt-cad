# State

The one state file for this repo: current goal and open items. Decisions go in `DECISIONS.md`, rules in `AGENTS.md`.

**Goal now:** keep the toolkit current and retire the old `handbuilt-models` repo once nothing in it is still needed.

**CNC rules (2026-11-04):** machined parts follow `docs/CNC-MACHINING-RULES.md` (Xometry guide, PDF 16 Apr 2025). 3D printed parts keep the structural-only, never-assumed wall rule. `tools/cnc_check.py` behavior is unchanged (inside-corner 1.3× is documented only).

## Open
- (2026-10-17) **Local-only knuckle work in the old `handbuilt-models` WSL clone** (never pushed, kept local on purpose): six skip-worktree files (knuckle chunks 15-18), the local branch `backup/local-main-2026-10-10`, and git-ignored `knuckle_billet/` sources (`baseline_al`, `fab`, `loads17`, `final/middle-*`). Where it goes is the maintainer's call. Don't archive or delete `handbuilt-models` until that's settled.
- (2026-10-17) **Models not yet in `$MODELS_DIR`:** `knuckle_billet/fab` A/B/C STEP (+STL), `bezel/bezel_hb.ply`. The bracket example outputs can be regenerated.
- (2026-10-17) **Do non-ST185 parts get drawings?** Open with the maintainer.
- (2026-10-30) **Fusion add-ins HB Export and HB BOM** (`tools/fusion_addins/`): merged and installed on both PCs. HB BOM now has columns Item, QTY, Part Number, Part Description (+ optional Component, Material, Vendor, Vendor PN, Notes), styles Top level / Indented / Parts only, and optional top-level thumbnails in the dialog. Maintainer to try the dialogs by hand. Fusion drawing-system idea: plan later.

**Kept branches:** none
**Last cleanup:** 2026-10-29 (squash-merge of remaining open PRs #49 then #52)
