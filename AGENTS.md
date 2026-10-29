# Agent guide (Claude, Cursor, Grok Bot and any other agent)

## Read first, before starting work or asking
Before starting work or asking the maintainer anything, read in order: (1) this repo's agent guide
(`AGENTS.md` / `CLAUDE.md`), (2) its binding rules / decisions file if it has one (`CONTRIBUTING.md`, `drawing/DRAWING-RULES.md`), (3) the shared
working memory `%USERPROFILE%\.claude\working-memory\<project>\INDEX.md` (WSL:
`/mnt/c/Users/<user>/.claude/working-memory/<project>/INDEX.md`), (4) the newest handoff note if one
exists (none yet; see `handoff/` if present). If a rule or note already answers a question, act on it and cite it - never ask the
maintainer something the rules already answer.

This file is the single agent guide for this repo. `CLAUDE.md` and `.cursor/rules/cad.mdc` only point here.

**State and decisions:** current goal and open items live only in `STATE.md`; dated decisions in `DECISIONS.md`. Scripts and hooks are registered in `automation.yml`. The `commit-msg` hook warns when code changes without one of these being updated (skip one commit with `[no-state]`).

## Before you change anything
1. Read this file, `CONTRIBUTING.md`, and the hooks/CI that apply (`.githooks/`, `.pre-commit-config.yaml`, `.github/workflows/` if present). Follow them. If a planned step would bypass a hook or gate, stop and ask the maintainer.
2. Never use `--no-verify`, never force-push, never push to `main`. Work on a branch and open a PR. Exception: the skill-zips CI bot may force-push (with lease) its own `chore/skill-zips` branch only.
3. Skill zips (`skills/<name>.zip`) are rebuilt automatically by CI; don't edit by hand. Never commit or push other generated or bot-owned files by hand; let the workflow that owns them regenerate them.
4. One clone per machine. On Windows + WSL it is the Windows clone (`<projects>\active\handbuilt-cad`); WSL sees the same files through the link `~/projects/handbuilt-cad`, so there is no WSL clone to keep in sync. Run git from Windows; pull with `git pull --ff-only`, one repo at a time; no batch pull/push scripts. In WSL use the Linux venv (`$CAD_PY`, default `~/.venvs/handbuilt-cad/bin/python`), never the repo's Windows `.venv`.
5. Use the repo's own venv (`.venv`, built by `setup.sh` from `uv.lock`). Don't install into system Python or into another project's venv. No code here imports from FreeCAD's bundled Python.

## Files that never go in this repo
- Part/model files (STEP, STL, 3MF, F3D, FCStd, PLY, OBJ, IGES, BREP, GLB), solver outputs, archives, files over 1 MB. Finished models go to `$MODELS_DIR/<job>_<MMDD>/<rev>/` (see `skills/publish-to-models`).
  Exception: Claude-importable skill zips at `skills/<skill-name>.zip`, rebuilt automatically by `.github/workflows/skill-zips.yml`. Do not add other archives.
- Secrets, `.env` files, tokens, personal paths or personal data.

## CAD and drawing rules
The drawing engine's full rule list (and which ones it enforces) is `drawing/DRAWING-RULES.md`; rev letters come from `drawing/revs.py`.

