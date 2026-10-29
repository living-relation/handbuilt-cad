"""Deterministic Claude skill zips and limit checks (does not edit skills)."""
import os
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

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


def _git(repo: Path, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


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
        infos = {i.filename: i for i in zf.infolist()}
    assert "demo-skill/SKILL.md" in names
    assert "demo-skill/refs/note.md" in names
    assert all(n == "demo-skill/" or n.startswith("demo-skill/") for n in names)
    assert not any(n.endswith(".zip") for n in names)
    assert infos["demo-skill/SKILL.md"].compress_type == zipfile.ZIP_STORED
    mode = infos["demo-skill/SKILL.md"].external_attr >> 16
    assert stat.S_IFMT(mode) == stat.S_IFREG


def test_zips_are_byte_identical_across_rebuilds(tmp_path):
    skills = tmp_path / "skills"
    _write_skill(skills / "demo-skill", "demo-skill", "A demo skill for packing.")
    assert pack.pack(skills, check=True) == 0
    first = (skills / "demo-skill.zip").read_bytes()
    old = skills / "demo-skill" / "SKILL.md"
    old.touch()
    assert pack.pack(skills, check=True) == 0
    assert (skills / "demo-skill.zip").read_bytes() == first
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


def test_env_dotfile_is_excluded_from_zip(tmp_path):
    skills = tmp_path / "skills"
    skill = skills / "demo-skill"
    _write_skill(skill, "demo-skill", "A demo skill for packing.")
    (skill / ".env").write_text("SECRET=1\n")
    (skill / ".hidden").mkdir()
    (skill / ".hidden" / "note.md").write_text("nope\n")
    assert pack.pack(skills, check=True) == 0
    with zipfile.ZipFile(skills / "demo-skill.zip") as zf:
        names = zf.namelist()
    assert "demo-skill/SKILL.md" in names
    assert not any(".env" in n or ".hidden" in n for n in names)


def test_untracked_file_excluded_when_git_repo(tmp_path):
    repo = tmp_path / "r"
    skills = repo / "skills"
    skill = skills / "demo-skill"
    _write_skill(skill, "demo-skill", "A demo skill for packing.")
    (skill / "secret.txt").write_text("untracked\n")
    _git(repo, "init")
    _git(repo, "config", "user.email", "ci@users.noreply.github.com")
    _git(repo, "config", "user.name", "ci")
    _git(repo, "add", "skills/demo-skill/SKILL.md")
    _git(repo, "commit", "-m", "skill")
    assert pack.pack(skills, check=True) == 0
    with zipfile.ZipFile(skills / "demo-skill.zip") as zf:
        names = zf.namelist()
    assert "demo-skill/SKILL.md" in names
    assert "demo-skill/secret.txt" not in names


def test_untracked_skill_md_fails_in_git_repo(tmp_path):
    repo = tmp_path / "r"
    skills = repo / "skills"
    skill = skills / "demo-skill"
    _write_skill(skill, "demo-skill", "A demo skill for packing.")
    _git(repo, "init")
    _git(repo, "config", "user.email", "ci@users.noreply.github.com")
    _git(repo, "config", "user.name", "ci")
    _git(repo, "commit", "--allow-empty", "-m", "init")
    rc = pack.pack(skills, check=True)
    assert rc == 1
    assert not (skills / "demo-skill.zip").exists()


def test_limit_violations_are_reported_without_editing_skill(tmp_path):
    skills = tmp_path / "skills"
    bad = skills / "Bad_Name"
    _write_skill(bad, "Bad_Name", "Has a <tag> and " + ("x" * 2000))
    original = (bad / "SKILL.md").read_text(encoding="utf-8")
    rc = pack.pack(skills, check=True)
    assert rc == 1
    assert (bad / "SKILL.md").read_text(encoding="utf-8") == original
    assert (skills / "Bad_Name.zip").is_file()
    issues, warnings = pack.check_skill(bad)
    joined = " ".join(issues)
    assert "lowercase" in joined
    assert "1024" in joined
    assert "angle-bracket" in joined
    assert warnings == []


def test_reserved_name_and_folder_mismatch(tmp_path):
    skills = tmp_path / "skills"
    folder = skills / "ok-name"
    _write_skill(folder, "claude-helper", "Uses reserved words.")
    issues, _ = pack.check_skill(folder)
    text = " ".join(issues)
    assert "does not match folder" in text
    assert "reserved word" in text


def test_unparseable_frontmatter_fails(tmp_path):
    skills = tmp_path / "skills"
    folder = skills / "demo-skill"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: ok\nthis line is garbage\n---\nbody\n",
        encoding="utf-8",
    )
    issues, _ = pack.check_skill(folder)
    assert any("cannot parse" in i or "YAML" in i for i in issues)


