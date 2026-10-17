# handbuilt-cad

A toolkit for hand-built CAD parts: build scripts (build123d), model checks, drawings and
revision tooling, simple FEA/sim helpers, and a scan-to-STEP pipeline. It holds **code, specs
and docs only** - no part models. Finished models live in a `models` folder outside the repo
(`$MODELS_DIR`, default `<Desktop>/models`, created by setup).

## Setup (about 5 minutes)

**WSL / Linux (the working copy):**
```bash
git clone <repo-url> ~/projects/handbuilt-cad
cd ~/projects/handbuilt-cad
bash setup.sh            # pinned uv + Python, .venv from uv.lock, gitleaks, git hooks, models folder
```
**Windows (pull-only copy, optional):**
```powershell
git clone <repo-url> C:\projects\active\handbuilt-cad
powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1
```
Both clones get the same `.gitattributes` (LF in the repo, CRLF only for .bat/.ps1), so a
Windows clone and a WSL clone of the same commit show no fake changes.

Then use the venv: `.venv/bin/python tools/cnc_check.py --help` (or set `CAD_PY` to it).

## What's where
| Folder | What |
|---|---|
| `tools/` | shared toolkit (cnc_check, blend, rev, scan_helper, features, quick_fea, views, viewer, an_fitting), `checks/`, `render/` (smooth renders, capped sections) |
| `drawing/` | drawing engine, rev letters (`revs.py`), drawing rules and templates |
| `sim/` | meshing/FEA helper scripts, smoke tests, FreeCAD launcher wrappers |
| `parts/` | build scripts and specs, one folder per part (no model files) |
| `pipelines/fairsolid/` | scan mesh -> parametric STEP pipeline (own venv, see its README). Vendored copy: the live fairsolid repo is the current source of truth, see [`docs/FAIRSOLID.md`](docs/FAIRSOLID.md) |
| `examples/` | small generic examples |
| `skills/` | agent skills (Claude, Cursor and bots install them from here); cnc-part-check, publish-to-models and scan-to-parametric are owned by SteveCAD (see `skills/README.md`) |
| `docs/` | wiki, tools index (`docs/TOOLS.md`), history |

## Rules in one line
PRs only, no part files, no secrets, follow `AGENTS.md` and `CONTRIBUTING.md`, never bypass the hooks.
