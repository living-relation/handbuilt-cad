"""Deterministic Claude skill zips and limit checks (does not edit skills)."""
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pack_skill_zips as pack  # noqa: E402

SKILLS = ROOT / "skills"
SCRIPT = ROOT / "scripts" / "pack_skill_zips.py"


def _run(args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
    )


def _write_skill(folder: Path, name: str, description: str, body: str = "body\n"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: >-\n  {description}\n---\n{body}",
        encoding="utf-8",
    )


def test_iter_skill_dirs_ignores_zips_readme_and_folders_without_skill_md(tmp_path):
    skills = tmp_path / "skills"
    _write_skill(skills / "demo-skill", "demo-skill", "A demo skill for packing.")
    (skills / "demo-skill.zip").write_bytes(b"PK leftover")
    (skills / "README.md").write_text("not a skill")
    (skills / "notes").mkdir()
    (skills / "notes" / "README.md").write_text("no SKILL.md")
    found = [p.name for p in pack.iter_skill_dirs(skills)]
    assert found == ["demo-skill"]


def test_zip_layout_is_single_top_folder_with_skill_md(tmp_path):
    skills = tmp_path / "skills"
    skill = skills / "demo-skill"
    _write_skill(skill, "demo-skill", "A demo skill for packing.")
    (skill / "refs").mkdir()
    (skill / "refs" / "note.md").write_text("ref\n")
    rc = pack.pack(skills, check=True)
    assert rc == 0
    zpath = skills / "demo-skill.zip"
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
    assert "demo-skill/SKILL.md" in names
    assert "demo-skill/refs/note.md" in names
    assert all(n == "demo-skill/" or n.startswith("demo-skill/") for n in names)
    assert not any(n.endswith(".zip") for n in names)


def test_zips_are_byte_identical_across_rebuilds(tmp_path):
    skills = tmp_path / "skills"
    _write_skill(skills / "demo-skill", "demo-skill", "A demo skill for packing.")
    assert pack.pack(skills, check=True) == 0
    first = (skills / "demo-skill.zip").read_bytes()
    old = skills / "demo-skill" / "SKILL.md"
    old.touch()  # mtime change must not change the zip
    assert pack.pack(skills, check=True) == 0
    assert (skills / "demo-skill.zip").read_bytes() == first
    # second process, same bytes
    r = _run(["--skills", str(skills)])
    assert r.returncode == 0, r.stdout + r.stderr
    assert (skills / "demo-skill.zip").read_bytes() == first


def test_stale_zip_removed_when_skill_folder_gone(tmp_path):
    skills = tmp_path / "skills"
    _write_skill(skills / "keep-me", "keep-me", "A skill that stays.")
    (skills / "gone.zip").write_bytes(b"PK stale")
    (skills / "keep-me.zip").write_bytes(b"PK old")
    assert pack.pack(skills, check=True) == 0
    assert not (skills / "gone.zip").exists()
    assert (skills / "keep-me.zip").exists()
    assert (skills / "keep-me.zip").read_bytes() != b"PK old"


def test_limit_violations_are_reported_without_editing_skill(tmp_path):
    skills = tmp_path / "skills"
    bad = skills / "Bad_Name"
    _write_skill(bad, "Bad_Name", "Has a <tag> and " + ("x" * 2000))
    original = (bad / "SKILL.md").read_text(encoding="utf-8")
    rc = pack.pack(skills, check=True)
    assert rc == 1
    assert (bad / "SKILL.md").read_text(encoding="utf-8") == original
    assert (skills / "Bad_Name.zip").is_file()
    issues = pack.check_skill(bad)
    joined = " ".join(issues)
    assert "lowercase" in joined
    assert "does not match folder" not in joined or "Bad_Name" in joined
    assert "1024" in joined
    assert "angle-bracket" in joined


def test_reserved_name_and_folder_mismatch(tmp_path):
    skills = tmp_path / "skills"
    folder = skills / "ok-name"
    _write_skill(folder, "claude-helper", "Uses reserved words.")
    issues = " ".join(pack.check_skill(folder))
    assert "does not match folder" in issues
    assert "reserved word" in issues


def test_committed_skill_zips_match_rebuild():
    skills = [p for p in pack.iter_skill_dirs(SKILLS)]
    assert skills, "expected SKILL.md folders under skills/"
    for skill in skills:
        zpath = SKILLS / f"{skill.name}.zip"
        assert zpath.is_file(), f"missing committed zip {zpath.name}"
        assert zpath.read_bytes() == pack.build_zip_bytes(skill)


def test_current_skills_pass_claude_limits():
    failed = []
    for skill in pack.iter_skill_dirs(SKILLS):
        issues = pack.check_skill(skill)
        if issues:
            failed.append((skill.name, issues))
    assert failed == []


def test_bash_wrapper_calls_python():
    sh = (ROOT / "scripts" / "pack-skill-zips.sh").read_text()
    assert "pack_skill_zips.py" in sh
    assert "CAD_PY" in sh


def test_ps1_wrapper_calls_python():
    ps1 = (ROOT / "scripts" / "pack-skill-zips.ps1").read_text()
    assert "pack_skill_zips.py" in ps1
    assert "$env:CAD_PY" in ps1


def test_gitignore_unignores_skill_zips():
    gi = (ROOT / ".gitignore").read_text()
    assert "*.zip" in gi
    assert "!/skills/*.zip" in gi or "!skills/*.zip" in gi


def test_workflow_does_not_retrigger_on_zip_commit():
    yml = (ROOT / ".github" / "workflows" / "skill-zips.yml").read_text()
    assert '"skills/**"' in yml or "'skills/**'" in yml
    assert "!**/*.zip" in yml
    assert "github-actions[bot]" in yml
    assert "[skip ci]" in yml
    assert "workflow_dispatch" in yml
    assert "skills/**/*.zip" not in yml.split("paths:")[0]


def test_verify_install_does_not_scan_skills_folder():
    text = (ROOT / "scripts" / "verify-install.sh").read_text()
    assert "skills/" not in text and "skills\\" not in text
