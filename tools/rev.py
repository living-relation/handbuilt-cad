#!/usr/bin/env python3
"""Create the next lettered revision folder for a part in $MODELS_DIR. Never overwrites.

Layout: $MODELS_DIR/<job>_<MMDD>/rev<LETTER>/ (model release) or rev<LETTER>.<NN>/ (clerical, drawings only),
each with a SUMMARY.md template. Rules (drawing/DRAWING-RULES.md 1-5, skills/publish-to-models step 3):
- Letters A..Z skip I, L, O and Q in every position, then AA, AB ... (drawing/revs.py does the counting).
- Rev A is only for a brand-new model. A model change takes the next letter after the highest rev<LETTER> folder.
- A clerical rev (drawing-only change to an already released drawing, no fit/form/function change) adds a decimal under
  the current letter: revD -> revD.01 -> revD.02. It holds drawings, SUMMARY.md and a manifest only, never a model file.
- Old numeric rev<N> folders are never converted or renamed. If a job has only those, the letter must come from the
  model's counted releases: pass --releases N (past releases; next letter follows) or --letter X.

    export MODELS_DIR=~/models                    # your own models folder
    python tools/rev.py bracket                   # new job dated today -> bracket_MMDD/revA, or the next letter
    python tools/rev.py bracket --date 1014       # job bracket_1014
    python tools/rev.py bracket_1014 --clerical   # drawing-only change: revD -> revD.01
    python tools/rev.py knuckle_1009 --releases 7 # job with only old revN folders and 7 counted releases -> revH
    python tools/rev.py bracket_1014 --source ~/work/bracket  # note where the files came from

It prints the new folder. Existing revs are never touched; if anything already exists at the target the tool stops.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "drawing"))
import revs  # noqa: E402  (letters, clerical decimals: the same code the drawing engine uses)

JOB_RE = re.compile(r"^(?P<name>.+)_(?P<mmdd>\d{4}|\d{6})$")
LETTER_RE = re.compile(r"^rev(?P<letter>[A-Z]+)(?:\.(?P<cl>\d{2}))?$")
NUMERIC_RE = re.compile(r"^rev\d+")

TEMPLATE = """# {job} / {rev}

- Created: {today}
- Rev: {rev_label}{clerical_note}
- Evidence for the letter: {evidence}
- Source: {source}
- Made with: (tool, e.g. build123d / Fusion; also MADE-WITH.md)
- What changed from the previous rev:
- Status: (candidate / approved; FEA not run until the geometry is approved)
- Files:
  - {files}
- Checks: (valid body, STEP round-trip, fit, CNC, structural-only minimum wall)
"""


class RevError(ValueError):
    """The next rev can't be worked out without a decision (e.g. only old numeric folders exist)."""


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


def scan(job_dir: Path):
    """([(letter, clerical), ...] from rev<LETTER>[.<NN>] folders, True if any old numeric rev<N> folder exists)."""
    lettered, numeric = [], False
    if job_dir.is_dir():
        for p in job_dir.iterdir():
            if not p.is_dir():
                continue
            m = LETTER_RE.match(p.name)
            if m and revs.is_valid_letter(m.group("letter")):
                lettered.append((m.group("letter"), int(m.group("cl") or 0)))
            elif NUMERIC_RE.match(p.name):
                numeric = True
    return lettered, numeric


def next_rev(job_dir: Path, clerical: bool = False, letter: str | None = None, releases: int | None = None) -> str:
    """Folder name of the next rev in job_dir (see the module docstring for the rules)."""
    lettered, numeric = scan(job_dir)
    top = max((l for l, _ in lettered), key=revs.letter_to_index, default=None)
    if clerical:
        if letter or releases is not None:
            raise RevError("--clerical takes the current letter; don't combine it with --letter / --releases")
        if top is None:
            raise RevError("a clerical rev needs a released rev<LETTER> folder (an unreleased drawing keeps its counted letter)")
        n = max(c for l, c in lettered if l == top) + 1
        return "rev" + revs.format_rev(top, n)
    if letter is not None and releases is not None:
        raise RevError("give --letter or --releases, not both")
    if releases is not None:
        if releases < 0:
            raise RevError("--releases must be >= 0")
        letter = revs.letter_from_release_count(releases + 1)
    if letter is not None:
        letter = letter.strip().upper()
        if not revs.is_valid_letter(letter):
            raise RevError(f"not a valid rev letter: {letter!r} (A-Z, no I, L, O or Q)")
        if top is not None and revs.letter_to_index(letter) <= revs.letter_to_index(top):
            raise RevError(f"rev{letter} is not newer than the highest existing rev{top}; never reuse a letter")
        return f"rev{letter}"
    if top is not None:                     # lettered folders win over old numeric ones
        return "rev" + revs.next_letter(top)
    if numeric:
        raise RevError("this job has only old numeric rev<N> folders: don't convert them. Count the model's real releases "
                       "and pass --releases N (or --letter X); list the releases as evidence in SUMMARY.md")
    return "revA"                           # brand-new model


def create(root: Path, job: str, date: str | None = None, source: str = "", today: _dt.date | None = None,
           clerical: bool = False, letter: str | None = None, releases: int | None = None) -> Path:
    today = today or _dt.date.today()
    job_name = resolve_job(root, job, date, today)
    job_dir = root / job_name
    name = next_rev(job_dir, clerical=clerical, letter=letter, releases=releases)
    rev_dir = job_dir / name
    job_dir.mkdir(exist_ok=True)
    rev_dir.mkdir()  # raises FileExistsError: never reuse a folder
    label = name[3:]
    if clerical:
        note = f" (clerical: drawing-only, under rev{label.split('.')[0]}; not listed in REVLOG.md)"
        files = "drawings\\ (PDF/DXF/SVG) only - no model file in a clerical rev"
        evidence = f"clerical decimal under rev{label.split('.')[0]}"
    else:
        note = ""
        files = "model STEP (STL only if a print job needs it), drawings\\, src\\, reference\\, REVLOG.md, MADE-WITH.md"
        if releases is not None:
            evidence = f"{releases} counted past release(s) (list them here)"
        elif letter is not None:
            evidence = "letter given by hand (list the counted releases here)"
        elif label == "A":
            evidence = "brand-new model (Rev A = Initial)"
        else:
            evidence = "next letter after the highest existing rev folder"
    with open(rev_dir / "SUMMARY.md", "x", encoding="utf-8") as f:  # 'x' = fail if it exists
        f.write(TEMPLATE.format(job=job_name, rev=name, rev_label=label, clerical_note=note, evidence=evidence,
                                today=today.isoformat(), source=source or "(fill in)", files=files))
    return rev_dir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", help="job name, or an existing <job>_<MMDD>")
    ap.add_argument("--date", help="MMDD for a new job (default: today)")
    ap.add_argument("--source", default="", help="where the files came from (for SUMMARY.md)")
    ap.add_argument("--clerical", action="store_true", help="drawing-only change: next .NN decimal under the current letter")
    ap.add_argument("--letter", help="use this letter (must be newer than every existing rev folder)")
    ap.add_argument("--releases", type=int, help="number of past releases of the model (old numeric jobs); next letter follows")
    a = ap.parse_args(argv)
    try:
        print(create(models_dir(), a.job, a.date, a.source, clerical=a.clerical, letter=a.letter, releases=a.releases))
    except FileExistsError as e:
        print(f"rev.py: refusing to overwrite {e.filename}", file=sys.stderr)
        return 1
    except RevError as e:
        print(f"rev.py: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
