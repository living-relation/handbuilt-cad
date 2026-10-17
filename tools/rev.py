#!/usr/bin/env python3
"""Create the next revision folder for a part in $MODELS_DIR. Never overwrites.

Layout: $MODELS_DIR/<job>_<MMDD>/revN/  with a SUMMARY.md template.

    export MODELS_DIR=~/models          # your own models folder
    python tools/rev.py bracket                 # new job dated today, or next rev of the newest bracket_* job
    python tools/rev.py bracket --date 1014     # job bracket_1014
    python tools/rev.py bracket_1014 --source ~/work/bracket  # also note where the files came from

It prints the new folder. Copy your STEP/STL/renders into it. Existing revs
are never touched; if anything already exists at the target the tool stops.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
from pathlib import Path

JOB_RE = re.compile(r"^(?P<name>.+)_(?P<mmdd>\d{4})$")
REV_RE = re.compile(r"^rev(?P<n>\d+)")

TEMPLATE = """# {job} / {rev}

- Created: {today}
- Source: {source}
- What changed from the previous rev:
- Status: (draft / checked / approved)
- Files:
  - (part.step, part.stl, renders, notes)
- Checks: (fit, CNC, strength)
"""


def models_dir(env=None) -> Path:
    env = os.environ if env is None else env
    d = env.get("MODELS_DIR")
    if not d:
        raise SystemExit("rev.py: MODELS_DIR is not set (point it at your models folder)")
    p = Path(d).expanduser()
    if not p.is_dir():
        raise SystemExit(f"rev.py: MODELS_DIR {p} does not exist")
    return p


def resolve_job(root: Path, job: str, date: str | None, today: _dt.date) -> str:
    if JOB_RE.match(job):
        return job
    if date:
        if not re.fullmatch(r"\d{4}", date):
            raise SystemExit("rev.py: --date must be MMDD")
        return f"{job}_{date}"
    existing = sorted(p.name for p in root.iterdir() if p.is_dir() and JOB_RE.match(p.name)
                      and JOB_RE.match(p.name).group("name") == job)
    return existing[-1] if existing else f"{job}_{today:%m%d}"


def next_rev(job_dir: Path) -> int:
    nums = [int(m.group("n")) for p in job_dir.iterdir() if p.is_dir() and (m := REV_RE.match(p.name))] if job_dir.is_dir() else []
    return max(nums, default=0) + 1


def create(root: Path, job: str, date: str | None = None, source: str = "", today: _dt.date | None = None) -> Path:
    today = today or _dt.date.today()
    job_name = resolve_job(root, job, date, today)
    job_dir = root / job_name
    rev_dir = job_dir / f"rev{next_rev(job_dir)}"
    job_dir.mkdir(exist_ok=True)
    rev_dir.mkdir()  # raises FileExistsError: never reuse a folder
    summary = rev_dir / "SUMMARY.md"
    with open(summary, "x", encoding="utf-8") as f:  # 'x' = fail if it exists
        f.write(TEMPLATE.format(job=job_name, rev=rev_dir.name, today=today.isoformat(), source=source or "(fill in)"))
    return rev_dir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", help="job name, or an existing <job>_<MMDD>")
    ap.add_argument("--date", help="MMDD for a new job (default: today)")
    ap.add_argument("--source", default="", help="where the files came from (for SUMMARY.md)")
    a = ap.parse_args(argv)
    try:
        print(create(models_dir(), a.job, a.date, a.source))
    except FileExistsError as e:
        print(f"rev.py: refusing to overwrite {e.filename}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
