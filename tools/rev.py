#!/usr/bin/env python3
"""Next per-part revision card in $MODELS_DIR. Never edits an existing rev file.

A job folder is `<subject>_<MMDD>` (first publish date). It is not a rev: parts in it
can be at different letters. A designed part and its drawing use `<part>-rev<LETTER>`
(clerical `<part>-rev<LETTER>.<NN>`). This tool writes the data card only.

The models folder holds usable models and drawings, plus that card and the folder
README. Scripts, runs, scans and working notes stay in the parts home
(`tools/paths.py`, default ~/cad-parts/<job>/).

Bought maker CAD lives in `reference/` with no rev. `--prune` deletes only older
files of one part (newest letter and the one before, plus clerical decimals of
those letters). It never deletes the job folder, `reference/`, or a file with no rev.

    export MODELS_DIR=~/models
    python tools/rev.py bracket --part leg          # bracket_MMDD/leg-revA.md
    python tools/rev.py bracket --part leg --clerical
    python tools/rev.py knuckle --releases 7        # only old revN folders: next letter from the count
    python tools/rev.py bracket --prune

Letters skip I, L, O and Q (drawing/revs.py). Old numeric rev<N> folders are never converted.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "drawing"))
import revs  # noqa: E402

LEGACY_JOB_RE = re.compile(r"^(?P<name>.+)_(?P<mmdd>\d{4}|\d{6})$")
FILE_REV_RE = re.compile(
    r"^(?P<part>.+)-rev(?P<letter>[A-Z]+)(?:\.(?P<cl>\d{2}))?(?:\.[A-Za-z0-9]+)?$")
NUMERIC_RE = re.compile(r"^rev\d+")
SKIP_DIRS = {"scan", "scans", "reference", "references", "src", "runs", "scripts", "script"}

TEMPLATE = """# {part} / {rev}

- Job: {job}
- Created: {today}
- Rev: {rev_label}{clerical_note}
- Evidence for the letter: {evidence}
- Source: {source}
- Made with: (tool, e.g. build123d / Fusion)
- What changed from the previous rev:
- Status: (candidate / approved; FEA not run until the geometry is approved)
- Files: {files}

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
    m = LEGACY_JOB_RE.match(job)
    return m.group("name") if m else job


def _skipped(path: Path, job_dir: Path) -> bool:
    rel = path.relative_to(job_dir)
    return any(p.lower() in SKIP_DIRS for p in rel.parts[:-1])


def iter_part_files(job_dir: Path):
    if not job_dir.is_dir():
        return
    for p in job_dir.rglob("*"):
        if not p.is_file() or _skipped(p, job_dir):
            continue
        m = FILE_REV_RE.match(p.name)
        if m and revs.is_valid_letter(m.group("letter")):
            yield p, m


def _has_numeric_rev_dir(job_dir: Path) -> bool:
    if not job_dir.is_dir():
        return False
    return any(p.is_dir() and NUMERIC_RE.match(p.name) for p in job_dir.iterdir())


def find_existing(root: Path, subject: str) -> Path | None:
    """Stable job folder: `<subject>` if present, else the latest `<subject>_<MMDD>`."""
    if not root.is_dir():
        return None
    exact = root / subject
    if exact.is_dir():
        return exact
    legacy = []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        m = LEGACY_JOB_RE.match(p.name)
        if m and m.group("name") == subject:
            legacy.append(p)
    return sorted(legacy, key=lambda p: p.name)[-1] if legacy else None


def next_rev(job_dir: Path, part: str, clerical: bool = False, letter: str | None = None,
             releases: int | None = None) -> str:
    """Next `rev<LETTER>` (or `rev<LETTER>.<NN>`) for this part. Does not look at other parts."""
    lettered = [(m.group("letter"), int(m.group("cl") or 0)) for _p, m in iter_part_files(job_dir) if m.group("part") == part]
    top = max((l for l, _ in lettered), key=revs.letter_to_index, default=None)
    if clerical:
        if letter or releases is not None:
            raise RevError("--clerical takes the current letter; don't combine it with --letter / --releases")
        if top is None:
            raise RevError("a clerical rev needs a released rev<LETTER> for this part (an unreleased drawing keeps its counted letter)")
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
    if top is not None:
        return "rev" + revs.next_letter(top)
    if _has_numeric_rev_dir(job_dir):
        raise RevError("this job has only old numeric rev<N> folders: don't convert them. Count the model's real releases "
                       "and pass --releases N (or --letter X); list the releases as evidence in the data card")
    return "revA"


