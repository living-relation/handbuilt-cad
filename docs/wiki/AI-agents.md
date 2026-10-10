# For AI agents

[← Home](../../README.md)

This repo is public so AI tools can read it. If you are an AI agent working on it:

1. **Read first:** this wiki, then the part's own `NOTES.md` / `PLAN.md` / `MEASURED.md`, then the top of the part script.
2. **Where to run:** in WSL Ubuntu at `~/projects/handbuilt-models`, with `.venv/bin/python` for models and `source sim-tools/wsl-env.sh` for simulation. Don't run solvers on `/mnt/c` paths (slow); use `~/sim-runs/`.
3. **Change a part:** edit the named dimensions, rerun the script, re-check fit (and FEA for structural parts), update the [Parts index](Parts.md) and add a dated line to `NOTES.md`.
4. **Don't:** move existing folders, scale scans, commit scans/solver output/secrets, force-push, or edit Fairsolid from here (it is a separate repo: <https://github.com/living-relation/fairsolid>).
5. **Public repo:** never write API keys, tokens, emails or personal paths into files here.
6. **Ask the owner** before machining-critical changes to the final knuckle versions in `knuckle_billet/final/`.
