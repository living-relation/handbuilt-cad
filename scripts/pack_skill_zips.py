#!/usr/bin/env python3
"""Build one Claude-importable zip per skill folder that contains SKILL.md.

Writes skills/<name>.zip with a single top folder <name>/SKILL.md (plus other
git-tracked files in that folder). Zips are deterministic: sorted names, fixed
timestamps, ZIP_STORED, Unix file-type bits. Unchanged skills stay byte-identical.

Only directories with SKILL.md are skills; sibling .zip files, README.md, dot
paths and untracked files are ignored. Stale skills/<name>.zip files with no
matching SKILL.md are removed.

Reports Claude Agent Skills frontmatter limits (does not edit skills). A
description over 200 characters prints a GitHub ::warning and never fails.
Hard failures (name/description rules, 1024-char cap) still exit 1 after zips
are written.
"""
from __future__ import annotations

import argparse
import io
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
# Claude: lowercase letters, numbers, and hyphens only (max 64 checked separately).
NAME_RE = re.compile(r"^[a-z0-9-]+$")
XML_TAG_RE = re.compile(r"</?[A-Za-z!?][^>]*>")
RESERVED = ("claude", "anthropic")
DESC_WARN = 200
DESC_MAX = 1024
NAME_MAX = 64
SKIP_NAMES = {"thumbs.db"}
EXCLUDE_FILE = "EXCLUDE.txt"
MARKER_RE = re.compile(r"(?m)^source:\s*['\"]?harness-design-app['\"]?\s*$")


class PackError(Exception):
    """Fatal pack error. pack() prints it and returns 1."""


def load_excluded(skills_root: Path) -> set[str]:
    """Names in skills/EXCLUDE.txt (one per line, # comments): Claude-app-owned skills."""
    f = skills_root / EXCLUDE_FILE
    if not f.is_file():
        return set()
    out = set()
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def is_app_marked(skill_dir: Path) -> bool:
    """True if SKILL.md frontmatter has `source: harness-design-app`."""
    p = skill_dir / "SKILL.md"
    if not p.is_file():
        return False
    text = p.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return False
    rest = text[3:].lstrip("\r\n")
    m = re.search(r"(?m)^---\s*$", rest)
    return bool(m and MARKER_RE.search(rest[: m.start()]))


def iter_skill_dirs(skills_root: Path) -> list[Path]:
    """Directories that contain SKILL.md. Files (including .zip) are ignored."""
    if not skills_root.is_dir():
        return []
    found = []
    for p in sorted(skills_root.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir() and not p.name.startswith(".") and (p / "SKILL.md").is_file():
            found.append(p)
    return found


def _git_ls_files(skill_dir: Path) -> set[str] | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(skill_dir), "ls-files", "-z", "--", "."],
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError:
        return None
    if r.returncode != 0:
        return None
    return {p for p in r.stdout.split("\0") if p}


def _is_skipped(rel: Path) -> bool:
    if rel.name.lower() in SKIP_NAMES:
        return True
    return any(part.startswith(".") or part == "__pycache__" for part in rel.parts)


def skill_files(skill_dir: Path) -> list[Path]:
    tracked = _git_ls_files(skill_dir)
    if tracked is not None:
        if not any(Path(p).as_posix() == "SKILL.md" for p in tracked):
            raise PackError(f"SKILL.md is not git-tracked in {skill_dir}")
        candidates = [skill_dir / p for p in tracked]
    else:
        candidates = [p for p in skill_dir.rglob("*") if p.is_file()]
    files = []
    for p in candidates:
        if not p.is_file():
            continue
        if _is_skipped(p.relative_to(skill_dir)):
            continue
        files.append(p)
    files.sort(key=lambda p: p.relative_to(skill_dir).as_posix())
    return files