1. **Model drives the rev letter.** The model generates the drawing; model and drawing rev letters always match. Letters start at A, skip I, L, O and Q, then continue AA, AB, ... after Z. Rev A is only for new models; an existing model's letter comes from counting its past releases.
2. **Clerical vs model revs.** Drawing-only edits that don't affect fit, form or function add a decimal (C -> C.01, C.02 ...). A model change bumps the letter for model and drawing (C.0x -> D) and resets the decimal.
3. **Redline workflow.** Mark up the drawing first, update the model to match, then regenerate the drawing from the model. Never fix a design issue on the drawing alone.
4. **Rev log table** at the top-right of sheet 1: Rev, Description, By, Date (dd/mm/yy). One entry per PR/release, not per edit; clerical revs are not listed; Rev A is "Initial"; drop the oldest rows when it gets too long. Template: `drawing/templates/REVLOG.md`.
5. **No hidden lines.** Center marks and center lines are fine.
6. **Smooth bodies, no mesh** in renders or drawings.
7. **Minimum wall thickness applies to critical or structural features only.** Anything questionable (e.g. a thin non-structural wall) is flagged for the maintainer to change or approve, never auto-fixed or auto-failed. No tool assumes a minimum: `tools/cnc_check.py` needs `--min-wall`, the spec's `min_wall_mm` or `--walls-config`, otherwise it reports walls as "not checked".
8. **Edge breaks are optional.** If the CAD can't do them cleanly, use a drawing note instead.
9. **Dimension each feature once.** Use an (xN) count for repeats, e.g. "Ø6.6 (x4)".
10. **Correct view.** Put each dimension in the ASME/ISO-correct view; chain, baseline and ordinate styles are all fine.
11. **Fillets go last.** Any fillet that fails is listed in the build report and drawing notes, never dropped silently.
12. **Made with.** Each model folder gets a `MADE-WITH.md` naming the tool that made it; the revision register has a "Made with" column (`drawing/templates/DRAWING-REVS.md`).
13. **STEP only.** No STL unless a specific job needs it.
14. Project-specific naming rules (e.g. whether file names carry rev letters) live in that project, not here.
15. **Capped sections only.** Every rendered section view uses closed-surface clipping: the cut part is a closed solid with its cut faces filled (caps). Never clip just the outer skin; open cut faces render as hollow shells and misread wall thickness. Use `tools/render/section.py` (or `smooth_render.py --section`); the drawing engine's section views are capped too. All of them refuse an open cut.
16. **Rev folders are lettered.** `tools/rev.py` makes `rev<LETTER>` (clerical `rev<LETTER>.<NN>`) folders by the rules above; it never converts old numeric `revN` folders.
17. **Initials, never agent names.** DRAWN = the person on Rev A; rev-log BY = the person who requested the change (`drawing/DRAWING-RULES.md` rule 32). They come from `~/.drawing-initials` (or env `DRAWING_INITIALS`); if missing and you are an agent (no terminal) the tool stops - ask the maintainer for the requester's initials, never guess or use "Claude" / "SteveCAD".
18. **Revision triangles.** Every full-letter rev puts its letter in a triangle next to each changed item (and the BOM row of a changed part number); .01 clerical revs have none and are not in the rev log (`drawing/DRAWING-RULES.md` rule 33, `drawing/revmarks.py`). Old triangles stay on later revs by default.

## Folder notes
Every folder the toolkit creates or uses (the parts home `~/cad-parts` root, its `_archive`, each `<job>`, `<job>/src`, `<job>/runs`, the models folder and each models job folder) has a README.md or AGENTS.md saying what is in it, who owns it, and where its paired folder is. An agent that creates a new job or folder adds one from `templates/notes/` (`tools/folder_notes.py` does it, add-only, never overwriting; it is the only writer of these notes, called by `setup.sh` and publish-to-models). Job folders are named `<name>_<MMDD>`; other folders are reported as warnings. `tools/folder_notes.py --check` lists folders missing one. This is the full rule.

## Checks before a PR
- `$CAD_PY -m pytest -q` (repo tests; `CAD_PY` = `.venv/bin/python`, or `~/.venvs/handbuilt-cad/bin/python` in WSL) and the checks for the files you touched.
- The pre-commit hook (guard + pinned gitleaks) must pass.

## Where every tool lives
WSL/Linux paths; `bash scripts/verify-install.sh` checks all of them (setup runs it last). Env vars load in any `bash -lc` from `~/.config/handbuilt-cad/env.sh`.

| Tool | Path / command | Used by (skill) |
|---|---|---|
| CAD venv (build123d, OCP) | `$CAD_PY` (`~/.venvs/handbuilt-cad/bin/python`) | all CAD skills, cnc-part-check, cad-drawing, blend-fillet |
| Sim venv (gmsh, meshio) | `$SIM_VENV/bin/python` (`~/simvenv`) | sim-stack (`tools/quick_fea.py`) |
| CalculiX | `ccx` (`/usr/bin/ccx`, apt) | sim-stack |
| Gmsh | `gmsh` (`/usr/bin/gmsh`, apt) | sim-stack |
| ParaView | `xvfb-run -a pvpython` (apt `paraview`) | sim-stack |
| uv | `uv` (`~/.local/bin/uv`) | setup, venvs |
| Elmer, OpenFOAM | optional, **not installed by setup** (`sim/SIM_TOOLS.md`) | sim-stack full studies |
| Repo / parts / models | `$CAD_HOME`, `$HBCAD_PARTS_HOME`, `$MODELS_DIR` | publish-to-models, all |

## Linux runtime
Open3D needs the system library `libEGL.so.1`. On Ubuntu install it with `sudo apt-get install -y --no-install-recommends libegl1` or `import open3d` fails. `setup.ps1` installs the sim apt packages in `apt-sim.txt` as root through `wsl.exe -u root` (no WSL password); `bash setup.sh` run directly tries `sudo -n`, then a sudo prompt only in a terminal, the sim venv and uv, then runs `scripts/verify-install.sh`, which fails with a list of anything missing. `--no-sim` / `-NoSim` skips the sim tools. Fairsolid stays optional (`--with-fairsolid`).
