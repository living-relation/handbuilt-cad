# handbuilt-cad

A toolkit for hand-built CAD parts: build scripts (build123d), model checks, drawings and
revision tooling, simple FEA/sim helpers, and a scan-to-STEP pipeline. It holds **code, specs
and docs only** - no part models. Finished models live in a `models` folder outside the repo
(`$MODELS_DIR`, default `<Desktop>/models`, created by setup).

## Setup (about 5 minutes)

**Windows + WSL: one clone, in Windows.** There is no separate WSL clone. WSL uses the same folder
through a link (`~/projects/handbuilt-cad -> /mnt/c/<projects>/active/handbuilt-cad`).
```powershell
git clone <repo-url> <projects>\active\handbuilt-cad
cd <projects>\active\handbuilt-cad
powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1   # Windows part, then links the clone into WSL and runs setup.sh there; -NoWsl skips WSL, -NoModels / -LinkSkills / -NoSim pass through
```
`setup.ps1` makes the WSL link only if nothing is there. A link that already points to this clone is left
as is. If `~/projects/handbuilt-cad` is a real folder (an old WSL clone) or a link to somewhere else,
it stops and changes nothing; move the old folder to an archive yourself and re-run. Windows uses
`<repo>\.venv`; the Linux venv lives outside the repo at `~/.venvs/handbuilt-cad` (`UV_PROJECT_ENVIRONMENT`).

**Plain Linux (no Windows):**
```bash
git clone <repo-url> ~/projects/handbuilt-cad
cd ~/projects/handbuilt-cad
bash setup.sh            # pinned uv + Python, .venv from uv.lock, sim tools (no password via setup.ps1), gitleaks, hooks, models folder, env file, verify
```
`.gitattributes` keeps LF in the repo (CRLF only for .bat/.ps1).

Then use the venv: `$CAD_PY tools/cnc_check.py --help` (`setup.sh` prints the `CAD_PY` to export: `.venv/bin/python`, or `~/.venvs/handbuilt-cad/bin/python` in WSL).

Setup ends with `scripts/verify-install.sh`; if it prints MISSING, setup failed. Where each tool lives: `AGENTS.md`.

## What's where
| Folder | What |
|---|---|
| `tools/` | shared toolkit (cnc_check, blend, rev, scan_helper, features, quick_fea, views, viewer, an_fitting), `checks/`, `render/` (smooth renders, capped sections) |
| `drawing/` | drawing engine, rev letters (`revs.py`), drawing rules and templates |
| `sim/` | meshing/FEA helper scripts, smoke tests, FreeCAD launcher wrappers |
| parts home (`~/cad-parts`, outside git) | part build scripts (`<job>/src`) and working outputs (`<job>/runs`); created by `setup.sh`, found through `HBCAD_PARTS_HOME` (`tools/paths.py`). Finished results go to the models folder (`publish-to-models`) |
| `pipelines/fairsolid/` | scan mesh -> parametric STEP pipeline (own venv, see its README). This is Fairsolid (the old fairsolid GitHub repo was deleted on 2026-10-21), see [`docs/FAIRSOLID.md`](docs/FAIRSOLID.md) |
| `examples/` | small generic examples |
| `skills/` | agent skills (Claude, Cursor and bots install them from here; see `skills/README.md`) |
| `docs/` | wiki, tools index (`docs/TOOLS.md`), history |

## Rules in one line
PRs only, no part files, no secrets, follow `AGENTS.md` and `CONTRIBUTING.md`, never bypass the hooks.
