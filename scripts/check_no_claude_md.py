#!/usr/bin/env python3
"""Fail if git still tracks a CLAUDE guide file. Stdlib only.

A tracked file named CLAUDE.md or CLAUDE.local.md, including .claude/CLAUDE.md,
has to be folded into AGENTS.md and deleted. This script only reports that.
It does not edit the tree.
"""
import subprocess
import sys

FORBIDDEN_BASENAMES = frozenset({"CLAUDE.md", "CLAUDE.local.md"})
# Called out on its own so the .claude path stays covered even if the
# basename set is edited later. Today the basename rule already matches it.
FORBIDDEN_PATHS = frozenset({".claude/CLAUDE.md"})

MESSAGE = (
    "Fold the content into AGENTS.md (keep every rule, drop exact duplicates) "
    "and delete the CLAUDE file in a PR."
)


def normalize(path):
    norm = path.replace("\\", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    return norm


def is_forbidden(path):
    norm = normalize(path)
    if not norm or norm.endswith("/"):
        return False
    base = norm.rsplit("/", 1)[-1]
    return base in FORBIDDEN_BASENAMES or norm in FORBIDDEN_PATHS


def offending(paths):
    return sorted({normalize(p) for p in paths if is_forbidden(p)})


def format_error(paths):
    lines = ["Tracked CLAUDE guide files must not stay in git:"]
    lines.extend(paths)
    lines.append(MESSAGE)
    return "\n".join(lines) + "\n"


def tracked_paths(root):
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
    )
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(err or "git ls-files failed")
    raw = result.stdout.decode("utf-8", errors="surrogateescape")
    return [p for p in raw.split("\0") if p]


def repo_root():
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        err = result.stderr.strip()
        raise RuntimeError(err or "not a git repo")
    return result.stdout.strip()


def check_repo(root):
    bad = offending(tracked_paths(root))
    if not bad:
        return 0, ""
    return 1, format_error(bad)


def main():
    try:
        code, text = check_repo(repo_root())
    except RuntimeError as exc:
        sys.stderr.write(f"check_no_claude_md: {exc}\n")
        return 2
    if code != 0:
        sys.stderr.write(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
