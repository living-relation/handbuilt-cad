#!/usr/bin/env python3
"""Next version folder of a models job, and the keep-two prune. Never edits an existing version.

Layout (Daniel, 2026-11-20): $MODELS_DIR/<job>/rev<LETTER>/ (clerical: rev<LETTER>.<NN>/).
Existing job folder names are kept as they are (e.g. `bracket-revB`, `knuckle-rev5`, `bracket_1017`);
a new job folder is the plain subject. Each version folder holds that version's assembly STEP at
its root, `Parts/` beside it, `drawings/`, `SUMMARY.md` and the drawing `REVLOG.md`.

- Letters A..Z skip I, L, O and Q in every position, then AA, AB ... (drawing/revs.py does the counting).
- Rev A is only for a brand-new model. A model change takes the next letter after the highest rev<LETTER> folder.
- A clerical rev (drawing-only change, no fit/form/function change) adds a decimal under the current
  letter: revD -> revD.01. It holds drawings and SUMMARY.md only, never a model file.
- Old numeric rev<N> folders are never converted. If a job has only those, pass --releases N or --letter X.
- --prune keeps the two newest versions of the job's assembly (letters, then numeric folders if there
  are fewer than two letters) and the clerical decimals of kept letters. Older version folders go, with
  the parts inside them. A folder that holds a 3D scan is never deleted. It only lists what it would
  delete unless --apply is given.

    export MODELS_DIR=~/models
    python tools/rev.py bracket                     # bracket/revA, or the next letter in the existing job folder
    python tools/rev.py bracket --clerical          # drawing-only: revD -> revD.01
    python tools/rev.py knuckle --releases 7        # only old revN folders and 7 counted releases -> revH
    python tools/rev.py bracket --prune [--apply]   # keep the two newest versions

It prints the new folder. Files inside an existing version folder are never edited; if the target exists the tool stops.
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
SUBJECT_REV_RE = re.compile(r"^(?P<subject>.+)-rev(?:[A-Z]+(?:\.\d{2})?|\d+[A-Za-z]*)$")
LETTER_RE = re.compile(r"^rev(?P<letter>[A-Z]+)(?:\.(?P<cl>\d{2}))?$")
NUMERIC_RE = re.compile(r"^rev(?P<num>\d+)(?P<tail>.*)$")
SCAN_SUFFIXES = {".ply", ".e57", ".pts", ".xyz", ".las", ".laz"}

TEMPLATE = """# {job} / {rev}

- Created: {today}
- Rev: {rev_label}{clerical_note}
- Evidence for the letter: {evidence}
- Source: {source}
- Made with: (tool and version, e.g. build123d 0.9 / Fusion; "unconfirmed" if unknown)
- What changed from the previous rev:
- Status: (candidate / approved; FEA not run until the geometry is approved)
- Mass / material / bounding box:
- Files:
  - {files}
- Checks: (valid body, STEP round-trip, fit, CNC, tools/checks/release_structure.py)
- Open issues:

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
    for rx, key in ((SUBJECT_REV_RE, "subject"), (LEGACY_JOB_RE, "name")):
        m = rx.match(job)
        if m:
            return m.group(key)
    return job


def find_existing(root: Path, job: str) -> Path | None:
    """The job folder: `job` itself if it exists, else one whose subject matches (names are never changed)."""
    if not root.is_dir():
        return None
    if (root / job).is_dir():
        return root / job
    subject = parse_subject(job)
    hits = sorted(p for p in root.iterdir() if p.is_dir() and parse_subject(p.name) == subject)
    if len(hits) > 1:
        raise RevError(f"several job folders match {subject!r}: {', '.join(p.name for p in hits)}; pass the folder name")
    return hits[0] if hits else None


def _has_scan(folder: Path) -> bool:
    return any(p.is_file() and p.suffix.lower() in SCAN_SUFFIXES for p in folder.rglob("*"))


def versions(job_dir: Path):
    """(model folders newest last, {letter: [clerical folders]}). Numeric rev<N> folders sort before letters."""
    model, clerical = [], {}
    if job_dir.is_dir():
        for p in job_dir.iterdir():
            if not p.is_dir():
                continue
            m = LETTER_RE.match(p.name)
            if m and revs.is_valid_letter(m.group("letter")):
                if m.group("cl"):
                    clerical.setdefault(m.group("letter"), []).append(p)
                else:
                    model.append(((1, revs.letter_to_index(m.group("letter")), ""), p))
                continue
            n = NUMERIC_RE.match(p.name)
            if n:
                model.append(((0, int(n.group("num")), n.group("tail").lower()), p))
    return [p for _k, p in sorted(model, key=lambda kp: kp[0])], clerical


