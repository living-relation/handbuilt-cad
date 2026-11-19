"""INSTALL.md's four routes, and the removal gate around them.

These checks read files. They also run install-plugins.sh against a fake browser opener.
They do not sign in to claude.ai or run setup.
"""
import os
import re
import subprocess
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
    assert "Do not copy skills into ~/.claude/skills or ~/.cursor/skills." in prompt
    assert "Do not upload skill zips." in prompt
    assert "handbuilt-cad-plugins" in prompt
    assert "living-relation/handbuilt-cad" in prompt
    assert "Sync automatically off" in prompt
    assert "https://claude.ai/customize/plugins" in prompt
    assert "Do not create a CLAUDE.md." in prompt
    assert "claude plugin marketplace add" not in prompt
    assert "claude plugin install" not in prompt
    assert "living-relation-plugins" not in prompt
    assert "workstation" not in prompt.lower()
    assert "link" not in prompt.lower().replace("st185-link-ecu-config", "")


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
    assert "install-plugins.cmd" in install
    assert "Plugin (Claude Code shell)" not in install
    assert "Claude Code session" not in install
    assert "not Administrator" in readme
    assert "not root" in readme
    assert "[INSTALL.md](INSTALL.md)" in readme
    assert "**handbuilt-cad** plugin" in readme
    for cmd in (
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\setup.ps1",
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\install-plugins.ps1",
        "bash setup.sh",
        "bash install-plugins.sh",
    ):
        assert cmd in install
        assert cmd in readme
    assert "https://claude.ai/customize/plugins" in install
    assert "Sync automatically off" in install
    assert "handbuilt-cad-plugins" in readme
    for banned_cmd in (
        "claude plugin marketplace add",
        "claude plugin install",
        "claude plugin update",
        "claude plugin uninstall",
        "/plugin marketplace add",
        "/plugin install",
        "-LinkSkills",
        "--link-skills",
    ):
        assert banned_cmd not in install
        assert banned_cmd not in readme
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
    assert "LINK_SKILLS" not in setup and "--link-skills" not in setup
    ps1 = (ROOT / "setup.ps1").read_text(encoding="utf-8")
    assert "LinkSkills" not in ps1 and "link-skills.ps1" not in ps1
    assert "skill-upload-popup" not in ps1
    for name in ("install-plugins.sh", "install-plugins.ps1"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "living-relation/handbuilt-cad" in text
        assert "https://claude.ai/customize/plugins" in text
        assert "Sync automatically off" in text
        assert "The handbuilt-cad plugin is present on claude.ai." in text
        assert "not added on claude.ai yet" in text
        assert "claude plugin marketplace add" not in text
        assert "claude plugin install" not in text
        assert "Register-ScheduledTask" not in text
        assert "schtasks" not in text
        assert "link-skills" not in text
        assert "link" not in text.lower().replace("claude.ai", "")
    cmd = (ROOT / "install-plugins.cmd").read_text(encoding="utf-8")
    assert "install-plugins.ps1 %*" in cmd and "pause" in cmd
    assert "-LinkSkills" not in cmd and "schtasks" not in cmd


def test_install_plugins_sh_prints_clicks_and_asks_to_open_the_page(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "open.log"
    opener = bin_dir / "xdg-open"
    opener.write_text("#!/bin/sh\nprintf '%s\\n' \"$1\" > \"$OPEN_LOG\"\n", encoding="utf-8")
    opener.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ, HOME=str(home), PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}", OPEN_LOG=str(log))
    script = ROOT / "install-plugins.sh"
    r = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "Catalog to paste: living-relation/handbuilt-cad" in r.stdout
    assert "Leave Sync automatically off." in r.stdout
    assert "WARN: The handbuilt-cad plugin is not added on claude.ai yet." in r.stdout
    assert "link" not in r.stdout.lower()
    assert log.read_text(encoding="utf-8").strip() == "https://claude.ai/customize/plugins"
    assert not (home / ".claude").exists()
    refused = subprocess.run(["bash", str(script), "extra"], env=env, capture_output=True, text=True)
    assert refused.returncode == 2


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
