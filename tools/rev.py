#!/usr/bin/env python3
"""Create the next lettered revision folder in $MODELS_DIR. Never edits an existing rev.

Layout (Daniel, 2026-11-20): $MODELS_DIR/<subject>-rev<current>/rev<LETTER>/
(clerical: rev<LETTER>.<NN>/). The job folder is renamed to the current rev when a new one is filed.
An old <subject>_<MMDD> folder is renamed to this form on the next filing. Rules (drawing/DRAWING-RULES.md 1-5,
skills/publish-to-models):
- Letters A..Z skip I, L, O and Q in every position, then AA, AB ... (drawing/revs.py does the counting).
- Rev A is only for a brand-new model. A model change takes the next letter after the highest rev<LETTER> folder.
- A clerical rev (drawing-only change to an already released drawing, no fit/form/function change) adds a decimal under
  the current letter: revD -> revD.01 -> revD.02. It holds drawings, SUMMARY.md and a manifest only, never a model file.
- Old numeric rev<N> folders are never converted. If a job has only those, the letter must come from the model's
  counted releases: pass --releases N (past releases; next letter follows) or --letter X.
- --prune keeps two model letters (the newest and the one before) and the clerical decimals of those letters.
  It deletes older rev folders. A folder that contains a 3D scan is left in place. --date is accepted and ignored
  (the date is no longer part of the folder name).

    export MODELS_DIR=~/models
    python tools/rev.py bracket                     # bracket-revA/revA, or the next letter
    python tools/rev.py bracket --clerical          # drawing-only: revD -> revD.01, folder renamed bracket-revD.01
    python tools/rev.py knuckle --releases 7        # only old revN folders and 7 counted releases -> revH
    python tools/rev.py bracket --prune             # drop rev folders older than the two newest letters

It prints the new folder. Files inside an existing rev folder are never edited; if the target rev exists the tool stops.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "drawing"))
import revs  # noqa: E402  (letters, clerical decimals: the same code the drawing engine uses)

LEGACY_JOB_RE = re.compile(r"^(?P<name>.+)_(?P<mmdd>\d{4}|\d{6})$")
SUBJECT_REV_RE = re.compile(r"^(?P<subject>.+)-rev(?P<letter>[A-Z]+)(?:\.(?P<cl>\d{2}))?$")
LETTER_RE = re.compile(r"^rev(?P<letter>[A-Z]+)(?:\.(?P<cl>\d{2}))?$")
NUMERIC_RE = re.compile(r"^rev\d+")
SCAN_SUFFIXES = {".ply", ".e57", ".pts", ".xyz", ".las", ".laz"}

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
- Checks: (valid body, STEP round-trip, fit, CNC, structural-only minimum wall, tools/checks/release_structure.py)

## Bought parts
(none)
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


def parse_subject(job: str) -> str:
    """Subject from a bare name, a `<subject>-rev<current>` folder, or a legacy `<subject>_<MMDD>` folder."""
    m = SUBJECT_REV_RE.match(job)
    if m and revs.is_valid_letter(m.group("letter")):
        return m.group("subject")
    m = LEGACY_JOB_RE.match(job)
    if m:
        return m.group("name")
    return job


def _subject_rev_rank(path: Path):
    m = SUBJECT_REV_RE.match(path.name)
    if not m or parse_subject(path.name) != m.group("subject"):
        return None
    if not revs.is_valid_letter(m.group("letter")):
        return None
    return (revs.letter_to_index(m.group("letter")), int(m.group("cl") or 0))


def find_existing(root: Path, subject: str) -> Path | None:
    """The job folder for this subject: newest `<subject>-rev<current>`, else the last legacy `<subject>_<MMDD>`."""
    if not root.is_dir():
        return None
    styled, legacy = [], []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        m = SUBJECT_REV_RE.match(p.name)
        if m and m.group("subject") == subject and revs.is_valid_letter(m.group("letter")):
            styled.append(p)
        else:
            leg = LEGACY_JOB_RE.match(p.name)
            if leg and leg.group("name") == subject:
                legacy.append(p)
    if styled:
        return max(styled, key=lambda p: _subject_rev_rank(p))
    return sorted(legacy, key=lambda p: p.name)[-1] if legacy else None


def job_folder_name(subject: str, rev_name: str) -> str:
    return f"{subject}-rev{rev_name[3:]}"


def _has_scan(folder: Path) -> bool:
    for p in folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in SCAN_SUFFIXES:
            return True
    return False


def prune_plan(job_dir: Path, keep: int = 2):
    """(folder names to delete, folder names kept because they hold a 3D scan).

    Keeps `keep` model letters (newest first) and every clerical decimal of those letters.
    Older letters, their clerical decimals, and old numeric rev<N> folders (once any lettered rev exists)
    are dropped. With no lettered rev, the highest `keep` numeric folders stay.
    """
    model, clerical, numeric = {}, {}, []
    if job_dir.is_dir():
        for p in job_dir.iterdir():
            if not p.is_dir():
                continue
            m = LETTER_RE.match(p.name)
            if m and revs.is_valid_letter(m.group("letter")):
                letter, cl = m.group("letter"), int(m.group("cl") or 0)
                if cl == 0:
                    model[letter] = p
                else:
                    clerical.setdefault(letter, []).append(p)
            elif NUMERIC_RE.match(p.name):
                numeric.append(p)
    letters = sorted(model, key=revs.letter_to_index)
    kept = set(letters[-keep:]) if keep else set()
    drop, scans = [], []

    def consider(path: Path):
        if _has_scan(path):
            scans.append(path.name)
        else:
            drop.append(path.name)

    for letter, path in model.items():
        if letter not in kept:
            consider(path)
    for letter, paths in clerical.items():
        if letter not in kept:
            for path in paths:
                consider(path)
    if letters:
        for p in numeric:
            consider(p)
    else:
        ordered = sorted(numeric, key=lambda p: p.name)
        for p in (ordered[:-keep] if keep else ordered):
            consider(p)
    return sorted(drop), sorted(scans)


def prune_revs(job_dir: Path, apply: bool = False, keep: int = 2):
    drop, scans = prune_plan(job_dir, keep=keep)
    if apply:
        for name in drop:
            shutil.rmtree(job_dir / name)
    return drop, scans


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
    if date and not re.fullmatch(r"\d{4}", date):
        raise SystemExit("rev.py: --date must be MMDD")
    subject = parse_subject(job)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", subject):
        raise RevError(f"bad subject {subject!r}")
    existing = find_existing(root, subject)
    name = next_rev(existing if existing is not None else root / ".no-such-job",
                    clerical=clerical, letter=letter, releases=releases)
    dest = root / job_folder_name(subject, name)
    if existing is not None and dest.exists() and dest.resolve() != existing.resolve():
        raise RevError(f"{dest.name} already exists beside {existing.name}")
    job_dir = existing if existing is not None else dest
    rev_dir = job_dir / name
    job_dir.mkdir(exist_ok=True)
    rev_dir.mkdir()  # raises FileExistsError: never reuse a folder
    label = name[3:]
    job_name = dest.name
    if clerical:
        note = f" (clerical: drawing-only, under rev{label.split('.')[0]}; not listed in REVLOG.md)"
        files = "drawings\\ (PDF/DXF/SVG) only - no model file in a clerical rev"
        evidence = f"clerical decimal under rev{label.split('.')[0]}"
    else:
        note = ""
        files = ("assembly STEP at the rev root, Parts\\ (one file per part or subassembly), drawings\\, src\\, "
                 "reference\\ (maker models), REVLOG.md, MADE-WITH.md. STL only if a print job needs it")
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
    if existing is not None and existing.resolve() != dest.resolve():
        existing.rename(dest)
        rev_dir = dest / name
    return rev_dir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", help="subject, or an existing <subject>-rev<current> or legacy <subject>_<MMDD>")
    ap.add_argument("--date", help="accepted and ignored; the folder name is <subject>-rev<current>")
    ap.add_argument("--source", default="", help="where the files came from (for SUMMARY.md)")
    ap.add_argument("--clerical", action="store_true", help="drawing-only change: next .NN decimal under the current letter")
    ap.add_argument("--letter", help="use this letter (must be newer than every existing rev folder)")
    ap.add_argument("--releases", type=int, help="number of past releases of the model (old numeric jobs); next letter follows")
    ap.add_argument("--prune", action="store_true",
                    help="delete rev folders beyond the two newest model letters; never delete a 3D scan")
    a = ap.parse_args(argv)
    try:
        if a.prune:
            if a.clerical or a.letter or a.releases is not None:
                raise RevError("--prune does not take --clerical, --letter or --releases")
            root = models_dir()
            job_dir = find_existing(root, parse_subject(a.job))
            if job_dir is None:
                raise RevError(f"no job folder for {parse_subject(a.job)!r}")
            drop, scans = prune_revs(job_dir, apply=True)
            print(f"pruned {job_dir}: dropped {', '.join(drop) or '(none)'}; kept for scans {', '.join(scans) or '(none)'}")
            return 0
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