def prune_plan(job_dir: Path, keep: int = 2):
    """(folder names to delete, folder names kept because they hold a 3D scan)."""
    model, clerical = versions(job_dir)
    kept = model[-keep:] if keep else []
    kept_letters = {LETTER_RE.match(p.name).group("letter") for p in kept if LETTER_RE.match(p.name)}
    old = [p for p in model if p not in kept]
    old += [p for letter, ps in clerical.items() if letter not in kept_letters for p in ps]
    drop = sorted(p.name for p in old if not _has_scan(p))
    scans = sorted(p.name for p in old if _has_scan(p))
    return drop, scans


def prune_revs(job_dir: Path, apply: bool = False, keep: int = 2):
    drop, scans = prune_plan(job_dir, keep=keep)
    if apply:
        for name in drop:
            shutil.rmtree(job_dir / name)
    return drop, scans


def next_rev(job_dir: Path, clerical: bool = False, letter: str | None = None, releases: int | None = None) -> str:
    """Folder name of the next rev in job_dir (see the module docstring for the rules)."""
    model, clerical_dirs = versions(job_dir)
    letters = [LETTER_RE.match(p.name).group("letter") for p in model if LETTER_RE.match(p.name)]
    numeric = len(letters) < len(model)
    top = letters[-1] if letters else None
    if clerical:
        if letter or releases is not None:
            raise RevError("--clerical takes the current letter; don't combine it with --letter / --releases")
        if top is None:
            raise RevError("a clerical rev needs a released rev<LETTER> folder (an unreleased drawing keeps its counted letter)")
        n = max([int(LETTER_RE.match(p.name).group("cl")) for p in clerical_dirs.get(top, [])], default=0) + 1
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


def create(root: Path, job: str, source: str = "", today: _dt.date | None = None,
           clerical: bool = False, letter: str | None = None, releases: int | None = None) -> Path:
    today = today or _dt.date.today()
    existing = find_existing(root, job)
    if existing is None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", job):
        raise RevError(f"bad subject {job!r}")
    job_dir = existing if existing is not None else root / job
    name = next_rev(job_dir, clerical=clerical, letter=letter, releases=releases)
    rev_dir = job_dir / name
    job_dir.mkdir(exist_ok=True)
    rev_dir.mkdir()  # raises FileExistsError: never reuse a folder
    label = name[3:]
    if clerical:
        note = f" (clerical: drawing-only, under rev{label.split('.')[0]}; not listed in REVLOG.md)"
        files = "drawings\\ (PDF) only - no model file in a clerical rev"
        evidence = f"clerical decimal under rev{label.split('.')[0]}"
    else:
        note = ""
        files = ("assembly AP242 STEP at the rev root, Parts\\ (one AP242 STEP per part, subassembly or bought part), "
                 "drawings\\ (assembly package, printed-parts list), REVLOG.md. No .f3d, STL, scripts or scans")
        if releases is not None:
            evidence = f"{releases} counted past release(s) (list them here)"
        elif letter is not None:
            evidence = "letter given by hand (list the counted releases here)"
        elif label == "A":
            evidence = "brand-new model (Rev A = Initial)"
        else:
            evidence = "next letter after the highest existing rev folder"
    with open(rev_dir / "SUMMARY.md", "x", encoding="utf-8") as f:  # 'x' = fail if it exists
        f.write(TEMPLATE.format(job=job_dir.name, rev=name, rev_label=label, clerical_note=note, evidence=evidence,
                                today=today.isoformat(), source=source or "(fill in)", files=files))
    return rev_dir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", help="subject or existing job folder name (kept as it is)")
    ap.add_argument("--source", default="", help="where the files came from (for SUMMARY.md)")
    ap.add_argument("--clerical", action="store_true", help="drawing-only change: next .NN decimal under the current letter")
    ap.add_argument("--letter", help="use this letter (must be newer than every existing rev folder)")
    ap.add_argument("--releases", type=int, help="number of past releases of the model (old numeric jobs); next letter follows")
    ap.add_argument("--prune", action="store_true", help="list version folders beyond the two newest (never a 3D scan)")
    ap.add_argument("--apply", action="store_true", help="with --prune: delete them")
    a = ap.parse_args(argv)
    try:
        if a.prune:
            if a.clerical or a.letter or a.releases is not None:
                raise RevError("--prune does not take --clerical, --letter or --releases")
            job_dir = find_existing(models_dir(), a.job)
            if job_dir is None:
                raise RevError(f"no job folder for {a.job!r}")
            drop, scans = prune_revs(job_dir, apply=a.apply)
            verb = "dropped" if a.apply else "would drop (add --apply)"
            print(f"{job_dir}: {verb} {', '.join(drop) or '(none)'}; kept for scans {', '.join(scans) or '(none)'}")
            return 0
        if a.apply:
            raise RevError("--apply only goes with --prune")
        print(create(models_dir(), a.job, a.source, clerical=a.clerical, letter=a.letter, releases=a.releases))
    except FileExistsError as e:
        print(f"rev.py: refusing to overwrite {e.filename}", file=sys.stderr)
        return 1
    except RevError as e:
        print(f"rev.py: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
