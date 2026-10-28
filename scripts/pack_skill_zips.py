#!/usr/bin/env python3
"""Build one Claude-importable zip per skill folder that contains SKILL.md.

Writes skills/<name>.zip with a single top folder <name>/SKILL.md (plus any
other files in that folder). Zips are deterministic: sorted names, fixed
timestamps, Unix attrs. Unchanged skills produce byte-identical zips.

Only directories with SKILL.md are skills; sibling .zip files and README.md
are ignored. Stale skills/<name>.zip files with no matching SKILL.md are
removed.

Also reports Claude Agent Skills frontmatter limits (does not edit skills):
name = lowercase letters, numbers, hyphens, max 64, no 'claude'/'anthropic',
no XML tags, must match the folder name; description = nonempty, max 1024,
no XML tags. Default exit is 1 when any check fails; zips are still written.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
XML_TAG_RE = re.compile(r"</?[A-Za-z!?][^>]*>")
RESERVED = ("claude", "anthropic")
SKIP_NAMES = {".ds_store", "thumbs.db"}
SKIP_DIR_PARTS = {"__pycache__", ".git"}


def iter_skill_dirs(skills_root: Path) -> list[Path]:
    """Directories that contain SKILL.md. Files (including .zip) are ignored."""
    if not skills_root.is_dir():
        return []
    found = []
    for p in sorted(skills_root.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir() and not p.name.startswith(".") and (p / "SKILL.md").is_file():
            found.append(p)
    return found


def skill_files(skill_dir: Path) -> list[Path]:
    files = []
    for p in skill_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.name.lower() in SKIP_NAMES:
            continue
        if any(part in SKIP_DIR_PARTS or part.startswith(".") for part in p.relative_to(skill_dir).parts[:-1]):
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
    if directory:
        info.compress_type = zipfile.ZIP_STORED
        info.external_attr = (0o755 << 16) | 0x10
    else:
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
    return info


def build_zip_bytes(skill_dir: Path) -> bytes:
    name = skill_dir.name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
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


def parse_frontmatter(text: str) -> tuple[str | None, str | None, str | None]:
    """Return (name, description, error). Minimal YAML for name + description."""
    if not text.startswith("---"):
        return None, None, "SKILL.md has no YAML frontmatter"
    rest = text[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    closer = re.search(r"\n---\s*(?:\n|$)", rest)
    if not closer:
        return None, None, "SKILL.md frontmatter is not closed"
    block = rest[: closer.start()]
    fields: dict[str, str] = {}
    key = None
    folded: list[str] = []
    style = ""

    def finish():
        nonlocal key, folded, style
        if key is None:
            return
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
        key, folded, style = None, [], ""

    for raw in block.splitlines():
        if key and (raw.startswith("  ") or raw.startswith("\t") or raw == ""):
            folded.append(raw[2:] if raw.startswith("  ") else raw[1:] if raw.startswith("\t") else raw)
            continue
        finish()
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        k, v = raw.split(":", 1)
        k, v = k.strip(), v.strip()
        if v in (">", ">-", ">+", "|", "|-", "|+"):
            key, style = k, v
            continue
        fields[k] = v.strip("'\"")
    finish()
    if "name" not in fields:
        return None, fields.get("description"), "frontmatter is missing name"
    if "description" not in fields or not str(fields["description"]).strip():
        return fields.get("name"), None, "frontmatter is missing a nonempty description"
    return fields["name"], fields["description"], None


def check_skill(skill_dir: Path) -> list[str]:
    """Claude Agent Skills limits. Does not edit the skill."""
    issues = []
    folder = skill_dir.name
    if len(folder) > 64:
        issues.append(f"folder name is {len(folder)} chars (max 64)")
    if not NAME_RE.fullmatch(folder):
        issues.append("folder name must be lowercase letters, numbers and hyphens")
    if any(w in folder.lower() for w in RESERVED):
        issues.append("folder name contains reserved word 'claude' or 'anthropic'")
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    name, desc, err = parse_frontmatter(text)
    if err:
        issues.append(err)
        return issues
    if name != folder:
        issues.append(f"frontmatter name {name!r} does not match folder {folder!r}")
    if name is not None:
        if len(name) > 64:
            issues.append(f"name is {len(name)} chars (max 64)")
        if not NAME_RE.fullmatch(name):
            issues.append("name must be lowercase letters, numbers and hyphens")
        if any(w in name.lower() for w in RESERVED):
            issues.append("name contains reserved word 'claude' or 'anthropic'")
        if XML_TAG_RE.search(name):
            issues.append("name contains an angle-bracket tag")
    if desc is not None:
        if len(desc) > 1024:
            issues.append(f"description is {len(desc)} chars (max 1024)")
        if XML_TAG_RE.search(desc):
            issues.append("description contains an angle-bracket tag")
    return issues


def pack(skills_root: Path, *, check: bool = True) -> int:
    skills = iter_skill_dirs(skills_root)
    wanted = {p.name for p in skills}
    changed = 0
    removed = 0
    for z in sorted(skills_root.glob("*.zip")):
        if z.stem not in wanted:
            z.unlink()
            print(f"removed stale {z.relative_to(skills_root.parent)}")
            removed += 1
    report = []
    failed = False
    for skill in skills:
        dest = skills_root / f"{skill.name}.zip"
        if write_zip_if_changed(dest, build_zip_bytes(skill)):
            print(f"wrote {dest.relative_to(skills_root.parent)}")
            changed += 1
        else:
            print(f"unchanged {dest.relative_to(skills_root.parent)}")
        issues = check_skill(skill) if check else []
        if issues:
            failed = True
            report.append((skill.name, issues))
        else:
            report.append((skill.name, []))
    print(f"skills: {len(skills)}  zips changed: {changed}  stale removed: {removed}")
    print("Claude skill limits:")
    for name, issues in report:
        if issues:
            print(f"  FAIL {name}")
            for i in issues:
                print(f"        {i}")
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
    args = p.parse_args(argv)
    return pack(args.skills, check=not args.no_check)


if __name__ == "__main__":
    sys.exit(main())
