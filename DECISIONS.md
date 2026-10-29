# Decisions

One dated line per decision, newest last. Rules that agents must follow live in `AGENTS.md`; this file records when and why they were decided.

- 2026-10-28: `STATE.md` is the one state file and `DECISIONS.md` the one decisions file. (maintainer, session-start cleanup)
- 2026-10-28: The state-file check runs as `.githooks/commit-msg` in comment mode (warns, never blocks). Switch with `bash scripts/state-check.sh --mode block`, committed in a PR. (maintainer)
- 2026-10-28: `automation.yml` registers every hook and setup job; `scripts/registry-check.py` checks it from the commit-msg hook. (maintainer)
- 2026-10-28: The pre-public checklist was done when the repo went public; `docs/PRE-PUBLIC-CHECKLIST.md` was removed. (maintainer)
- 2026-10-28: The PR #42 follow-up (other skill copies replaced by links to `skills/`) is done. (maintainer)
- 2026-10-29: Setup always links CAD skills into `~/.claude/skills` (Cursor reads that folder; do not duplicate into `~/.cursor/skills`). `-LinkSkills` / `--link-skills` stay as no-ops. After a Windows install, a popup reminds the user to upload skill zips in Claude desktop; `-NoPopup`/`-Quiet`/CI skip it.
