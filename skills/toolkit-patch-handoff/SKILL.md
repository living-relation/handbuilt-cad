---
name: toolkit-patch-handoff
description: >-
  Use when improving the handbuilt-models (or similar) public toolkit: edit only
  in a scratch clone on DansPC WSL, never commit from the worker, run tests
  there, and hand Grok Bot a clean patch plus report for review and push.
---
Use this whenever a bot improves tools, wiki, or scripts in the public handbuilt-models toolkit (or the same pattern for another shared repo). All work runs on DansPC in WSL, never on the bot's own computer; if DansPC is offline, stop and tell Daniel.

## Steps
1. **Scratch clone only.** Work in a disposable clone on DansPC WSL outside the live repo (e.g. `/home/daniel/projects/scratch-<bot>/`). Never edit the live checkout at `/home/daniel/projects/handbuilt-models` that the user or other bots rely on.
2. **Confirm clean start.** `git status` clean; note the base commit SHA. Confirm the live repo is still clean and on the expected SHA before you finish.
3. **Small scope.** Touch only the files the task names (tool + wiki How-To-Use when docs are needed).
4. **Patch, don't commit.** Produce a patch that applies cleanly to the base SHA (and preferably alone to main). No commits and no pushes from the worker.
5. **Test.** Run the project's full smoke/tests (e.g. `run_all.sh`) in WSL plus any task-specific cases. Capture a short log.
6. **Secrets/path scan.** Grep the diff for home paths, tokens, and passwords before handoff.
7. **Handoff pack.** Put it in the scratch folder: `REPORT.md` (what/why/results/limitations), patch + diffstat, test log, and any sheets. Give the reviewer its path, the base SHA, and confirm the live repo is untouched.
8. **Reviewer pushes.** The reviewer (usually Grok Bot) re-reads the report, applies on a clean tree, commits, and pushes only that toolkit change, never force-push.
9. **Cleanup.** Leave the scratch clone in place. It is removed only after Grok Bot has pushed and Daniel says yes, because deleting is destructive.

## Notes
- Personal part models stay off the public repo.
- If a pause or StopSubagent cuts a push mid-flight, re-check what was lost before retrying.
