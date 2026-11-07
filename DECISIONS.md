# Decisions

One dated line per decision, newest last. Rules that agents must follow live in `AGENTS.md`; this file records when and why they were decided.

- 2026-10-28: `STATE.md` is the one state file and `DECISIONS.md` the one decisions file. (maintainer, session-start cleanup)
- 2026-10-28: The state-file check runs as `.githooks/commit-msg` in comment mode (warns, never blocks). Switch with `bash scripts/state-check.sh --mode block`, committed in a PR. (maintainer)
- 2026-10-28: `automation.yml` registers every hook and setup job; `scripts/registry-check.py` checks it from the commit-msg hook. (maintainer)
- 2026-10-28: The pre-public checklist was done when the repo went public; `docs/PRE-PUBLIC-CHECKLIST.md` was removed. (maintainer)
- 2026-10-28: The PR #42 follow-up (other skill copies replaced by links to `skills/`) is done. (maintainer)
- 2026-10-29: skill-zips CI git push uses HTTP basic `x-access-token` (same as actions/checkout), not Bearer. `persist-credentials` stays false. Bearer was ignored and zip commits failed with "could not read Username".
- 2026-10-29: Setup always links CAD skills into `~/.claude/skills` (Cursor reads that folder; do not duplicate into `~/.cursor/skills`). `-LinkSkills` / `--link-skills` stay as no-ops. After a Windows install, a popup reminds the user to upload skill zips in Claude desktop; `-NoPopup`/`-Quiet`/CI skip it. Claude-app harness skills (`skills/EXCLUDE.txt` / `source: harness-design-app`) stay unlinked and untouched.
- 2026-10-29: Fusion add-ins live in `tools/fusion_addins/` (HB Export, HB BOM). On non-commercial Fusion plans custom BOM properties and IGES/SAT export are not available to scripts, so vendor, vendor part number and notes are stored as component attributes (group `handbuiltcad`) and IGES/SAT are offered but reported as blocked. (maintainer request)
- 2026-11-04: CNC machined parts follow `docs/CNC-MACHINING-RULES.md`, from Xometry "Design Guide: CNC Machining" (38 pp, PDF 16 Apr 2025). For CNC parts the guide's walls are the rule: 0.030" (0.762 mm) metal, 0.060" (1.52 mm) plastic/composite. The structural-only / never-assumed minimum wall is for 3D printed parts only. Inside-corner 1.3× the nearest standard tool radius (never an exact standard tool size) is documented only; `tools/cnc_check.py` is not changed. Project rules in AGENTS.md / DECISIONS.md still win where they are stricter. (maintainer)
- 2026-11-04: Models folder retention replaces add-only / latest-only: keep latest + 2 previous versions per assembly and the parts they use, latest per part, max 2 screenshots/2D renders per model, never delete 3D scans. ST185 jobs live in the models folder, not the st185 repo. (maintainer)
- 2026-11-06: Drawings are made only when asked for, never automatically. (maintainer)
- 2026-11-06: Agents delete their own leftovers (merged local branches, worktree folders, temp files) at the end of every task without asking. (maintainer)
- 2026-11-06: Knuckle and bezel sources are in the models folder and old handbuilt-models is gone; the HB Export/HB BOM hand test is closed. (maintainer)
