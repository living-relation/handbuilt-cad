"""guard-staged.sh: skill zips next to SKILL.md are allowed; other archives are not."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "guard-staged.sh"


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _repo(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "ci@users.noreply.github.com")
    _git(repo, "config", "user.name", "ci")
    return repo


def _guard(repo):
    return subprocess.run(["sh", str(GUARD)], cwd=repo, capture_output=True, text=True)


def test_guard_allows_skill_zip_when_skill_md_exists(tmp_path):
    repo = _repo(tmp_path)
    (repo / "skills" / "demo-skill").mkdir(parents=True)
    (repo / "skills" / "demo-skill" / "SKILL.md").write_text("---\nname: demo-skill\n---\n")
    (repo / "skills" / "demo-skill.zip").write_bytes(b"PK\x03\x04" + b"\x00" * 32)
    _git(repo, "add", "-f", "skills/demo-skill/SKILL.md", "skills/demo-skill.zip")
    r = _guard(repo)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "BLOCK" not in r.stdout


def test_guard_blocks_zip_without_matching_skill(tmp_path):
    repo = _repo(tmp_path)
    (repo / "skills").mkdir()
    (repo / "skills" / "orphan.zip").write_bytes(b"PK\x03\x04" + b"\x00" * 32)
    _git(repo, "add", "-f", "skills/orphan.zip")
    r = _guard(repo)
    assert r.returncode == 1
    assert "orphan.zip" in r.stdout


def test_guard_still_blocks_other_archives(tmp_path):
    repo = _repo(tmp_path)
    (repo / "handoff.zip").write_bytes(b"PK\x03\x04" + b"\x00" * 32)
    _git(repo, "add", "-f", "handoff.zip")
    r = _guard(repo)
    assert r.returncode == 1
    assert "handoff.zip" in r.stdout
