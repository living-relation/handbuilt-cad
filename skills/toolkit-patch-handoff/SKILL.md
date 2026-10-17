---
name: toolkit-patch-handoff
description: >-
  Use when improving a shared CAD toolkit repo: edit only in a scratch clone on
  the user's machine, never commit from the worker, run tests there, and hand
  the reviewer a clean patch plus report; the reviewer pushes a branch and opens
  a PR, never commits to main.
---
Use this whenever an agent improves tools, docs or scripts in a shared CAD toolkit repo (or the same pattern for another shared repo). All work runs on the user's machine (e.g. in WSL), never on the agent's own computer; if that machine is offline, stop and tell the user. Follow safe-repo-preflight and the repo's own rules (AGENTS.md, hooks, CI) throughout; they win over this skill.

## Steps
1. **Scratch clone only.** Work in a disposable clone outside every live checkout (e.g. `<scratch_dir>/<agent>/<task>/`, where `scratch_dir` is a folder the user set aside for scratch work, outside the repo). Never edit the user's or another agent's working copy of the repo.
2. **Confirm clean start.** `git status` clean; note the base commit SHA (origin/main). Confirm the live checkouts are still clean and on the expected SHA before you finish.
3. **Small scope.** Touch only the files the task names (tool plus its How-To-Use doc when docs are needed).
4. **Patch, don't commit.** Produce a patch that applies cleanly to the base SHA. No commits and no pushes from the worker.
5. **Test.** Run the repo's full tests/smoke checks plus any task-specific cases, using the repo's own environment (`[python] cad_py` in its `local.toml`, or the venv its setup builds). Capture a short log.
6. **Secrets/path scan.** Grep the diff for home and user paths, cloud-drive paths, personal names, emails, tokens and passwords before handoff. Paths belong in `local.toml`, never in tracked files.
7. **Handoff pack.** Put it in the scratch folder: `REPORT.md` (what/why/results/limitations), patch + diffstat, test log, and any sheets. Give the reviewer its path, the base SHA, and confirm the live checkouts are untouched.
8. **Reviewer opens a PR.** The reviewer re-reads the report, applies the patch in its own clean clone on a new branch, commits only that change (hooks run normally, never `--no-verify`), pushes the branch and opens a PR. Never commit to main, never force-push.
9. **After merge.** Whoever merged pulls every local copy (e.g. Windows and WSL) fast-forward only, and stops if a copy is dirty or diverged.
10. **Cleanup.** Leave the scratch clone in place. It is removed only after the PR is merged and the user says yes, because deleting is destructive.

## Notes
- CAD models stay out of the toolkit repo, apart from small samples when needed.
- Frozen dependencies are not part of this workflow: a project that pins its own environment or run outputs keeps them until the user says otherwise. Never change or repoint them from a toolkit patch.
- Outside services (e.g. a CAD app's MCP server, a harness-design MCP) are outside dependencies; reference them, never vendor them into the repo.
- If a pause or stop cuts a push mid-flight, re-check what was lost before retrying.
