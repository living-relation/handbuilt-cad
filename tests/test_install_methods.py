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
    assert "Turn Sync automatically on" in prompt
    assert "Sync automatically off" not in prompt
    assert "Updates arrive automatically after merges to main." in prompt
    assert "Check for updates in the catalog forces it sooner." in prompt
    assert "still updates by re-running the install-plugins script" in prompt
    assert "fully quit and reopen Cursor after the copy." in prompt
    assert "Developer: Reload Window" not in prompt
    assert "reload the Cursor window" not in prompt.lower()
    assert "copies .cursor-plugin and skills to ~/.cursor/plugins/local/handbuilt-cad and replaces the old copy" in prompt
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
    assert "Adding the repo alone does not install it." in readme
    assert "Adding the repo alone does not install it." in install
    for cmd in (
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\setup.ps1",
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\install-plugins.ps1",
        "bash setup.sh",
        "bash install-plugins.sh",
    ):
        assert cmd in install
    for cmd in (
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\setup.ps1",
        "powershell -NoProfile -ExecutionPolicy Bypass -File .\\install-plugins.ps1",
        "bash setup.sh",
    ):
        assert cmd in readme
    assert "https://claude.ai/customize/plugins" in install
    assert "Turn Sync automatically on" in install
    assert "Sync automatically off" not in install
    assert "where the Sync automatically switch sits is unverified" in (ROOT / "BACKLOG.md").read_text(encoding="utf-8")
    assert "Turn Sync automatically on" in (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "Turn Sync automatically on" in (ROOT / "skills" / "README.md").read_text(encoding="utf-8")
    assert "still updates by re-running" in (ROOT / "skills" / "README.md").read_text(encoding="utf-8")
    assert "handbuilt-cad-plugins" in install
    copy_line = "copies .cursor-plugin and skills to ~/.cursor/plugins/local/handbuilt-cad and replaces the old copy"
    assert copy_line in install.replace("`", "")
    assert copy_line in readme.replace("`", "")
    assert "Fully quit and reopen Cursor after the copy." in install
    assert "Fully quit and reopen Cursor after the copy." in readme
    assert "Developer: Reload Window" not in install
    assert "Developer: Reload Window" not in readme
    assert "cd <projects>\\active\\handbuilt-cad" in install
    assert "cd ~/projects/handbuilt-cad" in install
    assert "cd <projects>\\active\\handbuilt-cad" in readme
    assert "cd ~/projects/handbuilt-cad" in readme
    # The README may show only the per-repo Claude Code install (owner, 2026-11-27).
    project_install = (
        "claude plugin marketplace add living-relation/handbuilt-cad --scope project",
        "claude plugin install handbuilt-cad@handbuilt-cad-plugins --scope project",
    )
    readme_no_project_install = readme
    for line in project_install:
        assert line in readme
        readme_no_project_install = readme_no_project_install.replace(line, "")
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
        assert banned_cmd not in readme_no_project_install
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
        assert "Turn Sync automatically on" in text
        assert "Sync automatically off" not in text
        assert "Updates arrive automatically after merges to main." in text
        assert "still updates by re-running this script" in text
        assert "where that switch sits" in text.lower()
        assert "The handbuilt-cad plugin is present on claude.ai." in text
        assert "handbuilt-cad@handbuilt-cad-plugins" in text
        assert "WARN: handbuilt-cad plugin not added on claude.ai yet: add catalog living-relation/handbuilt-cad and turn on handbuilt-cad." in text
        assert "copies .cursor-plugin and skills to ~/.cursor/plugins/local/handbuilt-cad and replaces the old copy" in text
        assert "Fully quit and reopen Cursor." in text
        assert "Developer: Reload Window" not in text
        assert "Reload the Cursor window." not in text
        assert ".cursor/plugins/local/handbuilt-cad" in text
        assert "claude plugin marketplace add" not in text
        assert "claude plugin install" not in text
        assert "Register-ScheduledTask" not in text
        assert "schtasks" not in text
        assert "link-skills" not in text
        assert "link" not in text.lower().replace("claude.ai", "")
    cmd = (ROOT / "install-plugins.cmd").read_text(encoding="utf-8")
    assert "install-plugins.ps1 %*" in cmd and "pause" in cmd
    assert "-LinkSkills" not in cmd and "schtasks" not in cmd


def test_install_plugins_sh_copies_without_opening_a_browser(tmp_path):
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
    assert "Turn Sync automatically on." in r.stdout
    assert "Sync automatically off" not in r.stdout
    assert "WARN: handbuilt-cad plugin not added on claude.ai yet: add catalog living-relation/handbuilt-cad and turn on handbuilt-cad." in r.stdout
    dest = home / ".cursor" / "plugins" / "local" / "handbuilt-cad"
    assert (dest / ".cursor-plugin" / "plugin.json").is_file()
    assert (dest / "skills" / "cad-drawing" / "SKILL.md").is_file()
    assert not (dest / "README.md").exists()
    assert not (dest / ".git").exists()
    assert not (home / ".cursor" / "skills").exists()
    assert "Copied handbuilt-cad to" in r.stdout
    assert "Fully quit and reopen Cursor." in r.stdout
    assert "Developer: Reload Window" not in r.stdout
    assert "Reload the Cursor window." not in r.stdout
    assert "Nothing was scheduled." in r.stdout
    assert "link" not in r.stdout.lower()
    assert "This script does not open a browser." in r.stdout
    assert "Opening" not in r.stdout
    assert not log.exists()
    assert "xdg-open" not in (ROOT / "install-plugins.sh").read_text(encoding="utf-8")
    assert "Start-Process" not in (ROOT / "install-plugins.ps1").read_text(encoding="utf-8")
    assert not (home / ".claude").exists()
    refused = subprocess.run(["bash", str(script), "extra"], env=env, capture_output=True, text=True)
    assert refused.returncode == 2


def test_install_plugins_sh_replaces_the_old_copy(tmp_path):
    home = tmp_path / "home"
    dest = home / ".cursor" / "plugins" / "local" / "handbuilt-cad"
    stale = dest / "stale.txt"
    stale.parent.mkdir(parents=True)
    stale.write_text("old", encoding="utf-8")
    (dest / "skills" / "gone").mkdir(parents=True)
    (dest / "skills" / "gone" / "SKILL.md").write_text("gone", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    opener = bin_dir / "xdg-open"
    opener.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    opener.chmod(0o755)
    env = dict(os.environ, HOME=str(home), PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    r = subprocess.run(["bash", str(ROOT / "install-plugins.sh")], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    assert not stale.exists()
    assert not (dest / "skills" / "gone").exists()
    copied = (dest / "skills" / "cad-drawing" / "SKILL.md").read_text(encoding="utf-8")
    assert copied == (ROOT / "skills" / "cad-drawing" / "SKILL.md").read_text(encoding="utf-8")
    (dest / "skills" / "cad-drawing" / "SKILL.md").write_text("STALE", encoding="utf-8")
    r2 = subprocess.run(["bash", str(ROOT / "install-plugins.sh")], env=env, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr + r2.stdout
    assert (dest / "skills" / "cad-drawing" / "SKILL.md").read_text(encoding="utf-8") == copied


def test_install_plugins_sh_what_if_copies_nothing(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    log = tmp_path / "open.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    opener = bin_dir / "xdg-open"
    opener.write_text("#!/bin/sh\nprintf '%s\\n' \"$1\" > \"$OPEN_LOG\"\n", encoding="utf-8")
    opener.chmod(0o755)
    env = dict(os.environ, HOME=str(home), PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}", OPEN_LOG=str(log))
    r = subprocess.run(["bash", str(ROOT / "install-plugins.sh"), "--what-if"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "WhatIf: browser was not opened. Nothing was copied. Nothing was scheduled." in r.stdout
    assert "WARN: handbuilt-cad plugin not added on claude.ai yet:" in r.stdout
    assert not (home / ".cursor").exists()
    assert not log.exists()


def test_install_plugins_sh_user_home_skips_the_browser_and_reads_the_plugin_key(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text(
        '{"enabledPlugins": {"handbuilt-cad@handbuilt-cad-plugins": true}}',
        encoding="utf-8",
    )
    other = tmp_path / "other"
    other.mkdir()
    log = tmp_path / "open.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    opener = bin_dir / "xdg-open"
    opener.write_text("#!/bin/sh\nprintf '%s\\n' \"$1\" > \"$OPEN_LOG\"\n", encoding="utf-8")
    opener.chmod(0o755)
    env = dict(os.environ, HOME=str(other), PATH=f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}", OPEN_LOG=str(log))
    r = subprocess.run(
        ["bash", str(ROOT / "install-plugins.sh"), "--user-home", str(home)],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "The handbuilt-cad plugin is present on claude.ai." in r.stdout
    assert "browser was not opened (test home). Nothing was scheduled." in r.stdout
    assert (home / ".cursor" / "plugins" / "local" / "handbuilt-cad" / ".cursor-plugin" / "plugin.json").is_file()
    assert not (other / ".cursor").exists()
    assert not log.exists()
    (home / ".claude" / "settings.json").write_text(
        '{"enabledPlugins": {"handbuilt-cad@handbuilt-cad-plugins": false}}',
        encoding="utf-8",
    )
    off = subprocess.run(
        ["bash", str(ROOT / "install-plugins.sh"), "--user-home", str(home)],
        env=env, capture_output=True, text=True,
    )
    assert off.returncode == 0, off.stderr + off.stdout
    assert "WARN: handbuilt-cad plugin not added on claude.ai yet:" in off.stdout
    assert "The handbuilt-cad plugin is present on claude.ai." not in off.stdout


def test_install_plugins_sh_refuses_to_copy_into_its_own_folder(tmp_path):
    src = tmp_path / "src"
    (src / ".cursor-plugin").mkdir(parents=True)
    (src / "skills").mkdir()
    script = src / "install-plugins.sh"
    script.write_text((ROOT / "install-plugins.sh").read_text(encoding="utf-8"), encoding="utf-8")
    script.chmod(0o755)
    marker = src / "skills" / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    r = subprocess.run(
        ["bash", str(script), "--user-home", str(src)],
        capture_output=True, text=True,
    )
    assert "Refusing to copy the plugin into its own folder." in r.stdout
    assert r.returncode == 1
    assert marker.read_text(encoding="utf-8") == "keep"
    assert not (src / ".cursor" / "plugins").exists()


def test_ps1_copy_replaces_cursor_plugin_and_checks_the_same_key():
    ps1 = (ROOT / "install-plugins.ps1").read_text(encoding="utf-8")
    assert "handbuilt-cad@handbuilt-cad-plugins" in ps1
    assert "Remove-Item -LiteralPath $fullDest -Recurse -Force" in ps1
    assert ps1.index("Remove-Item -LiteralPath $fullDest") < ps1.index("Copy-Item -LiteralPath $from")
    assert "@('.cursor-plugin', 'skills')" in ps1
    assert "Join-Path $copyHome '.cursor\\plugins\\local\\handbuilt-cad'" in ps1
    assert "[string]$UserHome" in ps1
    assert "WhatIfPreference" in ps1
    assert "Refusing to copy the plugin into its own folder." in ps1
    assert "browser was not opened (test home). Nothing was scheduled." in ps1
    assert "plugins/local" not in (ROOT / "setup.sh").read_text(encoding="utf-8")
    assert "plugins\\local" not in (ROOT / "setup.ps1").read_text(encoding="utf-8")


def test_repo_does_not_name_another_project_repo():
    """The check file is the only place those names may appear, as the search terms.

    archives/ holds old state files kept verbatim (history), so it is not searched.
    """
    import subprocess

    for word in ("workstation", "living-relation-plugins"):
        found = subprocess.run(
            [
                "git", "grep", "-i", "-n", "-I", "--untracked", word, "--",
                ".", ":!tests/test_install_methods.py", ":!archives/",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert found.returncode == 1, found.stdout
