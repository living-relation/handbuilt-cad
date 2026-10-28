# Changelog

## 2026-10-28: Claude skill zips next to each skill folder
- One import zip per skill at `skills/<name>.zip`, rebuilt by `scripts/pack_skill_zips.py` (wrappers: `scripts/pack-skill-zips.sh`, `scripts/pack-skill-zips.ps1`).
- GitHub Action `.github/workflows/skill-zips.yml` rebuilds on push to `main` that touches `skills/**` except `*.zip`, plus `workflow_dispatch`. The bot commit cannot retrigger itself (zip paths excluded, actor check, `[skip ci]`).
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
