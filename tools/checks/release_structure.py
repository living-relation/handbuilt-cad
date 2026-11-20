#!/usr/bin/env python3
"""Check a published rev folder against the model-structure rules (Daniel, 2026-11-20).

    .venv/bin/python tools/checks/release_structure.py <rev-folder> [<rev-folder> ...]

Exit 1 if any rev fails. A clerical rev with no STEP file passes.

Automated (STEP and the rev folder):
- A made part STEP must be one valid solid. More than one solid is a fused multi-body part and fails.
  A file may hold extra solids only when those extras are named as fasteners (SR Fasteners bodies).
- A bought part listed under "## Bought parts" in SUMMARY.md must point at a non-empty maker-model file.
- The assembly STEP's component names must match the files in Parts/ (fastener names on either side are ignored).
- A path inside a STEP that names an older rev folder fails.

Not automated here (Fusion is not opened by this repo; checklist in skills/publish-to-models):
the live Fusion browser tree, linked-component opens, and which Fusion version each link uses.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "drawing"))
import revs  # noqa: E402

LETTER_RE = re.compile(r"^rev(?P<letter>[A-Z]+)(?:\.(?P<cl>\d{2}))?$")
PRODUCT_RE = re.compile(r"PRODUCT\s*\(\s*'([^']*)'", re.I)
PATH_RE = re.compile(r"'([^']+\.(?:step|stp))'", re.I)
NAUO = "NEXT_ASSEMBLY_USAGE_OCCURRENCE"
FASTENER_RE = re.compile(
    r"(?:^|[^A-Za-z0-9])(?:shcs|bhcs|fhcs|screws?|nuts?|washers?|rivets?|helicoil|sr[\s_-]*fastener)(?:[^A-Za-z0-9]|$)",
    re.I)
STEP_SUFFIXES = {".step", ".stp"}


def is_fastener(name: str) -> bool:
    return bool(FASTENER_RE.search(name or ""))


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def product_names(text: str) -> list[str]:
    return PRODUCT_RE.findall(text)


def external_paths(text: str) -> list[str]:
    return PATH_RE.findall(text)


def _step_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in STEP_SUFFIXES)


def solid_info(path: Path):
    """(solid count, all valid, error). error is set when the file is not a readable STEP."""
    try:
        from build123d import import_step
        shape = import_step(str(path))
        solids = list(shape.solids())
    except Exception as e:
        return 0, False, f"not a readable STEP ({e.__class__.__name__})"
    if not solids:
        return 0, True, None
    ok = True
    for s in solids:
        v = s.is_valid
        ok = ok and (v() if callable(v) else bool(v))
    return len(solids), ok, None


def part_solid_failures(path: Path) -> list[str]:
    """A made-part file is one solid. Fastener-named extras inside an assembly structure are allowed."""
    n, valid, err = solid_info(path)
    if err:
        return [f"{path.name}: {err}"]
    if not valid:
        return [f"{path.name}: invalid solid"]
    if n == 1:
        return []
    text = path.read_text(errors="replace")
    names = product_names(text)
    nauo = NAUO in text.upper()
    if n == 0 and nauo:
        return []
    if n > 1 and nauo:
        extras = [nm for nm in names if norm(nm) != norm(path.stem)]
        if extras and all(is_fastener(nm) for nm in extras):
            return []
    if n == 0:
        return [f"{path.name}: made part has no solid"]
    return [f"{path.name}: made part has {n} solids; a part is one solid, not a fused multi-body"]


def tree_failures(step: Path, part_files: list[Path], summary: str) -> list[str]:
    text = step.read_text(errors="replace")
    names = product_names(text)
    name_norms = {norm(nm) for nm in names}
    part_stems = {norm(p.stem) for p in part_files if not is_fastener(p.stem)}
    comp = set()
    for nm in names:
        if is_fastener(nm) or norm(nm) == norm(step.stem):
            continue
        comp.add(norm(nm))
    extra = comp - part_stems
    missing = part_stems - comp
    if not missing and len(extra) == 1 and norm(step.stem) not in name_norms:
        extra = set()
    fails = []
    if missing or extra:
        fails.append(
            f"{step.name}: STEP tree does not match Parts/ "
            f"(STEP {sorted(comp) or ['(none)']}, Parts {sorted(part_stems) or ['(none)']}; "
            "SR fastener names are ignored)"
        )
    fast_files = [p.name for p in part_files if is_fastener(p.stem)]
    if fast_files and "separate file" not in summary.lower():
        fails.append(
            "Parts/ has fastener files (" + ", ".join(fast_files) + "); "
            "SUMMARY.md must say the SR fastener bodies are separate files"
        )
    return fails


def stale_failures(step: Path, rev_dir: Path) -> list[str]:
    m = LETTER_RE.match(rev_dir.name)
    if not m or not revs.is_valid_letter(m.group("letter")):
        return [f"{rev_dir.name} is not a rev<LETTER> folder"]
    current = m.group("letter")
    cur_i = revs.letter_to_index(current)
    fails = []
    for raw in external_paths(step.read_text(errors="replace")):
        for hit in re.finditer(r"(?<![A-Za-z0-9])rev([A-Za-z]+)", raw):
            letter = hit.group(1).upper()
            if revs.is_valid_letter(letter) and revs.letter_to_index(letter) < cur_i:
                fails.append(f"{step.name} references {raw}, which is older than rev{current}")
                break
    return fails


def bought_failures(summary: str, rev_dir: Path) -> list[str]:
    fails = []
    in_sec = False
    for line in summary.splitlines():
        if line.startswith("#"):
            in_sec = line.strip().lower() in ("## bought parts", "# bought parts")
            continue
        if not in_sec:
            continue
        body = line.strip()
        if not body.startswith("-"):
            continue
        body = body.lstrip("-").strip()
        if not body or body.lower() in ("none", "(none)"):
            continue
        if ":" not in body:
            fails.append(f"bought part {body!r} has no maker model")
            continue
        name, rel = body.split(":", 1)
        rel = rel.strip().replace("\\", "/")
        f = (rev_dir / rel)
        if not rel or not f.is_file() or f.stat().st_size == 0:
            fails.append(f"bought part {name.strip()} has no maker model ({rel or 'no path'})")
    return fails


def check_release(rev_dir: Path) -> list[str]:
    """Failure messages for one rev folder. Empty means pass."""
    rev_dir = Path(rev_dir)
    if not rev_dir.is_dir():
        return [f"{rev_dir} is not a folder"]
    summary_path = rev_dir / "SUMMARY.md"
    summary = summary_path.read_text(errors="replace") if summary_path.is_file() else ""
    fails = bought_failures(summary, rev_dir)
    root_steps = _step_files(rev_dir)
    parts_dir = rev_dir / "Parts"
    part_files = _step_files(parts_dir)
    if len(root_steps) > 1:
        fails.append("rev root has more than one STEP; the top assembly is one file")
    if not root_steps and part_files:
        fails.append("Parts/ is present but there is no assembly STEP at the rev root")
    if len(root_steps) == 1 and parts_dir.is_dir():
        root = root_steps[0]
        _n, valid, err = solid_info(root)
        if err:
            fails.append(f"{root.name}: {err}")
        elif not valid:
            fails.append(f"{root.name}: invalid solid")
        fails += tree_failures(root, part_files, summary)
        fails += stale_failures(root, rev_dir)
        for p in part_files:
            fails += part_solid_failures(p)
            fails += stale_failures(p, rev_dir)
    elif len(root_steps) == 1:
        fails += part_solid_failures(root_steps[0])
        fails += stale_failures(root_steps[0], rev_dir)
    elif not root_steps and not part_files:
        pass
    return fails


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rev", nargs="+", help="rev folder (rev<LETTER> or rev<LETTER>.<NN>)")
    args = ap.parse_args(argv)
    bad = 0
    for raw in args.rev:
        fails = check_release(Path(raw))
        if fails:
            bad += 1
            print(f"BAD {raw}")
            for f in fails:
                print(f"  - {f}")
        else:
            print(f"OK  {raw}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
