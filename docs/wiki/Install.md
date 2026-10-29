# Install (ELI5)

[← Home](../../README.md) · next: [Setup](Setup.md) · [How to use](How-To-Use.md)

## The whole thing in 3 steps

1. **Install it** (below). This is the only part you might do by hand, and your agent can do it for you too.
2. **Point your AI agent at this repo** (Claude Code, Cursor, Codex, Grok Bot or similar). Tell it where the folder is and to read `README.md`.
3. **Hand it your scan, mesh or idea.** The agent measures, builds, checks and shows you the result.

You never need to run the commands on the other wiki pages. They're instructions for the agent.

**What to tell your agent** (copy, then change the details):

> Use the handbuilt-cad repo in `~/projects/handbuilt-cad` (start with `README.md` and `docs/wiki/AI-agents.md`). Here's a scan of my bracket: `~/scans/bracket.stl`. Make a clean STEP I can machine from 6061, keep the holes where they are on the scan, run the fit, CNC and strength checks, and show me the 6-view sheet before you call it done.

Or start from an idea instead of a scan:

> Using handbuilt-cad, design a 90° -10 AN adapter pipe, no longer than 53 mm, with a smooth bore. Show me the 6-view sheet and the checks.

## Installing

**What you get:** a folder of tools that turn measurements into clean CAD parts (STEP files) for CNC machining, and check them (fit, strength, pictures). It runs on **Linux**. On Windows it runs inside **WSL** (a small Linux that lives inside Windows).

You need: internet, about **5 GB** free disk, and your login password (for installing programs).

## A. Windows PC (do this once)

1. Click Start, type **PowerShell**, right-click it, pick **Run as administrator**.
2. Copy-paste this and press Enter:
   ```powershell
   wsl --install -d Ubuntu
   ```
3. Restart the PC when it asks. Ubuntu opens by itself and asks for a **user name and password**. Pick any (remember the password).
4. From now on, open **Ubuntu** from the Start menu. That black window is where you paste the commands below.

**You should see** a prompt like `you@PC:~$`.

## B. Get the toolkit (Windows-in-Ubuntu or plain Linux)

Paste these lines one at a time:

```bash
sudo apt update && sudo apt install -y git curl python3
git clone https://github.com/living-relation/handbuilt-cad.git
cd handbuilt-cad
bash setup.sh
```

**On Windows, use one clone, in Windows, instead of the lines above.** Clone in PowerShell to `<projects>\active\handbuilt-cad` and run `setup.ps1` there. It links that folder into WSL as `~/projects/handbuilt-cad` (or `-WslLink` / `[paths] wsl_link` in `local.toml`) and runs this WSL step for you (`wsl -d Ubuntu`) through the link. It never makes a second clone. If the link is already there and points to the clone, it's left as is. If that path is a real folder (an old WSL clone) or a link to somewhere else, it stops and changes nothing: move the old folder to an archive (e.g. `~/cad-parts/_archive/handbuilt-cad-wsl-<date>`) and re-run. The Linux venv goes to `~/.venvs/handbuilt-cad` so it never clashes with the Windows `.venv`. It always links CAD skills into `~/.claude/skills` (Cursor reads that folder too; `-LinkSkills` is a no-op). At the end it shows a Windows popup listing the skill zips and reminding you to upload them in the Claude desktop app for each Claude account; `-NoPopup` / `-Quiet` skip the popup (also skipped in CI). It passes `-NoModels` through as `--no-models`, stops with a clear error if WSL or Ubuntu is missing, and `-NoWsl` skips it. `setup.sh` does everything (see [Setup](Setup.md) for what it installs). Before that it installs the sim programs (`apt-sim.txt`) as root through `wsl -u root`, so no WSL password is needed; `-NoSim` skips them. It takes about **5-15 minutes** the first time.

**You should see** green `[ok]` lines at the end, like:

```
[ok]   model venv  .../handbuilt-cad/.venv  (build123d 0.13.0)
[ok]   sim venv    /home/you/simvenv  (gmsh 4.15.2)
[ok]   CalculiX    /usr/bin/ccx
```

Yellow `[skip]` lines are optional extras. Red `[fail]` lines need fixing (see below).

## C. Try it

```bash
source sim/env.sh
bash examples/bracket/run_all.sh
```

**You should see** "ALL PASS" for the hole check and a "safety factor" line. New files appear in `examples/bracket/`.

To see the files from Windows: in the Ubuntu window type `explorer.exe .` (with the dot). Open the `.png` pictures, open `bracket_viewer.html` in your browser, and open `bracket.step` in Fusion / your CAM program.

## Common problems

| You see | Do this |
|---|---|
| `wsl: command not found` or "virtualization disabled" | Turn on virtualization in the PC's BIOS (often called SVM or VT-x), then try step A again. |
| `git: command not found` | `sudo apt install -y git` |
| `Permission denied` on setup.sh | Run it as `bash setup.sh` (not `./setup.sh`). |
| `[fail] model venv install failed` | Check the internet, then just run `bash setup.sh` again. It's safe to re-run. |
| `[fail] CalculiX missing` | Run `bash setup.sh` again and type your password when it asks. |
| Very slow when working in `/mnt/c/...` | Expected with the one-clone layout: the repo lives on the Windows drive and WSL reaches it through `~/projects/handbuilt-cad`. Keep heavy run outputs in the parts home (`~/cad-parts`, Linux side) and the venv in `~/.venvs/handbuilt-cad` (both already set up that way). |
| Using a Mac | Not tested. Use a Linux virtual machine, or install Docker/Ubuntu. |

To update later: on Windows, `git pull --ff-only` in the one clone (PowerShell), then `bash setup.sh` in WSL from `~/projects/handbuilt-cad`; on plain Linux, `cd ~/projects/handbuilt-cad && git pull --ff-only && bash setup.sh`.
