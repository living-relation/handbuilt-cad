"""INSTALL.md's four routes, and the removal gate around them.

These checks read files only. They do not install the plugin or run setup.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMMAND_FENCE = re.compile(r"```(bash|powershell)\n(.*?)```", re.DOTALL)
PROMPT_FENCE = re.compile(r"```prompt\n(.*?)```", re.DOTALL)


def _one_line_commands(path: Path):
    text = path.read_text(encoding="utf-8")
    bad = []
    for lang, body in COMMAND_FENCE.findall(text):
        lines = [ln for ln in body.splitlines() if ln.strip()]
        if len(lines) != 1:
            bad.append(f"{path.name} {lang} fence has {len(lines)} commands")
    return bad


def test_command_fences_are_one_line():
    bad = []
    for rel in ("README.md", "INSTALL.md", "docs/wiki/Install.md"):
        bad.extend(_one_line_commands(ROOT / rel))
    assert bad == []


def test_prompt_matches_setup_prompt_file():
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    prompt = (ROOT / "SETUP-PROMPT.txt").read_text(encoding="utf-8")
    fenced = PROMPT_FENCE.findall(install)
    assert len(fenced) == 1
    assert fenced[0].strip("\n") == prompt.strip("\n")
    assert "Do not link skills." in prompt
    assert "Do not upload skill zips." in prompt
    assert "handbuilt-cad-plugins" in prompt
    assert "living-relation/handbuilt-cad" in prompt
    assert "Do not create a CLAUDE.md." in prompt
    assert "living-relation-plugins" not in prompt
    assert "workstation" not in prompt.lower()


def test_four_routes_and_readme_points_at_the_plugin():
    install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for heading in (
        "## 1. Installer or shortcut",
        "## 2. README commands",
        "## 3. Agent prompt",
        "## 4. Manual steps",
    ):
        assert heading in install
    assert "install.cmd" in install
    assert "not Administrator" in readme
    assert "not root" in readme
    assert "[INSTALL.md](INSTALL.md)" in readme
    assert "**handbuilt-cad** plugin" in readme
    for cmd in (
        "claude plugin marketplace add living-relation/handbuilt-cad",
        "claude plugin install handbuilt-cad@handbuilt-cad-plugins",
        "claude plugin update handbuilt-cad@handbuilt-cad-plugins",
        "claude plugin uninstall handbuilt-cad@handbuilt-cad-plugins",
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\setup.ps1",
        "bash setup.sh",
    ):
        assert cmd in install
    for cmd in (
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\setup.ps1",
        "bash setup.sh",
        "claude plugin marketplace add living-relation/handbuilt-cad",
        "claude plugin install handbuilt-cad@handbuilt-cad-plugins",
    ):
        assert cmd in readme
    assert "handbuilt-cad-plugins" in readme
    for banned in ("living-relation-plugins", "workstation"):
        assert banned not in install.lower()
        assert banned not in readme.lower()


def test_own_catalog_and_nothing_claude_removed_is_back():
    import json

    catalog_path = ROOT / ".claude-plugin" / "marketplace.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["name"] == "handbuilt-cad-plugins"
    assert catalog["plugins"] == [{"name": "handbuilt-cad", "source": "./"}]
    assert "version" not in catalog
    assert not (ROOT / "CLAUDE.md").exists()
    assert not (ROOT / "scripts" / "skill-upload-popup.ps1").exists()
    assert not (ROOT / "skills" / "agent-handoff-pack" / "templates.md").exists()
    market = (ROOT / ".cursor-plugin" / "marketplace.json").read_text(encoding="utf-8")
    assert '"source": "."' in market
    assert "living-relation/workstation" not in market
    assert len(json.loads(market)["plugins"]) == 1
    setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
    assert "LINK_SKILLS=0" in setup
    ps1 = (ROOT / "setup.ps1").read_text(encoding="utf-8")
    assert "if ($LinkSkills)" in ps1
    assert "skill-upload-popup" not in ps1


def test_repo_does_not_name_another_project_repo():
    """The check file is the only place those names may appear, as the search terms."""
    import subprocess

    for word in ("workstation", "living-relation-plugins"):
        found = subprocess.run(
            [
                "git", "grep", "-i", "-n", "-I", "--untracked", word, "--",
                ".", ":!tests/test_install_methods.py",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert found.returncode == 1, found.stdout
