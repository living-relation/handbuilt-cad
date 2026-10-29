# Changelog

## 2026-10-29: setup links skills by default; Windows skill-zip upload popup
- Setup always links each CAD skill into `~/.claude/skills` (Windows junctions and WSL/Linux symlinks). Cursor reads that folder too, so skills are not also linked into `~/.cursor/skills`; old links this repo made there are removed (the link only). `-LinkSkills` / `--link-skills` stay as no-ops.
- At the end of a Windows install (`setup.ps1`, including double-click `install.cmd`) a separate popup reminds you to upload new or changed CAD skill zips in the Claude desktop app for each Claude account (Skills settings), lists the zip names (or skill folders if there are no zips), and offers to open that folder in Explorer. `-NoPopup` / `-Quiet` skip it, as do CI env vars.
- Claude-app harness skills (`skills/EXCLUDE.txt` or `source: harness-design-app`) stay unlinked and are never moved, backed up, replaced or removed.

## 2026-10-29: the latest rev replaces the previous one
- Rule (AGENTS.md 19, `skills/publish-to-models` step 7, `skills/cnc-part-check`): The latest revision of a model always replaces the previous one. When a new rev is filed, delete the old rev's models and outputs (models folder and runs); keep only the latest rev. Never keep old revs side by side.
- Docs and skills text only. `tools/rev.py` is unchanged: it still creates the new `rev<LETTER>` folder beside the old ones; the old ones are deleted after the new rev is filed and checked.

## 2026-10-29: skill-zips CI git push auth
- Zip commits use HTTP basic `x-access-token` (same as actions/checkout). Bearer was ignored, so the bot could not push rebuilt `skills/*.zip` files.

## 2026-10-29: electrical plan, off-the-shelf CAD, questions to Dan
- Every design with electronics has a plan document (wiring tables, schematic, electronics BOM). Wiring tables list every required wire; unplanned GPIO/PCB pins are TBA. Electrical designs use real gauges, connectors, routing and device specs. Off-the-shelf parts (dev boards, extrusion brackets, plates and similar hardware) use the supplier's official CAD model, or a labelled best-guess from the datasheet; put the supplier's part number on the BOM and save every part model, purchased and fabricated, in a `parts/` folder inside the project.
- Questions to the maintainer are always multiple choice, labelled a1, a2, with a recommended answer when there is one.
- Docs and skills only (`AGENTS.md` "Electrical and design plans", not CAD rule 19 — that number is reserved for PR 49).

## 2026-10-28: one state file, decisions file and automation registry
- New `STATE.md` (goal, open items, last cleanup) and `DECISIONS.md` (dated decisions). `AGENTS.md` points to both.
- New `automation.yml` lists every hook, workflow and setup job; `scripts/registry-check.py` checks it.
- New `.githooks/commit-msg` runs `scripts/state-check.sh` in comment mode (`.state-check-mode`): it warns when code changes without a state/decisions update. `[no-state]` in the message skips one commit. It uses the first Python that actually runs and warns (never goes silent) if the registry check fails.
- Removed `docs/PRE-PUBLIC-CHECKLIST.md` (done when the repo went public). Fairsolid's surface-fit plan status updated.

## 2026-10-28: Claude skill zips next to each skill folder
- One import zip per skill at `skills/<name>.zip`, rebuilt by `scripts/pack_skill_zips.py` (optional wrappers: `scripts/pack-skill-zips.sh`, `scripts/pack-skill-zips.ps1`).
- GitHub Action `.github/workflows/skill-zips.yml` rebuilds on a same-repo PR whose head is not `main` and commits changed zips back to that branch, then runs the same pytest + zip-match checks as the verify job. On stale `main` it resets `chore/skill-zips` to `origin/main`, rebuilds the zips on that tree (`--force-with-lease` on that bot branch only), and opens a zip PR. It never pushes to `main`. GITHUB_TOKEN commits re-dispatch a verify run. Actor + `[skip ci]` prevent loops.
- Guard, gitignore and linkers treat only directories with `SKILL.md` as skills; zip files are not linked. `verify-install.sh` still does not scan `skills/`.

## 2026-10-26: skills are linked for Cursor too
- `setup.ps1 -LinkSkills` and `setup.sh --link-skills` now link each CAD skill into `~/.cursor/skills` as well as `~/.claude/skills` (Windows and WSL), so Cursor loads them from the repo. They no longer remove links in `~/.cursor/skills`; dead links there are pruned like in `~/.claude/skills`.