def _zip_info(arcname: str, *, directory: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(arcname)
    info.date_time = ZIP_EPOCH
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.compress_type = zipfile.ZIP_STORED
    if directory:
        info.external_attr = ((stat.S_IFDIR | 0o755) << 16) | 0x10
    else:
        info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def build_zip_bytes(skill_dir: Path) -> bytes:
    name = skill_dir.name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr(_zip_info(f"{name}/", directory=True), b"")
        for p in skill_files(skill_dir):
            rel = p.relative_to(skill_dir).as_posix()
            zf.writestr(_zip_info(f"{name}/{rel}"), p.read_bytes())
    return buf.getvalue()


def write_zip_if_changed(path: Path, data: bytes) -> bool:
    if path.is_file() and path.read_bytes() == data:
        return False
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    return True


def _frontmatter_block(text: str) -> tuple[str | None, str | None]:
    if not text.startswith("---"):
        return None, "SKILL.md has no YAML frontmatter"
    rest = text[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    closer = re.search(r"\n---\s*(?:\n|$)", rest)
    if not closer:
        return None, "SKILL.md frontmatter is not closed"
    return rest[: closer.start()], None


def _load_yaml_mapping(block: str) -> tuple[dict | None, str | None]:
    try:
        import yaml
    except ImportError:
        return _strict_yaml_mapping(block)
    try:
        data = yaml.safe_load(block)
    except Exception as e:
        return None, f"frontmatter YAML error: {e}"
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return None, "frontmatter is not a YAML mapping"
    return data, None


def _strict_yaml_mapping(block: str) -> tuple[dict | None, str | None]:
    """Subset parser used when PyYAML is missing. Fails on lines it cannot parse."""
    fields: dict[str, object] = {}
    key = None
    folded: list[str] = []
    style = ""

    def finish():
        nonlocal key, folded, style
        if key is None:
            return None
        if style.startswith(">"):
            parts, cur = [], []
            for line in folded:
                if line.strip() == "":
                    if cur:
                        parts.append(" ".join(cur))
                        cur = []
                else:
                    cur.append(line.strip())
            if cur:
                parts.append(" ".join(cur))
            fields[key] = "\n".join(parts)
        elif style.startswith("|"):
            fields[key] = "\n".join(folded).rstrip("\n")
        else:
            return f"cannot parse frontmatter key {key!r}"
        key, folded, style = None, [], ""
        return None

    for raw in block.splitlines():
        if key and (raw.startswith("  ") or raw.startswith("\t") or raw == ""):
            folded.append(raw[2:] if raw.startswith("  ") else raw[1:] if raw.startswith("\t") else raw)
            continue
        err = finish()
        if err:
            return None, err
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            return None, f"cannot parse frontmatter line: {raw!r}"
        k, v = raw.split(":", 1)
        k, v = k.strip(), v.strip()
        if not k:
            return None, f"cannot parse frontmatter line: {raw!r}"
        if v in (">", ">-", ">+", "|", "|-", "|+"):
            key, style = k, v
            continue
        if v == "":
            return None, f"cannot parse empty or nested value for {k!r}"
        fields[k] = v.strip("'\"")
    err = finish()
    if err:
        return None, err
    return fields, None


def parse_frontmatter(text: str) -> tuple[str | None, str | None, str | None]:
    """Return (name, description, error). Uses yaml.safe_load when PyYAML is installed."""
    block, err = _frontmatter_block(text)
    if err:
        return None, None, err
    fields, err = _load_yaml_mapping(block)
    if err:
        return None, None, err
    name = fields.get("name")
    desc = fields.get("description")
    if name is not None and not isinstance(name, str):
        name = str(name)
    if desc is not None and not isinstance(desc, str):
        desc = str(desc)
    if not name:
        return None, desc, "frontmatter is missing name"
    if not desc or not str(desc).strip():
        return name, None, "frontmatter is missing a nonempty description"
    return name, desc, None


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def check_skill(skill_dir: Path) -> tuple[list[str], list[str]]:
    """Claude Agent Skills limits. Does not edit the skill. Returns (issues, warnings)."""
    issues: list[str] = []
    warnings: list[str] = []
    folder = skill_dir.name
    if len(folder) > NAME_MAX:
        issues.append(f"folder name is {len(folder)} chars (max {NAME_MAX})")
    if not NAME_RE.fullmatch(folder):
        issues.append("folder name must be lowercase letters, numbers and hyphens")
    if any(w in folder.lower() for w in RESERVED):
        issues.append("folder name contains reserved word 'claude' or 'anthropic'")
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    name, desc, err = parse_frontmatter(text)
    if err:
        issues.append(err)
        return issues, warnings
    if name != folder:
        issues.append(f"frontmatter name {name!r} does not match folder {folder!r}")
    if name is not None:
        if len(name) > NAME_MAX:
            issues.append(f"name is {len(name)} chars (max {NAME_MAX})")
        if not NAME_RE.fullmatch(name):
            issues.append("name must be lowercase letters, numbers and hyphens")
        if any(w in name.lower() for w in RESERVED):
            issues.append("name contains reserved word 'claude' or 'anthropic'")
        if XML_TAG_RE.search(name):
            issues.append("name contains an angle-bracket tag")
    if desc is not None:
        n = len(desc)
        if n > DESC_MAX:
            issues.append(f"description is {n} chars (max {DESC_MAX})")
        elif n > DESC_WARN:
            warnings.append(f"description is {n} chars (warn over {DESC_WARN})")
        if XML_TAG_RE.search(desc):
            issues.append("description contains an angle-bracket tag")
    return issues, warnings


def emit_warning(skill_dir: Path, message: str) -> None:
    rel = _rel(skill_dir / "SKILL.md")
    print(f"::warning file={rel},line=1::{message}")
    print(f"  WARN {skill_dir.name}: {message}")


def pack(skills_root: Path, *, check: bool = True, write: bool = True) -> int:
    excluded = load_excluded(skills_root)
    skills = []
    for p in iter_skill_dirs(skills_root):
        if p.name in excluded or is_app_marked(p):
            excluded.add(p.name)
            print(f"skip excluded {p.name} (harness app skill)")
            continue
        skills.append(p)
    wanted = {p.name for p in skills}
    changed = 0
    removed = 0
    if write:
        for z in sorted(skills_root.glob("*.zip")):
            if z.stem not in wanted:
                if z.stem in excluded:
                    continue  # excluded skills: never pack, never touch
                z.unlink()
                print(f"removed stale {z.relative_to(skills_root.parent)}")
                removed += 1
    report: list[tuple[str, list[str], list[str]]] = []
    failed = False
    for skill in skills:
        dest = skills_root / f"{skill.name}.zip"
        try:
            skill_files(skill)
        except PackError as e:
            print(f"FAIL {skill.name}: {e}", file=sys.stderr)
            failed = True
            report.append((skill.name, [str(e)], []))
            continue
        if write:
            if write_zip_if_changed(dest, build_zip_bytes(skill)):
                print(f"wrote {dest.relative_to(skills_root.parent)}")
                changed += 1
            else:
                print(f"unchanged {dest.relative_to(skills_root.parent)}")
        if check:
            issues, warnings = check_skill(skill)
            for w in warnings:
                emit_warning(skill, w)
            if issues:
                failed = True
            report.append((skill.name, issues, warnings))
        else:
            report.append((skill.name, [], []))
    if write:
        print(f"skills: {len(skills)}  zips changed: {changed}  stale removed: {removed}")
    if check:
        print("Claude skill limits:")
        for name, issues, warnings in report:
            if issues:
                print(f"  FAIL {name}")
                for i in issues:
                    print(f"        {i}")
            elif warnings:
                print(f"  warn {name}")
            else:
                print(f"  ok   {name}")
    if failed:
        print("VALIDATION FAILED: skill content was not edited. Fix SKILL.md in a separate change.", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--skills", type=Path, default=SKILLS, help="skills folder (default: <repo>/skills)")
    p.add_argument("--no-check", action="store_true", help="write zips only; skip Claude limit report")
    p.add_argument("--check-only", action="store_true", help="report limits only; do not write zips")
    args = p.parse_args(argv)
    if args.no_check and args.check_only:
        p.error("use only one of --no-check and --check-only")
    return pack(args.skills, check=not args.no_check, write=not args.check_only)


if __name__ == "__main__":
    sys.exit(main())
