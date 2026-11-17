# State

The one state file for this repo: current goal and open items. Decisions go in `DECISIONS.md`, rules in `AGENTS.md`.

**Goal now:** keep the toolkit current, and ship it as the `handbuilt-cad` plugin (phase 1). (`handbuilt-models` is retired.)

**CNC rules (2026-11-14):** machined parts follow `docs/CNC-MACHINING-RULES.md` (Xometry guide, PDF 16 Apr 2025, plus project rules). CNC walls under 0.030"/0.060" fail; printed parts keep the structural-only, never-assumed wall rule. `tools/cnc_check.py` flags inside corners under 1.3× the nearest standard tool radius and exact standard sizes, and applies the CNC wall floors. Edge breaks are never auto-applied. The in-repo source is `docs/references/xometry-design-guide-cnc-machining-2025-04-16.md`; the PDF is in the models folder `references/`. Under-1.5×D engagement is a model-check flag only; over 2×D is never flagged. Drawings call out actual thread and hole depths, with `THRU` (no depth) for through holes.

**Plugin (2026-11-17):** Phase 1 adds `.claude-plugin/plugin.json` and `.cursor-plugin/` (`plugin.json` plus a one-entry marketplace, `"source": "."`). No `version` field. Skills stay in `skills/`. `plugin-validate` CI runs `claude plugin validate .` (no `--strict`, because a missing `version` is only a warning) and checks the Cursor JSON. Cursor's live import of `"source": "."` is not verified.

## Open
- Dan merges the phase 1 plugin PR. Later phases stay unstarted.

**Kept branches:** none
**Last cleanup:** 2026-10-29 @ 94a7706
