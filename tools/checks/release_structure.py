#!/usr/bin/env python3
"""Check a models job folder (Daniel, 2026-11-20).

    .venv/bin/python tools/checks/release_structure.py <job-folder> [<job-folder> ...]

The models folder holds STEP files and their drawings, plus the per-part data card
`<part>-rev<LETTER>.md` and the folder README. Fusion exports to STEP; the .f3d stays
in Fusion's cloud. Scripts, runs, scans and working notes stay in the parts home
(`tools/paths.py`).

Exit 1 on any failure. A clerical card with no STEP passes.

Automated:
- A made part STEP must be one valid solid. Extra solids are allowed only when they are named fasteners.
- A bought part listed under "## Bought parts" must point at a non-empty maker STEP (no rev; usually reference/).
- STEP only, schema AP242 (`write.step.schema` = AP242DIS). Any other model format, or a STEP header that is not AP242, fails. Two STEP files for the same item fail.
- An assembly STEP must reference each non-fastener file in `Parts/` (`DOCUMENT_FILE` / external id). An assembly that embeds those parts fails. SR fastener bodies may stay inside the assembly STEP.
- A STEP that names `<part>-rev<LETTER>` fails when a newer letter of that same part is in the job.
- A script, source file, run, scan, or working note in the tree fails.

Not automated (Fusion is not opened here; checklist in skills/publish-to-models):
the live Fusion browser and linked-component opens.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "drawing"))
import revs  # noqa: E402

PRODUCT_RE = re.compile(r"PRODUCT\s*\(\s*'([^']*)'", re.I)
PATH_RE = re.compile(r"'([^']+\.(?:step|stp))'", re.I)
FILE_REV_RE = re.compile(
    r"^(?P<part>.+)-rev(?P<letter>[A-Z]+)(?:\.(?P<cl>\d{2}))?(?:\.[A-Za-z0-9]+)?$")
CARD_RE = re.compile(r"^.+-rev[A-Z]+(?:\.\d{2})?\.md$", re.I)
NAUO = "NEXT_ASSEMBLY_USAGE_OCCURRENCE"
FASTENER_RE = re.compile(
    r"(?:^|[^A-Za-z0-9])(?:shcs|bhcs|fhcs|screws?|nuts?|washers?|rivets?|helicoil|sr[\s_-]*fastener)(?:[^A-Za-z0-9]|$)",
    re.I)
STEP_SUFFIXES = {".step", ".stp"}
NON_STEP_MODELS = {".f3d", ".fcstd", ".stl", ".iges", ".igs", ".3mf", ".brep", ".sat",
                   ".obj", ".glb", ".jt", ".sldprt", ".sldasm", ".x_t", ".x_b"}
SCRIPT_SUFFIXES = {".py", ".pyw", ".sh", ".ps1", ".bat", ".cmd", ".js", ".ts", ".ipynb"}
SCAN_SUFFIXES = {".ply", ".e57", ".pts", ".xyz", ".las", ".laz"}
BLOCK_DIRS = {"src", "runs", "scripts", "script", "scan", "scans"}
ALLOWED_MD = {"readme.md", "agents.md"}


def is_fastener(name: str) -> bool:
    return bool(FASTENER_RE.search(name or ""))


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def bare_name(stem: str) -> str:
    """`leg-revC` -> `leg`. A name with no rev is unchanged."""
    m = FILE_REV_RE.match(stem)
    return m.group("part") if m else stem


def _skipped_dir(rel: Path) -> bool:
    return any(p.lower() in BLOCK_DIRS or p.lower() in {"reference", "references"} for p in rel.parts[:-1])


def blocked_reason(rel: Path) -> str | None:
    """Why this path must not be published into the models folder. None means it may stay."""
    for seg in rel.parts[:-1]:
        if seg.lower() in BLOCK_DIRS:
            return f"{rel.as_posix()}: {seg}/ is agent working files; keep it in the parts home (~/cad-parts)"
    name = rel.name
    suf = rel.suffix.lower()
    if suf in SCRIPT_SUFFIXES:
        return f"{name}: source file; keep it in the parts home (~/cad-parts)"
    if suf in SCAN_SUFFIXES:
        return f"{name}: scan; keep it in the parts home (~/cad-parts), not the models folder"
    if suf == ".md" and name.lower() not in ALLOWED_MD and not CARD_RE.match(name) and not name.upper().endswith("REVLOG.MD"):
        return f"{name}: working note; the models folder keeps only the per-part data card, rev log, and README"
    return None


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
    part_stems = {norm(bare_name(p.stem)) for p in part_files
                  if not is_fastener(p.stem) and not is_fastener(bare_name(p.stem))}
    comp = set()
    for nm in names:
        if is_fastener(nm) or norm(nm) == norm(bare_name(step.stem)):
            continue
        comp.add(norm(nm))
    extra = comp - part_stems
    missing = part_stems - comp
    if not missing and len(extra) == 1 and norm(bare_name(step.stem)) not in name_norms and norm(step.stem) not in name_norms:
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
            "the data card must say the SR fastener bodies are separate files"
        )
    return fails


def newest_letters(job: Path) -> dict[str, str]:
    """Highest model letter of each designed part (clerical decimals do not count)."""
    best: dict[str, str] = {}
    if not job.is_dir():
        return best
    for p in job.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(job)
        if _skipped_dir(rel):
            continue
        m = FILE_REV_RE.match(p.name)
        if not m or m.group("cl") or not revs.is_valid_letter(m.group("letter")):
            continue
        part, letter = m.group("part"), m.group("letter")
        if part not in best or revs.letter_to_index(letter) > revs.letter_to_index(best[part]):
            best[part] = letter
    return best


def stale_failures(step: Path, job: Path) -> list[str]:
    """Fail when a STEP names a rev of a part that is older than that part's newest file."""
    best = newest_letters(job)
    fails = []
    for raw in external_paths(step.read_text(errors="replace")):
        m = FILE_REV_RE.match(Path(raw.replace("\\", "/")).name)
        if not m or not revs.is_valid_letter(m.group("letter")):
            continue
        part, letter = m.group("part"), m.group("letter")
        newest = best.get(part)
        if newest and revs.letter_to_index(letter) < revs.letter_to_index(newest):
            fails.append(f"{step.name} references {raw}, but {part} newest is rev{newest}")
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


