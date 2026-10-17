---
name: toolkit-patch-handoff
description: >-
  Use when improving the handbuilt-cad (or similar) shared toolkit: edit only
  in a scratch clone in WSL on the CAD workstation, never commit from the worker,
  run tests there, and hand the reviewer a clean patch plus report.
---
Use this whenever an agent improves tools, wiki, or scripts in the handbuilt-cad toolkit (or the same pattern for another shared repo). All work runs in WSL on the CAD workstation, never on an agent's own computer; if it is offline, stop and tell the owner.

## Steps
1. **Scratch clone only.** Work in a disposable clone in WSL on the CAD workstation, outside the live repo (e.g. `~/projects/scratch-<bot>/`). Never edit the live checkout (`$CAD_HOME`) that the user or other agents rely on.
2. **Confirm clean start.** `git status` clean; note the base commit SHA. Confirm the live repo is still clean and on the expected SHA before you finish.
3. **Small scope.** Touch only the files the task names (tool + wiki How-To-Use when docs are needed).
4. **Patch, don't commit.** Produce a patch that applies cleanly to the base SHA (and preferably alone to main). No commits and no pushes from the worker.
5. **Test.** Run the project's full smoke/tests (e.g. `run_all.sh`) in WSL plus any task-specific cases. Capture a short log.
6. **Secrets/path scan.** Grep the diff for home paths, tokens, and passwords before handoff.
7. **Handoff pack.** Put it in the scratch folder: `REPORT.md` (what/why/results/limitations), patch + diffstat, test log, and any sheets. Give the reviewer its path, the base SHA, and confirm the live repo is untouched.
8. **Reviewer opens the PR.** The reviewer re-reads the report, applies it on a clean branch, commits (hooks on, never `--no-verify`), and opens a PR with only that toolkit change. Never push to main, never force-push.
9. **Cleanup.** Leave the scratch clone in place. It is removed only after the PR is merged and the owner says yes, because deleting is destructive.

## Notes
- Personal part models stay off the public repo.
- If a pause or StopSubagent cuts a push mid-flight, re-check what was lost before retrying.
