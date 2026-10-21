# For AI agents

[← Home](../../README.md)

> **For the agent.** You (the person) don't need to run anything on this page. Your AI agent reads it and runs the commands. Your part is the 3 steps on the [home page](../../README.md#start-here-you-dont-run-any-of-this-yourself).

This repo is public so AI tools can read it. Start with [How to use](How-To-Use.md) (it has a short section for AI assistants). If you are an AI agent working on it:

1. **Read first:** this wiki, then the part's own `NOTES.md` / `PLAN.md` / `MEASURED.md`, then the top of the part script.
2. **Where to run:** in WSL Ubuntu at `~/projects/handbuilt-cad`, with `.venv/bin/python` for models and `source sim/wsl-env.sh` for simulation. Don't run solvers on `/mnt/c` paths (slow); use `~/sim-runs/`.
3. **Change a part:** edit the named dimensions, rerun the script, re-check fit and run the CNC check (FEA for structural parts only after the owner approves the geometry), update the [Parts index](Parts.md) and add a dated line to `NOTES.md`.
4. **Don't:** move existing folders, scale scans, commit scans/solver output/secrets, force-push, or edit Fairsolid here without reading [`docs/FAIRSOLID.md`](../FAIRSOLID.md) first (Fairsolid is `pipelines/fairsolid/` in this repo; the old fairsolid GitHub repo was deleted on 2026-10-21).
5. **Public repo:** never write API keys, tokens, emails or personal paths into files here.
6. **Ask the owner** before machining-critical changes to the final knuckle versions (scripts in `knuckle_billet/`, part files in `$MODELS_DIR/knuckle_billet_<MMDD>/`).
