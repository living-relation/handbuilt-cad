# State

The one state file for this repo: current goal and open items. Decisions go in `DECISIONS.md`, rules in `AGENTS.md`.

**Goal now:** keep the toolkit current, and ship it as the `handbuilt-cad` plugin (phase 1). (`handbuilt-models` is retired.)

**CNC rules (2026-11-14):** machined parts follow `docs/CNC-MACHINING-RULES.md` (Xometry guide, PDF 16 Apr 2025, plus project rules). CNC walls under 0.030"/0.060" fail; printed parts keep the structural-only, never-assumed wall rule. `tools/cnc_check.py` flags inside corners under 1.3× the nearest standard tool radius and exact standard sizes, and applies the CNC wall floors. Edge breaks are never auto-applied. The in-repo source is `docs/references/xometry-design-guide-cnc-machining-2025-04-16.md`; the PDF is in the models folder `references/`. Under-1.5×D engagement is a model-check flag only; over 2×D is never flagged. Drawings call out actual thread and hole depths, with `THRU` (no depth) for through holes.

**Plugin (2026-11-17):** Phase 1 adds `.claude-plugin/plugin.json` and `.cursor-plugin/` (`plugin.json` plus a one-entry marketplace, `"source": "."`). No `version` field. Skills stay in `skills/`. `plugin-validate` CI runs `claude plugin validate .` (no `--strict`, because a missing `version` is only a warning) and checks the Cursor JSON. Cursor's live import of `"source": "."` is not verified.

**Stand-alone catalog (2026-11-19):** This repo does not name or depend on any other project repo. The Claude catalog is `.claude-plugin/marketplace.json` here, named `handbuilt-cad-plugins`, listing only handbuilt-cad at source `./`. On each claude.ai account, paste `living-relation/handbuilt-cad` under Customize, Plugins, Turn Sync automatically on, and turn on handbuilt-cad. Updates arrive automatically after merges to main. Check for updates in the catalog forces it sooner. That covers chat, Cowork, and Claude Code signed in to that account.

**Agent guide (2026-11-17):** Root `CLAUDE.md` contained only `@AGENTS.md`. That line duplicated this guide, so no extra rules were copied and the file was deleted. `no-claude-md` CI fails if a tracked file is named `CLAUDE.md` or `CLAUDE.local.md`, or is `.claude/CLAUDE.md`.

**Skill delivery (2026-11-19):** Skills reach Claude Chat, Cowork and Claude Code when the handbuilt-cad plugin is on for the claude.ai account; no zip upload. Setup does not copy skills onto the machine. The upload popup is gone.

**Install routes (2026-11-19):** [INSTALL.md](INSTALL.md) has the four ways: `install.cmd` plus `install-plugins.cmd`, single-line commands in the README, [SETUP-PROMPT.txt](SETUP-PROMPT.txt), and the claude.ai clicks. claude.ai is the only Claude route. `install-plugins.ps1`, `install-plugins.cmd`, and `install-plugins.sh` copy `.cursor-plugin` and `skills` to `~/.cursor/plugins/local/handbuilt-cad` and replace that copy each time you run them. They print the clicks when you run them. They do not open a browser. After that copy, fully quit and reopen Cursor. Setup does not copy skills into `~/.claude/skills` or `~/.cursor/skills`.

## Open
- Confirm a live add of handbuilt-cad on a claude.ai account (catalog `living-relation/handbuilt-cad`, Turn Sync automatically on) and fully quitting and reopening Cursor after the local copy. Linux `install-plugins.sh` was run against a temporary home: it copies `.cursor-plugin` and `skills`, replaces the old copy, and prints the missing-plugin line. `install-plugins.ps1` was not executed (no Windows PowerShell on this machine). Windows double-click, a live claude.ai sign-in, and fully quitting and reopening Cursor were not run, so where the Sync automatically switch sits is unverified.

**Kept branches:** none
**Last cleanup:** 2026-10-29 @ 94a7706
