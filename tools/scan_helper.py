#!/usr/bin/env python3
"""Run Fairsolid on a scan without hard-coding where Fairsolid lives.

Fairsolid (https://github.com/living-relation/fairsolid) is found ONLY through
the FAIRSOLID_HOME environment variable: the folder of a Fairsolid checkout
that has its own virtual environment in .venv.

    export FAIRSOLID_HOME=~/projects/fairsolid
    python tools/scan_helper.py check
    python tools/scan_helper.py prepare ~/scans/bracket.stl --run /tmp/bracket_run
    python tools/scan_helper.py fit --run /tmp/bracket_run
    python tools/scan_helper.py run ~/scans/bracket.stl --run /tmp/bracket_run

Any extra arguments after the known ones are passed to Fairsolid unchanged.
Run folders should live outside this repo (scans and runs are never committed).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# helper name -> Fairsolid CLI sub-command
COMMANDS = {"prepare": "prepare-cmd", "run": "run-cmd", "fit": "fit", "status": "status", "review": "review"}


class FairsolidNotFound(RuntimeError):
    pass


def fairsolid_exe(env: dict | None = None) -> Path:
    """Return the Fairsolid executable inside $FAIRSOLID_HOME/.venv."""
    env = os.environ if env is None else env
    home = env.get("FAIRSOLID_HOME")
    if not home:
        raise FairsolidNotFound("FAIRSOLID_HOME is not set. Point it at your Fairsolid checkout, "
                                "e.g. export FAIRSOLID_HOME=~/projects/fairsolid")
    home_p = Path(home).expanduser()
    for cand in (home_p / ".venv" / "bin" / "fairsolid", home_p / ".venv" / "Scripts" / "fairsolid.exe"):
        if cand.is_file():
            return cand
    raise FairsolidNotFound(f"No Fairsolid venv found in {home_p}/.venv. Create it there first "
                            "(see the Fairsolid README).")


def build_cmd(command: str, scan: str | None, run_dir: str | None, extra: list[str], env: dict | None = None) -> list[str]:
    if command not in COMMANDS:
        raise ValueError(f"unknown command {command!r}; use one of {sorted(COMMANDS)}")
    cmd = [str(fairsolid_exe(env)), COMMANDS[command]]
    if command in ("prepare", "run"):
        if not scan:
            raise ValueError(f"{command} needs a scan file")
        cmd.append(str(Path(scan).expanduser().resolve()))
    if run_dir:
        cmd += ["--run", str(Path(run_dir).expanduser().resolve())]
    return cmd + list(extra)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=sorted(COMMANDS) + ["check"])
    ap.add_argument("scan", nargs="?", help="scan mesh or point cloud (prepare / run)")
    ap.add_argument("--run", dest="run_dir", help="Fairsolid run folder (keep it outside this repo)")
    args, extra = ap.parse_known_args(argv)
    try:
        if args.command == "check":
            exe = fairsolid_exe()
            print(f"Fairsolid found: {exe}")
            return subprocess.call([str(exe), "--help"], stdout=subprocess.DEVNULL)
        cmd = build_cmd(args.command, args.scan, args.run_dir, extra)
    except (FairsolidNotFound, ValueError) as e:
        print(f"scan_helper: {e}", file=sys.stderr)
        return 2
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
