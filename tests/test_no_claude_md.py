"""Tracked CLAUDE.md / CLAUDE.local.md / .claude/CLAUDE.md files fail the check."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_no_claude_md as chk  # noqa: E402

SCRIPT = ROOT / "scripts" / "check_no_claude_md.py"


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / "AGENTS.md").write_text("guide\n", encoding="utf-8")
    _git(repo, "add", "AGENTS.md")
    return repo


def _run(repo):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def test_names_and_dot_claude_path():
    assert chk.is_forbidden("CLAUDE.md")
    assert chk.is_forbidden("notes/CLAUDE.md")
    assert chk.is_forbidden("CLAUDE.local.md")
    assert chk.is_forbidden("pkg/CLAUDE.local.md")
    assert chk.is_forbidden(".claude/CLAUDE.md")
    assert chk.is_forbidden(".claude\\CLAUDE.md")
    assert not chk.is_forbidden("AGENTS.md")
    assert not chk.is_forbidden(".claude/settings.json")
    assert not chk.is_forbidden("docs/FAIRSOLID.md")
    assert not chk.is_forbidden("CLAUDE.md.bak")
    assert not chk.is_forbidden("claude.md")
    assert not chk.is_forbidden("MY_CLAUDE.md")


def test_error_tells_you_to_fold_into_agents():
    text = chk.format_error(["CLAUDE.md", ".claude/CLAUDE.md"])
    assert chk.MESSAGE in text
    assert "keep every rule, drop exact duplicates" in text
    assert "delete the CLAUDE file in a PR" in text
    assert "CLAUDE.md" in text


def test_clean_repo_passes(tmp_path):
    repo = _repo(tmp_path)
    (repo / "docs").mkdir()
    (repo / "docs" / "notes.md").write_text("see CLAUDE.md in history\n", encoding="utf-8")
    (repo / ".claude").mkdir()
    (repo / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
    _git(repo, "add", "docs/notes.md", ".claude/settings.json")
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_untracked_claude_file_passes(tmp_path):
    repo = _repo(tmp_path)
    (repo / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "rel",
    ["CLAUDE.md", "guides/CLAUDE.local.md", ".claude/CLAUDE.md"],
)
def test_tracked_claude_file_fails(tmp_path, rel):
    repo = _repo(tmp_path)
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("a rule that is not in AGENTS.md\n", encoding="utf-8")
    _git(repo, "add", rel)
    result = _run(repo)
    assert result.returncode == 1
    assert chk.MESSAGE in result.stderr
    assert rel in result.stderr


def test_this_repo_tracks_no_claude_guide():
    code, text = chk.check_repo(str(ROOT))
    assert code == 0, text


def test_workflow_runs_the_check_and_is_registered():
    yml = (ROOT / ".github" / "workflows" / "no-claude-md.yml").read_text(encoding="utf-8")
    assert "python3 scripts/check_no_claude_md.py" in yml
    assert "pull_request:" in yml
    auto = (ROOT / "automation.yml").read_text(encoding="utf-8")
    assert "id: no-claude-md" in auto
    assert ".github/workflows/no-claude-md.yml" in auto
    assert "scripts/check_no_claude_md.py" in auto
