# Install (ELI5)

[← Home](../../README.md) · next: [Setup](Setup.md) · [How to use](How-To-Use.md)

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
git clone https://github.com/living-relation/handbuilt-models.git
cd handbuilt-models
bash setup.sh
```

`setup.sh` does everything (see [Setup](Setup.md) for what it installs). It asks for your password once if it needs to install programs. It takes about **5-15 minutes** the first time.

**You should see** green `[ok]` lines at the end, like:

```
[ok]   model venv  .../handbuilt-models/.venv  (build123d 0.13.0)
[ok]   sim venv    /home/you/simvenv  (gmsh 4.15.2)
[ok]   CalculiX    /usr/bin/ccx
```

Yellow `[skip]` lines are optional extras. Red `[fail]` lines need fixing (see below).

## C. Try it

```bash
source sim-tools/env.sh
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
| Very slow when working in `/mnt/c/...` | Keep the folder in your Linux home (`~/handbuilt-models`), as above. |
| Using a Mac | Not tested. Use a Linux virtual machine, or install Docker/Ubuntu. |

To update later: `cd ~/handbuilt-models && git pull && bash setup.sh`.