def test_long_multiline_description_warns_and_does_not_fail(tmp_path, capsys):
    skills = tmp_path / "skills"
    folder = skills / "demo-skill"
    folder.mkdir(parents=True)
    para = (
        "Use this skill when packing a long folded description that stays under "
        "the hard 1024 character cap but goes past the 200 character warning so "
        "the packer must print a GitHub annotation and still succeed."
    )
    assert 200 < len(para) < 1024
    (folder / "SKILL.md").write_text(
        "---\n"
        "name: demo-skill\n"
        "description: >-\n"
        f"  {para[:80]}\n"
        f"  {para[80:160]}\n"
        f"  {para[160:]}\n"
        "---\n"
        "body\n",
        encoding="utf-8",
    )
    original = (folder / "SKILL.md").read_text(encoding="utf-8")
    name, desc, err = pack.parse_frontmatter(original)
    assert err is None and name == "demo-skill"
    assert desc is not None and len(desc) > 200
    rc = pack.pack(skills, check=True)
    assert rc == 0
    assert (folder / "SKILL.md").read_text(encoding="utf-8") == original
    out = capsys.readouterr().out
    assert "::warning" in out
    assert "warn over 200" in out
    issues, warnings = pack.check_skill(folder)
    assert issues == []
    assert warnings and "200" in warnings[0]


@pytest.mark.skipif(not os.environ.get("CI"), reason="zips are CI-owned (AGENTS.md rule 3); set CI=1 to run")
def test_committed_skill_zips_match_rebuild():
    skills = list(pack.iter_skill_dirs(SKILLS))
    assert skills, "expected SKILL.md folders under skills/"
    for skill in skills:
        zpath = SKILLS / f"{skill.name}.zip"
        assert zpath.is_file(), f"missing committed zip {zpath.name}"
        assert zpath.read_bytes() == pack.build_zip_bytes(skill)


def test_current_skills_pass_claude_limits():
    failed = []
    for skill in pack.iter_skill_dirs(SKILLS):
        issues, _ = pack.check_skill(skill)
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


def test_workflow_commits_to_pr_branch_never_to_main():
    yml = (ROOT / ".github" / "workflows" / "skill-zips.yml").read_text()
    assert "pull_request" in yml
    assert "!**/*.zip" in yml
    assert "github-actions[bot]" in yml
    assert "[skip ci]" in yml
    assert "workflow_dispatch" in yml
    assert "persist-credentials: false" in yml
    assert "continue-on-error" not in yml
    assert "11bd71901bbe5b1630ceea73d27597364c9af683" in yml
    assert "github.head_ref != github.event.repository.default_branch" in yml
    assert "refusing to push to default branch" in yml
    assert "--force-with-lease" in yml
    assert "gh workflow run" in yml
    assert "verify_only" in yml
    assert "scripts/pack_skill_zips.py" in yml
    assert ".github/workflows/skill-zips.yml" in yml
    assert "guard-staged.sh" in yml
    assert "pack-skill-zips.reqs.txt" in yml
    assert "permissions: {}" in yml
    assert "HEAD:main" not in yml
    assert "push origin main" not in yml
    assert "chore/skill-zips" in yml
    on_pr = yml.split("on-pr:")[1].split("on-pr-fork:")[0]
    assert "pytest" in on_pr
    assert "git diff --cached --exit-code -- 'skills/*.zip'" in on_pr
    assert 'CI: "true"' in on_pr
    on_main = yml.split("on-main:")[1].split("verify:")[0]
    assert on_main.index("git reset --hard") < on_main.index("pack_skill_zips.py --no-check")


def test_stage_skill_zips_uses_git_pathspec():
    sh = (ROOT / "scripts" / "stage-skill-zips.sh").read_text()
    assert "-- 'skills/*.zip'" in sh
    assert "skills/*.zip" not in sh.replace("'skills/*.zip'", "")
    assert "guard-staged.sh" not in sh  # caller runs the guard


def test_pyyaml_is_pinned():
    req = (ROOT / "scripts" / "pack-skill-zips.reqs.txt").read_text()
    assert "pyyaml==6.0.3" in req.lower() or "PyYAML==6.0.3" in req


def test_rule_3_is_reworded_in_place():
    lines = (ROOT / "AGENTS.md").read_text().splitlines()
    rule2 = [l for l in lines if l.startswith("2. ")][0]
    assert "Never use `--no-verify`" in rule2
    assert "never force-push" in rule2
    assert "never push to `main`" in rule2
    assert (
        "Exception: the skill-zips CI bot may force-push (with lease) its own "
        "`chore/skill-zips` branch only."
    ) in rule2
    line = [l for l in lines if l.startswith("3. ")][0]
    assert line.startswith("3. Skill zips")
    assert "rebuilt automatically by CI" in line
    assert "Allow GitHub Actions to create and approve pull requests" in (ROOT / "CONTRIBUTING.md").read_text()


def test_verify_install_does_not_scan_skills_folder():
    text = (ROOT / "scripts" / "verify-install.sh").read_text()
    assert "skills/" not in text and "skills\\" not in text


def test_name_regex_matches_claude_rule():
    assert pack.NAME_RE.fullmatch("a")
    assert pack.NAME_RE.fullmatch("cnc-part-check")
    assert pack.NAME_RE.fullmatch("a--b")  # hyphens only, as Claude states
    assert not pack.NAME_RE.fullmatch("Bad_Name")
    assert not pack.NAME_RE.fullmatch("Has Space")
    assert not pack.NAME_RE.fullmatch("")
