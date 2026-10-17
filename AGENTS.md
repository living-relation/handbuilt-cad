# Agent guide (Claude, Cursor, Grok Bot and any other agent)

This file is the single agent guide for this repo. `CLAUDE.md` and `.cursor/rules/cad.mdc` only point here.

## Before you change anything
1. Read this file, `CONTRIBUTING.md`, and the hooks/CI that apply (`.githooks/`, `.pre-commit-config.yaml`, `.github/workflows/` if present). Follow them. If a planned step would bypass a hook or gate, stop and ask the maintainer.
2. Never use `--no-verify`, never force-push, never push to `main`. Work on a branch and open a PR.
3. Never commit or push generated or bot-owned files by hand; let the workflow that owns them regenerate them.
4. Run git in the WSL/Linux working copy. A Windows clone is pull-only (`git pull --ff-only`, one repo at a time; no batch pull/push scripts).
5. Use the repo's own venv (`.venv`, built by `setup.sh` from `uv.lock`). Don't install into system Python or into another project's venv. No code here imports from FreeCAD's bundled Python.

## Files that never go in this repo
- Part/model files (STEP, STL, 3MF, F3D, FCStd, PLY, OBJ, IGES, BREP, GLB), solver outputs, archives, files over 1 MB. Finished models go to `$MODELS_DIR/<job>_<MMDD>/<rev>/` (see `skills/publish-to-models`).
- Secrets, `.env` files, tokens, personal paths or personal data.

## CAD and drawing rules
1. **Model drives the rev letter.** The model generates the drawing; model and drawing rev letters always match. Letters start at A, skip I, L, O and Q, then continue AA, AB, ... after Z. Rev A is only for new models; an existing model's letter comes from counting its past releases.
2. **Clerical vs model revs.** Drawing-only edits that don't affect fit, form or function add a decimal (C -> C.01, C.02 ...). A model change bumps the letter for model and drawing (C.0x -> D) and resets the decimal.
3. **Redline workflow.** Mark up the drawing first, update the model to match, then regenerate the drawing from the model. Never fix a design issue on the drawing alone.
4. **Rev log table** at the top-right of sheet 1: Rev, Description, By, Date (dd/mm/yy). One entry per PR/release, not per edit; clerical revs are not listed; Rev A is "Initial"; drop the oldest rows when it gets too long. Template: `drawing/templates/REVLOG.md`.
5. **No hidden lines.** Center marks and center lines are fine.
6. **Smooth bodies, no mesh** in renders or drawings.
7. **Minimum wall thickness applies to critical or structural features only.** Anything questionable (e.g. a thin non-structural wall) is flagged for the maintainer to change or approve, never auto-fixed or auto-failed.
8. **Edge breaks are optional.** If the CAD can't do them cleanly, use a drawing note instead.
9. **Dimension each feature once.** Use an (xN) count for repeats, e.g. "Ø6.6 (x4)".
10. **Correct view.** Put each dimension in the ASME/ISO-correct view; chain, baseline and ordinate styles are all fine.
11. **Fillets go last.** Any fillet that fails is listed in the build report and drawing notes, never dropped silently.
12. **Made with.** Each model folder gets a `MADE-WITH.md` naming the tool that made it; the revision register has a "Made with" column (`drawing/templates/DRAWING-REVS.md`).
13. **STEP only.** No STL unless a specific job needs it.
14. Project-specific naming rules (e.g. whether file names carry rev letters) live in that project, not here.

## Checks before a PR
- `.venv/bin/python -m pytest -q` (repo tests) and the checks for the files you touched.
- The pre-commit hook (guard + pinned gitleaks) must pass.