## 2026-10-23: setup installs the sim tools and checks itself
- `setup.sh` (and so `setup.ps1`) now installs the sim tools by default: `apt-sim.txt` (`setup.ps1` as root via `wsl -u root`, no password; `setup.sh` alone tries `sudo -n`, then a prompt in a terminal), the sim venv `~/simvenv` on the repo Python (3.13; an old 3.12 one is moved aside) with `SIM_VENV` in `~/.profile`, and uv in `~/.local/bin`. Opt out with `--no-sim` / `-NoSim`.
- Setup writes `~/.config/handbuilt-cad/env.sh` and loads it from the login file, so `CAD_HOME`, `CAD_PY`, `MODELS_DIR`, `HBCAD_PARTS_HOME`, `SIM_VENV` work in `bash -lc` (`--no-profile` skips).
- New `scripts/verify-install.sh`, run last by setup: exit 1 with a list of anything missing.
- AGENTS.md has a "Where every tool lives" table. Elmer and OpenFOAM are documented as optional, not installed by setup.

## 2026-10-23: setup.ps1 WSL step works in Windows PowerShell 5.1
- `setup.ps1` passes the WSL setup script to `wsl.exe` base64-encoded. Windows PowerShell 5.1 dropped the escaping of its double quotes, so bash failed with `syntax error near unexpected token`. Works the same in PowerShell 7.

## 2026-10-23: one clone on Windows + WSL
- Windows + WSL now uses one clone, in Windows (`<projects>\active\handbuilt-cad`). `setup.ps1` links it into WSL as `~/projects/handbuilt-cad` (`-WslLink`, `[paths] wsl_link`) and runs `setup.sh` through the link. It never clones in WSL. A correct link is left as is; a real folder or a link elsewhere stops setup with nothing changed. `-WslClone` and `wsl_clone` are gone.
- `setup.sh` on a Windows drive (`/mnt/<x>/`) puts the Linux venv outside the repo (`UV_PROJECT_ENVIRONMENT`, default `~/.venvs/handbuilt-cad`) so it doesn't clash with the Windows `.venv`, and prints the matching `CAD_PY`. `sim/env.sh` uses `CAD_PY` for `hbm-py`.
- Docs (README, AGENTS.md, CONTRIBUTING.md, wiki) describe the one-clone layout; git runs from the Windows clone.
- Review fixes: `setup.sh` always exports `UV_PROJECT_ENVIRONMENT`/`CAD_PY` and stops if it would point at the Windows `.venv`; new `scripts/hbcad-env.sh` gives the env to non-interactive shells (put it in `~/.profile`, not only `~/.bashrc`); `setup.ps1` single-quotes paths for bash and validates `wsl_link`; both setups stop clearly when the models path is a file; `--link-skills` prunes broken links left by old clones; line endings renormalized and `.sh` files made executable.

## 2026-10-22: setup no longer links skills by default; folder notes say who uses each folder
- `setup.sh` and `setup.ps1` no longer link `skills/` into `~/.claude/skills` and `~/.cursor/skills` unless asked: use `bash setup.sh --link-skills` (or `LINK_SKILLS=1`) or `setup.ps1 -LinkSkills`. `NO_SKILLS` and `-NoSkills` are gone. Existing links are left alone.
- Folder notes now say which tool uses the folder and that deleting or moving it breaks things, and name the repo and its GitHub link instead of a local clone path. `folder_notes.py --clone` is removed. Notes are strictly add-only (exclusive create).
- `setup.ps1` now also runs `setup.sh` in WSL (`-WslDistro`, default Ubuntu; superseded on 2026-10-23: there is no WSL clone any more, `setup.ps1` links the Windows clone to `~/projects/handbuilt-cad` and `-WslClone` / `wsl_clone` are gone), passing `-NoModels` / `-LinkSkills` through. It fails clearly if WSL or the distro is missing. `-NoWsl` opts out.
- `setup.sh` reads `parts_home` and `models_dir` only from the `[paths]` section of `local.toml`, like `tools/paths.py`.

## 2026-10-21: wall checker (`tools/checks/check_printed_walls.py`, #18)
New detection defaults that can change results for existing configs. Each one is a config key; set it to 0 to turn it off:
- `snap = 1e-4` mm: section segment ends closer than this are joined (fixes outlines dropped from a section).
- `despike = 0.02` mm: each section is opened and closed by this, which drops spikes and slits where two cut faces meet.
- `sliver = 0.01` mm: round-off slivers along the shared edges of a thin piece are dropped.
- `graze_sections = 4`: a spot seen by one axis family in fewer sections than this counts as planes grazing a square edge, and is dropped.
- `skin = 1.5` mm: a thin piece must stand at least this far out of the body to count as a cantilever.
These were tuned on a sweep of real printed parts, where the results matched the previous project-specific checker exactly.
Other configs may now report fewer spots. Re-run them and compare, or set the keys to 0 to get the old behaviour.
Also: `walls()` now uses `opts['step']` when `step` isn't passed (before, it silently used the 0.5 mm default).