def _md_text(job: Path) -> str:
    chunks = []
    for p in sorted(job.rglob("*.md")):
        rel = p.relative_to(job)
        if _skipped_dir(rel):
            continue
        if p.name.lower() in ALLOWED_MD or CARD_RE.match(p.name):
            chunks.append(p.read_text(errors="replace"))
    return "\n".join(chunks)


def _model_key(path: Path):
    """One identity per part rev. Two `leg-revC.step` files are the same item."""
    m = FILE_REV_RE.match(path.name)
    if m and revs.is_valid_letter(m.group("letter")):
        return (m.group("part").lower(), m.group("letter").upper(), m.group("cl") or "")
    return (path.stem.lower(), "", "")


def schema_failures(path: Path) -> list[str]:
    """The HEADER schema must be AP242. AP214 and AP203 fail. Non-STEP bytes are ignored."""
    text = path.read_text(errors="replace")
    if "FILE_SCHEMA" not in text:
        return []
    head = text.split("DATA;", 1)[0]
    if "AP242" not in head:
        return [f"{path.name}: STEP schema is not AP242"]
    return []


def external_ref_failures(job: Path) -> list[str]:
    """Assembly STEP must point at each non-fastener Parts/ STEP. Embedded parts fail."""
    parts_dir = job / "Parts"
    if not parts_dir.is_dir():
        return []
    needed = []
    for p in sorted(parts_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() not in STEP_SUFFIXES:
            continue
        if is_fastener(p.stem) or is_fastener(bare_name(p.stem)):
            continue
        needed.append(p.name)
    if not needed:
        return []
    roots = [p for p in job.iterdir() if p.is_file() and p.suffix.lower() in STEP_SUFFIXES]
    if not roots:
        return ["Parts/ has part STEPs but there is no assembly STEP at the job root"]
    fails = []
    for root in roots:
        text = root.read_text(errors="replace")
        missing = [name for name in needed if name not in text and f"Parts/{name}" not in text and f"Parts\\{name}" not in text]
        if missing:
            fails.append(
                f"{root.name}: does not reference external STEP {', '.join(missing)} in Parts/; "
                "embedded parts are not the release format (SR fastener bodies may stay in the assembly)"
            )
    return fails


def model_file_failures(job: Path) -> list[str]:
    """STEP only, one file per item. .f3d and other model formats fail. Drawings are not models."""
    groups: dict[tuple, list[Path]] = {}
    fails = []
    for p in job.rglob("*"):
        if not p.is_file():
            continue
        suf = p.suffix.lower()
        rel = p.relative_to(job).as_posix()
        if suf in NON_STEP_MODELS:
            fails.append(f"{rel}: models folder is STEP only; export to STEP (Fusion keeps .f3d in its cloud)")
        elif suf in STEP_SUFFIXES:
            groups.setdefault(_model_key(p), []).append(p)
    for key, files in groups.items():
        if len(files) < 2:
            continue
        rels = ", ".join(sorted(str(f.relative_to(job)) for f in files))
        label = f"{key[0]} rev{key[1]}" if key[1] else key[0]
        fails.append(f"{label}: duplicate STEP files ({rels}); keep one")
    return fails


def check_release(job: Path) -> list[str]:
    """Failure messages for one models job folder. Empty means pass."""
    job = Path(job)
    if not job.is_dir():
        return [f"{job} is not a folder"]
    fails = []
    for p in job.rglob("*"):
        if p.is_file():
            reason = blocked_reason(p.relative_to(job))
            if reason:
                fails.append(reason)
    summary = _md_text(job)
    fails += bought_failures(summary, job)
    fails += model_file_failures(job)
    fails += external_ref_failures(job)
    all_steps = [p for p in job.rglob("*") if p.is_file() and p.suffix.lower() in STEP_SUFFIXES]
    for p in all_steps:
        fails += schema_failures(p)
    steps = [p for p in all_steps if not _skipped_dir(p.relative_to(job))]
    parts_dir = job / "Parts"
    part_files = [p for p in steps if parts_dir in p.parents] if parts_dir.is_dir() else []
    root_steps = [p for p in steps if p.parent == job]
    root_models = [p for p in job.iterdir() if p.is_file() and p.suffix.lower() in STEP_SUFFIXES]
    for p in part_files:
        fails += part_solid_failures(p)
        fails += stale_failures(p, job)
    for p in root_steps:
        n, valid, err = solid_info(p)
        if err:
            fails.append(f"{p.name}: {err}")
            continue
        if not valid:
            fails.append(f"{p.name}: invalid solid")
        text = p.read_text(errors="replace")
        is_assy = parts_dir.is_dir() and (NAUO in text.upper() or "DOCUMENT_FILE" in text or n != 1)
        if not is_assy:
            fails += part_solid_failures(p)
        fails += stale_failures(p, job)
    if not root_models and part_files:
        fails.append("Parts/ is present but there is no assembly model at the job root")
    return fails


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", nargs="+", help="models job folder")
    args = ap.parse_args(argv)
    bad = 0
    for raw in args.job:
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