def prune_plan(job_dir: Path, keep: int = 2) -> list[Path]:
    """Files to delete: for each part, letters older than the `keep` newest, and their clerical files.

    `reference/`, scans, scripts and files with no rev are not included. Directories are not included.
    """
    groups: dict[str, list[tuple[str, int, Path]]] = {}
    for path, m in iter_part_files(job_dir):
        groups.setdefault(m.group("part"), []).append((m.group("letter"), int(m.group("cl") or 0), path))
    drop = []
    for items in groups.values():
        letters = sorted({let for let, cl, _ in items if cl == 0}, key=revs.letter_to_index)
        kept = set(letters[-keep:]) if keep else set()
        for let, _cl, path in items:
            if let not in kept:
                drop.append(path)
    return sorted(drop, key=lambda p: str(p))


def prune_revs(job_dir: Path, apply: bool = False, keep: int = 2) -> list[Path]:
    drop = prune_plan(job_dir, keep=keep)
    if apply:
        for path in drop:
            path.unlink()
    return drop


def create(root: Path, job: str, date: str | None = None, source: str = "", today: _dt.date | None = None,
           clerical: bool = False, letter: str | None = None, releases: int | None = None,
           part: str | None = None) -> Path:
    today = today or _dt.date.today()
    if date and not re.fullmatch(r"\d{4}", date):
        raise SystemExit("rev.py: --date must be MMDD")
    subject = parse_subject(job)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", subject):
        raise RevError(f"bad subject {subject!r}")
    part = part or subject
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", part):
        raise RevError(f"bad part {part!r}")
    existing = find_existing(root, subject)
    if existing is None:
        stamp = date or f"{today:%m%d}"
        existing = root / f"{subject}_{stamp}"
        existing.mkdir(parents=True)
    name = next_rev(existing, part, clerical=clerical, letter=letter, releases=releases)
    card = existing / f"{part}-{name}.md"
    label = name[3:]
    if clerical:
        note = f" (clerical: drawing-only, under rev{label.split('.')[0]}; not listed in REVLOG.md)"
        files = f"drawing {part}-{name}.pdf only - no model file in a clerical rev"
        evidence = f"clerical decimal under rev{label.split('.')[0]}"
    else:
        note = ""
        files = (f"{part}-{name}.step (or Parts\\{part}-{name}.step) and drawing {part}-{name}.pdf. "
                 "AP242 STEP only. A print STL and scripts stay in the parts home.")
        if releases is not None:
            evidence = f"{releases} counted past release(s) (list them here)"
        elif letter is not None:
            evidence = "letter given by hand (list the counted releases here)"
        elif label == "A":
            evidence = "brand-new model (Rev A = Initial)"
        else:
            evidence = "next letter after this part's highest rev"
    with open(card, "x", encoding="utf-8") as f:
        f.write(TEMPLATE.format(part=part, job=existing.name, rev=name, rev_label=label, clerical_note=note,
                                evidence=evidence, today=today.isoformat(), source=source or "(fill in)", files=files))
    return card


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", help="subject, or an existing <subject>_<MMDD>")
    ap.add_argument("--part", help="designed part or assembly (default: the subject). Other parts are left alone")
    ap.add_argument("--date", help="MMDD for a new job folder (default: today). Not a rev")
    ap.add_argument("--source", default="", help="where the model came from (for the data card)")
    ap.add_argument("--clerical", action="store_true", help="drawing-only change: next .NN under this part's current letter")
    ap.add_argument("--letter", help="use this letter (must be newer than this part's existing revs)")
    ap.add_argument("--releases", type=int, help="past releases of this part when the job has only old numeric rev folders")
    ap.add_argument("--prune", action="store_true",
                    help="delete older rev files per part (newest + previous). Never deletes the job folder or reference/")
    a = ap.parse_args(argv)
    try:
        if a.prune:
            if a.clerical or a.letter or a.releases is not None or a.part:
                raise RevError("--prune does not take --part, --clerical, --letter or --releases")
            root = models_dir()
            job_dir = find_existing(root, parse_subject(a.job))
            if job_dir is None:
                raise RevError(f"no job folder for {parse_subject(a.job)!r}")
            drop = prune_revs(job_dir, apply=True)
            names = ", ".join(str(p.relative_to(job_dir)) for p in drop) or "(none)"
            print(f"pruned {job_dir}: dropped {names}")
            return 0
        print(create(models_dir(), a.job, a.date, a.source, clerical=a.clerical, letter=a.letter,
                     releases=a.releases, part=a.part))
    except FileExistsError as e:
        print(f"rev.py: refusing to overwrite {e.filename}", file=sys.stderr)
        return 1
    except RevError as e:
        print(f"rev.py: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
