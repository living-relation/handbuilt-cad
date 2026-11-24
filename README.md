# handbuilt-cad

A toolkit for hand-built CAD parts: build scripts (build123d), model checks, drawings and
revision tooling, simple FEA/sim helpers, and a scan-to-STEP pipeline. It holds **code, specs
and docs only** - no part models. Finished models live in a `models` folder outside the repo
(`$MODELS_DIR`, default `<Desktop>/models`, created by setup).

## Setup (about 5 minutes)

Skip this if you don't use Claude.

1. Open https://claude.ai/customize/plugins and sign in.
2. Click Add, then Add marketplace, then Add from a repository.
3. Paste https://github.com/living-relation/handbuilt-cad, turn Sync automatically on, and confirm.
4. Wait for it to load; it opens the handbuilt-cad summary page.
5. Click Add (top right) on that page to install it. Adding the repo alone does not install it.
6. Fully quit Claude desktop from the tray icon and reopen it.

Updates arrive automatically after merges to main.

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
`-NoWsl` skips WSL. `-NoModels` and `-NoSim` pass through. Setup does not copy skills onto this machine.

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

Skip this if you don't use Cursor.

Open a Cursor agent chat in any folder and paste this:

```text
Install the handbuilt-cad Cursor plugin from https://github.com/living-relation/handbuilt-cad: if it is not cloned yet, clone it into my projects folder; then copy the repo (without .git and .venv) to ~/.cursor/plugins/local/handbuilt-cad, replacing any old copy. Tell me when done so I can fully quit and reopen Cursor.
```

Manual fallback. Windows PowerShell 5.1, normal window, not admin. `<projects-folder>` is the folder where you keep clones, for example `C:\Users\<you>\projects`.

1. `cd <projects-folder>`

```powershell
cd <projects-folder>
```

2. Clone if needed: `git clone https://github.com/living-relation/handbuilt-cad`

```powershell
git clone https://github.com/living-relation/handbuilt-cad
```

3. `cd <projects-folder>\handbuilt-cad`

```powershell
cd <projects-folder>\handbuilt-cad
```

4. Copy the Cursor plugin. This does not open a browser.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-plugins.ps1
```

5. Fully quit and reopen Cursor.

Double-click `pull.cmd` in the clone (or run it from a prompt) to `git pull --ff-only` this repo only. Double-click `install.cmd` (or run it from a normal prompt, not Administrator; extra args pass through, e.g. `install.cmd -NoSim`) to run `setup.ps1`. That shortcut installs the toolkit only. It does not add the plugin and it does not open a browser. Double-click `install-plugins.cmd` for the Cursor copy. That runs only because you started it. It does not open a browser. It copies `.cursor-plugin` and `skills` to `~/.cursor/plugins/local/handbuilt-cad` and replaces the old copy. Fully quit and reopen Cursor after the copy.

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
| `skills/` | agent skills. They reach Claude and Cursor through the handbuilt-cad plugin ([INSTALL.md](INSTALL.md), `skills/README.md`) |
| `docs/` | wiki, tools index (`docs/TOOLS.md`), history |

## Rules in one line
PRs only, no part files, no secrets, follow `AGENTS.md` and `CONTRIBUTING.md`, never bypass the hooks.
