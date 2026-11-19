# handbuilt-cad

A toolkit for hand-built CAD parts: build scripts (build123d), model checks, drawings and
revision tooling, simple FEA/sim helpers, and a scan-to-STEP pipeline. It holds **code, specs
and docs only** - no part models. Finished models live in a `models` folder outside the repo
(`$MODELS_DIR`, default `<Desktop>/models`, created by setup).

## Setup (about 5 minutes)

Skills reach Claude Chat, Cowork, Claude Code, and Cursor only by installing the **handbuilt-cad** plugin. Setup does not link skills, and there is no zip upload. The four ways (shortcut, these commands, an agent prompt, and Plugins-menu clicks) are in [INSTALL.md](INSTALL.md). Plugin updates are the Plugins menu. The Claude catalog in this repo is named `handbuilt-cad-plugins`. It lists only this plugin.

`<projects>` is your Projects folder. Each block below is one command.

**Windows PowerShell, normal window (not Administrator).** One clone, in Windows. WSL uses that same folder through a link (`~/projects/handbuilt-cad`).

```powershell
git clone https://github.com/living-relation/handbuilt-cad.git <projects>\active\handbuilt-cad
```

```powershell
cd <projects>\active\handbuilt-cad
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
```

`setup.ps1` makes the WSL link only if nothing is there. A link that already points to this clone is left
as is. If `~/projects/handbuilt-cad` is a real folder (an old WSL clone) or a link to somewhere else,
it stops and changes nothing; move the old folder to an archive yourself and re-run. Windows uses
`<repo>\.venv`; the Linux venv lives outside the repo at `~/.venvs/handbuilt-cad` (`UV_PROJECT_ENVIRONMENT`).
`-NoWsl` skips WSL. `-NoModels` and `-NoSim` pass through. Do not pass `-LinkSkills`.

**Plain Linux, normal terminal (not root):**

```bash
git clone https://github.com/living-relation/handbuilt-cad.git ~/projects/handbuilt-cad
```

```bash
cd ~/projects/handbuilt-cad
```

```bash
bash setup.sh
```

`.gitattributes` keeps LF in the repo (CRLF only for .bat/.cmd/.ps1).

**Plugin, normal terminal (not Administrator and not root).** Skip this if your claude.ai account already has the plugin, or Claude Code will load it twice. Leave marketplace auto-update off. Details and the other routes are in [INSTALL.md](INSTALL.md).

```bash
claude plugin marketplace add living-relation/handbuilt-cad
```

```bash
claude plugin install handbuilt-cad@handbuilt-cad-plugins
```

Double-click `pull.cmd` in the clone (or run it from a prompt) to `git pull --ff-only` this repo only. Double-click `install.cmd` (or run it from a normal prompt, not Administrator; extra args pass through, e.g. `install.cmd -NoSim`) to run `setup.ps1`. That shortcut installs the toolkit only. It does not install the plugin.

Then use the venv: `$CAD_PY tools/cnc_check.py --help` (`setup.sh` prints the `CAD_PY` to export: `.venv/bin/python`, or `~/.venvs/handbuilt-cad/bin/python` in WSL).

Setup ends with `scripts/verify-install.sh`; if it prints MISSING, setup failed. Where each tool lives: `AGENTS.md`.

CI still rebuilds `skills/<name>.zip` on a same-repo PR whose head is not `main`, and commits any changed zips back onto that PR branch (never onto `main`). Those zips are not how you install skills. If `main` is stale, CI opens or updates `chore/skill-zips` instead. That zip PR needs the repo setting **Allow GitHub Actions to create and approve pull requests**. GITHUB_TOKEN commits do not start checks on their own; the workflow re-dispatches a verify run on the new commit. The local pack script is optional.

**Windows PowerShell, normal window (not Administrator).**

```powershell
powershell -NoProfile -File scripts\pack-skill-zips.ps1
```

**Plain Linux, normal terminal (not root).**

```bash
bash scripts/pack-skill-zips.sh
```

## What's where
| Folder | What |
|---|---|
| `tools/` | shared toolkit (cnc_check, blend, rev, scan_helper, features, quick_fea, views, viewer, an_fitting), `checks/`, `render/` (smooth renders, capped sections) |
| `drawing/` | drawing engine, rev letters (`revs.py`), drawing rules and templates |
| `sim/` | meshing/FEA helper scripts, smoke tests, FreeCAD launcher wrappers |
| parts home (`~/cad-parts`, outside git) | part build scripts (`<job>/src`) and working outputs (`<job>/runs`); created by `setup.sh`, found through `HBCAD_PARTS_HOME` (`tools/paths.py`). Finished results go to the models folder (`publish-to-models`) |
| `pipelines/fairsolid/` | scan mesh -> parametric STEP pipeline (own venv, see its README). This is Fairsolid (the old fairsolid GitHub repo was deleted on 2026-10-21), see [`docs/FAIRSOLID.md`](docs/FAIRSOLID.md) |
| `examples/` | small generic examples |
| `skills/` | agent skills. They reach Claude and Cursor through the handbuilt-cad plugin ([INSTALL.md](INSTALL.md), `skills/README.md`). CI zip files live next to each skill folder as `skills/<name>.zip` and are not the install path |
| `docs/` | wiki, tools index (`docs/TOOLS.md`), history |

## Rules in one line
PRs only, no part files, no secrets, follow `AGENTS.md` and `CONTRIBUTING.md`, never bypass the hooks.
