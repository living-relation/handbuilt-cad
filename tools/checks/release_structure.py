#!/usr/bin/env python3
"""Check models job folders (Daniel, 2026-11-20).

    .venv/bin/python tools/checks/release_structure.py <job-or-rev-folder> [...]

A job folder holds version folders `rev<LETTER>/` (clerical `rev<LETTER>.<NN>/`, old numeric
`rev<N>/`). Each version folder is checked; a folder with no version folders is checked as one.
A version holds its assembly AP242 STEP at the root, `Parts/` beside it (made parts, subassemblies
and bought maker STEPs), `drawings/`, `SUMMARY.md` and `REVLOG.md`. Scripts, runs, scans and working
notes stay in the parts home (`tools/paths.py`). Exit 1 on any failure.

Automated:
- More than two model versions in a job fails (keep the two newest; `tools/rev.py <job> --prune`).
- Model files are AP242 STEP only. Any other model format, a STEP header that is not AP242, or two
  STEP files with the same name in one version fails.
- A made part STEP is one valid solid. Bought parts listed under "## Bought parts" in SUMMARY.md
  (`- name: Parts/<file>.stp`) must exist, are exempt from the one-solid check.
- An assembly STEP (one with external references) must reference parts that exist. Embedded bodies other
  than named fasteners (SR Fasteners) fail. A STEP without external references is a made part: one solid
  besides named fastener bodies. A part in
  `Parts/` that no assembly references fails.
- A script, source file, run, scan, or working note fails.

Not automated (checklist in skills/publish-to-models): the live Fusion browser, linked-component
opens, and that the one assembly is built from the newest parts.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rev  # noqa: E402

PRODUCT_RE = re.compile(r"PRODUCT\s*\(\s*'([^']*)'", re.I)
PATH_RE = re.compile(r"'([^']+\.(?:step|stp))'", re.I)
BREP = "MANIFOLD_SOLID_BREP"
FASTENER_RE = re.compile(
    r"(?:^|[^A-Za-z0-9])(?:shcs|bhcs|fhcs|screws?|nuts?|washers?|rivets?|helicoil|sr[\s_-]*fastener)(?:[^A-Za-z0-9]|$)",
    re.I)
STEP_SUFFIXES = {".step", ".stp"}
NON_STEP_MODELS = {".fcstd", ".stl", ".iges", ".igs", ".3mf", ".brep", ".sat",
                   ".obj", ".glb", ".jt", ".sldprt", ".sldasm", ".x_t", ".x_b"}
SCRIPT_SUFFIXES = {".py", ".pyw", ".sh", ".ps1", ".bat", ".cmd", ".js", ".ts", ".ipynb"}
SCAN_SUFFIXES = rev.SCAN_SUFFIXES
BLOCK_DIRS = {"src", "runs", "scripts", "script", "scan", "scans"}
ALLOWED_MD = {"readme.md", "agents.md", "summary.md", "revlog.md"}


def is_fastener(name: str) -> bool:
    return bool(FASTENER_RE.search(name or ""))


def blocked_reason(rel: Path) -> str | None:
    """Why this path must not be in the models folder. None means it may stay."""
    for seg in rel.parts[:-1]:
        if seg.lower() in BLOCK_DIRS:
            return f"{rel.as_posix()}: {seg}/ is agent working files; keep it in the parts home (~/cad-parts)"
    name, suf = rel.name, rel.suffix.lower()
    if suf in SCRIPT_SUFFIXES:
        return f"{rel.as_posix()}: source file; keep it in the parts home (~/cad-parts)"
    if suf in SCAN_SUFFIXES:
        return f"{rel.as_posix()}: scan; keep it in the parts home (~/cad-parts), not the models folder"
    if suf in NON_STEP_MODELS:
        return f"{rel.as_posix()}: models folder is AP242 STEP only (plus a Fusion .f3d when needed); export to STEP"
    if suf == ".md" and name.lower() not in ALLOWED_MD and not name.lower().endswith(".revlog.md"):
        return f"{rel.as_posix()}: working note; a version keeps only SUMMARY.md, REVLOG.md and README"
    return None


def data_text(text: str) -> str:
    """The DATA section (the HEADER names the file itself)."""
    return text.split("DATA;", 1)[-1]


def solid_info(path: Path):
    """(solid count, all valid, error). error is set when the file is not a readable STEP."""
    try:
        from build123d import import_step
        solids = list(import_step(str(path)).solids())
    except Exception as e:
        return 0, False, f"not a readable STEP ({e.__class__.__name__})"
    ok = True
    for s in solids:
        v = s.is_valid
        ok = ok and (v() if callable(v) else bool(v))
    return len(solids), ok, None


def schema_failures(path: Path, text: str) -> list[str]:
    if "FILE_SCHEMA" in text and "AP242" not in text.split("DATA;", 1)[0]:
        return [f"{path.name}: STEP schema is not AP242"]
    return []


def bought_files(summary: str, ver: Path) -> tuple[set[Path], list[str]]:
    files, fails, in_sec = set(), [], False
    for line in summary.splitlines():
        if line.startswith("#"):
            in_sec = line.strip().lower() in ("## bought parts", "# bought parts")
            continue
        body = line.strip()
        if not in_sec or not body.startswith("-"):
            continue
        body = body.lstrip("-").strip()
        if not body or body.lower() in ("none", "(none)"):
            continue
        name, _, rel = body.partition(":")
        rel = rel.strip().replace("\\", "/")
        f = ver / rel
        if not rel or not f.is_file() or f.stat().st_size == 0:
            fails.append(f"bought part {name.strip()} has no maker model ({rel or 'no path'})")
        else:
            files.add(f.resolve())
    return files, fails


def assembly_failures(step: Path, text: str, ver: Path) -> tuple[list[str], set[Path]]:
    """Failures for one assembly STEP, and the external files it references."""
    data = data_text(text)
    refs = set()
    fails = []
    for raw in PATH_RE.findall(data):
        target = (step.parent / raw.replace("\\", "/")).resolve()
        if not target.is_file():
            target = (ver / raw.replace("\\", "/")).resolve()
        if target.is_file():
            refs.add(target)
        else:
            fails.append(f"{step.name}: references {raw}, which is missing")
    breps = data.upper().count(BREP + "(")
    fasteners = {n for n in PRODUCT_RE.findall(data) if is_fastener(n)}
    if breps > len(fasteners):
        fails.append(f"{step.name}: embeds {breps - len(fasteners)} non-fastener bodies; each part must be an external "
                     "STEP in Parts/ (SR fastener bodies may stay inside)")
    return fails, refs


def check_version(ver: Path) -> list[str]:
    fails = []
    for p in sorted(ver.rglob("*")):
        if p.is_file():
            reason = blocked_reason(p.relative_to(ver))
            if reason:
                fails.append(reason)
    summary = (ver / "SUMMARY.md").read_text(errors="replace") if (ver / "SUMMARY.md").is_file() else ""
    bought, bfails = bought_files(summary, ver)
    fails += bfails
    steps = sorted(p for p in ver.rglob("*") if p.is_file() and p.suffix.lower() in STEP_SUFFIXES)
    seen: dict[str, Path] = {}
    for p in steps:
        key = p.stem.lower()
        if key in seen:
            fails.append(f"{p.relative_to(ver)}: duplicate of {seen[key].relative_to(ver)}; keep one STEP per item")
        seen.setdefault(key, p)
    referenced: set[Path] = set()
    parts = [p for p in steps if (ver / "Parts") in p.parents]
    for p in steps:
        text = p.read_text(errors="replace")
        fails += schema_failures(p, text)
        data = data_text(text)
        if p.resolve() in bought:
            continue
        if PATH_RE.search(data):
            f, refs = assembly_failures(p, text, ver)
            fails += f
            referenced |= refs
            continue
        n, valid, err = solid_info(p)
        made = n - len({nm for nm in PRODUCT_RE.findall(data) if is_fastener(nm)})
        if err:
            fails.append(f"{p.name}: {err}")
        elif not valid:
            fails.append(f"{p.name}: invalid solid")
        elif made != 1:
            fails.append(f"{p.name}: made part has {made} solids besides fasteners; a part is one solid. "
                         "Several pieces are an assembly with each part an external STEP in Parts/")
    for p in parts:
        if p.resolve() not in referenced:
            fails.append(f"Parts/{p.name}: no assembly references it; link it from the assembly or remove it")
    return fails


def check_release(folder: Path) -> list[str]:
    """Failure messages for a job folder (each version) or one version folder. Empty means pass."""
    folder = Path(folder)
    if not folder.is_dir():
        return [f"{folder} is not a folder"]
    model, clerical = rev.versions(folder)
    vers = model + [p for ps in clerical.values() for p in ps]
    if not vers:
        return check_version(folder)
    fails = []
    if len(model) > 2:
        fails.append(f"{len(model)} model versions; keep the two newest (tools/rev.py {folder.name} --prune)")
    for v in sorted(vers):
        fails += [f"{v.name}/{f}" for f in check_version(v)]
    return fails


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", nargs="+", help="models job folder or version folder")
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
