"""setup.sh / setup.ps1 behaviour that can be checked without running the install."""
import os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = (ROOT / "setup.sh").read_text()


def _block(start, end):
    return SETUP[SETUP.index(start):SETUP.index(end)]


def _toml_paths(tmp_path, toml, key):
    (tmp_path / "local.toml").write_text(toml)
    script = _block("toml_paths() {", "# end toml_paths") + f"\ntoml_paths {key}\n"
    return subprocess.run(["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True, check=True).stdout.strip()


def test_toml_paths_reads_only_paths_section(tmp_path):
    toml = '[other]\nparts_home = "/wrong"\nmodels_dir = "/wrong"\n\n[ paths ]\nparts_home = \'/right parts\'\nmodels_dir = "D:/cad/models"\n[later]\nparts_home = "/late"\n'
    assert _toml_paths(tmp_path, toml, "parts_home") == "/right parts"
    assert _toml_paths(tmp_path, toml, "models_dir") == "D:/cad/models"


def test_toml_paths_missing(tmp_path):
    assert _toml_paths(tmp_path, '[other]\nparts_home = "/wrong"\n', "parts_home") == ""
    assert _toml_paths(tmp_path, '[paths]\nparts_home_x = "/wrong"\n', "parts_home") == ""


def test_toml_paths_matches_paths_py(tmp_path):
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import paths
    toml = '[x]\nparts_home = "/a"\n[paths]\nparts_home = "/b"\n'
    assert _toml_paths(tmp_path, toml, "parts_home") == paths._local("parts_home", tmp_path / "local.toml") == "/b"


def _run_step6(tmp_path, link):
    home = tmp_path / "home"; home.mkdir(exist_ok=True)
    root = tmp_path / "clone"; (root / "skills" / "demo").mkdir(parents=True)
    (root / "skills" / "demo" / "SKILL.md").write_text("x")
    env = dict(os.environ, HOME=str(home), ROOT=str(root), LINK_SKILLS=link)
    script = "set -euo pipefail\n" + _block("# 6. skills", "# end 6")
    r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return home, r.stdout


def test_skills_linked_by_default(tmp_path):
    home, out = _run_step6(tmp_path, "0")  # LINK_SKILLS=0 must still link
    assert (home / ".claude" / "skills" / "demo").is_symlink()
    assert not (home / ".cursor" / "skills").exists()
    assert "not linked" not in out


def test_skills_linked_with_noop_flag(tmp_path):
    home, _ = _run_step6(tmp_path, "1")
    assert (home / ".claude" / "skills" / "demo").is_symlink()
    assert not (home / ".cursor" / "skills" / "demo").exists()


def test_skills_link_ignores_zips_readme_and_folders_without_skill_md(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    root = tmp_path / "clone"
    (root / "skills" / "demo").mkdir(parents=True)
    (root / "skills" / "demo" / "SKILL.md").write_text("x")
    (root / "skills" / "demo.zip").write_bytes(b"PK")
    (root / "skills" / "README.md").write_text("not a skill")
    (root / "skills" / "not-a-skill").mkdir()
    (root / "skills" / "not-a-skill" / "notes.md").write_text("x")
    env = dict(os.environ, HOME=str(home), ROOT=str(root), LINK_SKILLS="0")
    script = "set -euo pipefail\n" + _block("# 6. skills", "# end 6")
    r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    dest = home / ".claude" / "skills"
    assert (dest / "demo").is_symlink()
    assert not (dest / "demo.zip").exists()
    assert not (dest / "README.md").exists()
    assert not (dest / "not-a-skill").exists()
    assert not (home / ".cursor" / "skills" / "demo").exists()


def test_dead_skill_links_pruned_only_when_ours(tmp_path):
    home = tmp_path / "home"
    root = tmp_path / "clone"
    other = tmp_path / "other"; (other / "keep").mkdir(parents=True)
    for t in (".claude", ".cursor"):
        d = home / t / "skills"; d.mkdir(parents=True)
        (d / "gone").symlink_to(root / "skills" / "gone")      # ours, dead
        (d / "elsewhere").symlink_to(other / "missing")        # not ours, dead
        (d / "keep").symlink_to(other / "keep")                # not ours
        (d / "real").mkdir()                                   # real folder
    _, out = _run_step6(tmp_path, "0")
    d = home / ".claude" / "skills"
    assert not (d / "gone").is_symlink() and not (d / "gone").exists()
    assert (d / "elsewhere").is_symlink() and (d / "keep").is_symlink() and (d / "real").is_dir()
    assert (d / "demo").is_symlink()
    c = home / ".cursor" / "skills"
    assert not (c / "gone").exists() and not (c / "demo").exists()
    assert (c / "elsewhere").is_symlink() and (c / "keep").is_symlink() and (c / "real").is_dir()
    assert "skill link pruned" in out
    assert "skill link unlinked" in out


def test_harness_app_skills_never_linked_or_touched(tmp_path):
    home = tmp_path / "home"
    root = tmp_path / "clone"
    (root / "skills" / "demo").mkdir(parents=True)
    (root / "skills" / "demo" / "SKILL.md").write_text("x")
    (root / "skills" / "harness-design").mkdir(parents=True)
    (root / "skills" / "harness-design" / "SKILL.md").write_text("---\nname: harness-design\n---\n")
    (root / "skills" / "marked-skill").mkdir(parents=True)
    (root / "skills" / "marked-skill" / "SKILL.md").write_text(
        "---\nname: marked-skill\nsource: harness-design-app\n---\n"
    )
    (root / "skills" / "EXCLUDE.txt").write_text("harness-design\n")
    claude = home / ".claude" / "skills"
    claude.mkdir(parents=True)
    (claude / "harness-design").mkdir()
    (claude / "harness-design" / "today.md").write_text("app edit\n")
    cursor = home / ".cursor" / "skills"
    cursor.mkdir(parents=True)
    (cursor / "harness-design").mkdir()
    (cursor / "harness-design" / "keep.md").write_text("app\n")
    env = dict(os.environ, HOME=str(home), ROOT=str(root), LINK_SKILLS="0")
    script = "set -euo pipefail\n" + _block("# 6. skills", "# end 6")
    r = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "SKIP harness app skill" in r.stdout
    assert (home / ".claude" / "skills" / "demo").is_symlink()
    assert not (home / ".claude" / "skills" / "harness-design").is_symlink()
    assert (claude / "harness-design" / "today.md").read_text() == "app edit\n"
    assert not (home / ".claude" / "skills" / "marked-skill").exists()
    assert not (home / ".cursor" / "skills" / "demo").exists()
    assert (cursor / "harness-design" / "keep.md").read_text() == "app\n"
    assert not (home / ".skills-backup").exists()


def test_cursor_our_links_unlinked_others_untouched(tmp_path):
    home = tmp_path / "home"
    root = tmp_path / "clone"  # _run_step6 creates root/skills/demo
    other = tmp_path / "other"; (other / "keep").mkdir(parents=True)
    d = home / ".cursor" / "skills"; d.mkdir(parents=True)
    (d / "demo").symlink_to(root / "skills" / "demo")  # ours: unlink, do not duplicate
    (d / "keep").symlink_to(other / "keep")            # not ours
    (d / "real").mkdir()                               # real folder
    _, out = _run_step6(tmp_path, "0")
    assert not (d / "demo").exists()
    assert (d / "keep").is_symlink() and (d / "real").is_dir()
    assert (home / ".claude" / "skills" / "demo").is_symlink()
    assert "skill link unlinked" in out


def test_ps1_link_skills_prunes_only_dead_links_into_from():
    ps1 = (ROOT / "scripts" / "link-skills.ps1").read_text()
    assert "[IO.Directory]::Delete($item.FullName, $false)" in ps1  # link only, never recursive
    assert "StartsWith($_, [StringComparison]::OrdinalIgnoreCase)" in ps1 and "'SKILL.md'" in ps1
    assert "'would-prune'" in ps1 and "Remove-Item" not in ps1


def test_ps1_link_skills_claude_only_unlinks_cursor():
    ps1 = (ROOT / "scripts" / "link-skills.ps1").read_text()
    assert '[string[]]$Targets = @("$env:USERPROFILE\\.claude\\skills"),' in ps1
    assert '[string[]]$Unlink = @("$env:USERPROFILE\\.cursor\\skills"),' in ps1
    assert "$env:USERPROFILE\\.cursor\\skills" not in ps1.split("[string[]]$Targets")[1].split("[string[]]$Unlink")[0]
    assert "'would-unlink'" in ps1 and "'unlinked'" in ps1 and ps1.count("[IO.Directory]::Delete($item.FullName, $false)") == 2


def test_setup_sh_flag_and_ps1_link_skills_noop():
    assert "--link-skills) LINK_SKILLS=1" in SETUP and "NO_SKILLS" not in SETUP
    assert 'LINK_SKILLS=1' in SETUP.split("for a in")[0]
    assert 'echo "skills: not linked' not in SETUP
    ps1 = (ROOT / "setup.ps1").read_text()
    assert "[switch]$LinkSkills" in ps1 and "if (-not $LinkSkills)" not in ps1 and "NoSkills" not in ps1
    assert r"scripts\link-skills.ps1" in ps1


def test_ps1_runs_wsl_half():
    ps1 = (ROOT / "setup.ps1").read_text()
    for s in ("[switch]$NoWsl", "wsl.exe -d $WslDistro", "bash setup.sh", "'--no-models'",
              "wsl.exe not found", "not found (have:", "$LASTEXITCODE -ne 0"):
        assert s in ps1, s
    assert "'--link-skills'" not in ps1
    assert ps1.index("if ($NoWsl)") < ps1.index("wsl.exe -d $WslDistro")


def test_ps1_links_one_clone_into_wsl_never_clones():
    ps1 = (ROOT / "setup.ps1").read_text()
    assert "[string]$WslLink = ''" in ps1 and "WslClone" not in ps1 and "wsl_clone" not in ps1
    assert "@($WslLink, $lc, '~/projects/handbuilt-cad')" in ps1 and "wsl_link" in ps1 and "$sec -eq 'paths'" in ps1
    assert "git clone" not in ps1 and "wslpath -u $(& $sq $Root)" in ps1 and "wsl_link '$link' is not valid" in ps1 and "ln -s" in ps1
    assert "(exists, left as is)" in ps1 and ps1.count("exit 3") == 2 and "Nothing changed" in ps1
    assert ps1.index("[ -L ") < ps1.index("elif [ -e ") < ps1.index("ln -s")  # link check, then real-folder stop, then create
    assert "UV_PROJECT_ENVIRONMENT:-`$HOME/.venvs/handbuilt-cad" in ps1
    inst = (ROOT / "docs" / "wiki" / "Install.md").read_text()
    assert "~/projects/handbuilt-cad" in inst and "one clone" in inst.lower()


def _link_block(tmp_path):
    """The bash link step of setup.ps1 (between 'l=...' and 'export UV_'), with t/l given by the test."""
    ps1 = (ROOT / "setup.ps1").read_text()
    body = ps1[ps1.index('"if [ -L '):ps1.index('"export UV_PROJECT_ENVIRONMENT')]
    parts = [p.strip().rstrip("+").strip() for p in body.splitlines()]
    s = "".join(p[1:-1] for p in parts if p.startswith('"'))
    return s.replace('`"', '"').replace("`$", "$")


def _run_link(tmp_path, prep=None):
    t = tmp_path / "C" / "handbuilt-cad"; t.mkdir(parents=True, exist_ok=True)
    l = tmp_path / "home" / "projects" / "handbuilt-cad"
    if prep: prep(l)
    script = f"set -e; t='{t}'; l='{l}'; " + _link_block(tmp_path)
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return t, l, r


def test_wsl_link_created_then_idempotent(tmp_path):
    t, l, r = _run_link(tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    assert l.is_symlink() and l.resolve() == t.resolve() and "linked" in r.stdout
    _, _, r2 = _run_link(tmp_path)
    assert r2.returncode == 0 and "left as is" in r2.stdout


def test_wsl_link_never_overwrites_real_folder_or_other_link(tmp_path):
    def real(l): l.mkdir(parents=True); (l / "keep.txt").write_text("x")
    _, l, r = _run_link(tmp_path, real)
    assert r.returncode == 3 and "STOP" in r.stdout and (l / "keep.txt").read_text() == "x" and not l.is_symlink()
    other = tmp_path / "other"; other.mkdir()
    def wrong(l): l.parent.mkdir(parents=True); l.symlink_to(other)
    _, l2, r2 = _run_link(tmp_path / "b", wrong)
    assert r2.returncode == 3 and "STOP" in r2.stdout and l2.resolve() == other.resolve()


def test_setup_sh_linux_venv_outside_repo_on_windows_drive():
    assert 'case "$(pwd -P)" in /mnt/[a-z]/*) export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-$HOME/.venvs/handbuilt-cad}"' in SETUP
    assert 'VENV="${UV_PROJECT_ENVIRONMENT:-$ROOT/.venv}"' in SETUP and 'export CAD_PY="\\${CAD_PY:-$VENV/bin/python}"' in SETUP
    assert "env -u UV_PROJECT_ENVIRONMENT" in SETUP

def test_ps1_wsl_command_survives_windows_powershell_51():
    """PS 5.1 mangles embedded double quotes in native args, so the bash script goes to wsl.exe base64-encoded."""
    ps1 = (ROOT / "setup.ps1").read_text()
    assert "bash -lc $cmd" not in ps1
    assert "[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(\"exec </dev/null; $cmd\"))" in ps1
    assert 'bash -lc "echo $b64 | base64 -d | bash"' in ps1


def test_setup_installs_sim_by_default_with_opt_out():
    assert "SIM=1;" in SETUP and "--no-sim) SIM=0" in SETUP and "sudo apt-get install -y $need" in SETUP
    assert "Or paste in a terminal:" in SETUP and "sudo -n true" in SETUP
    assert '"$UV" venv "$SIM_VENV" --python "$SIM_PY"' in SETUP and 'SIM_PY="${SIM_PYTHON:-$(cat .python-version)}"' in SETUP
    assert "sudo -n apt-get install -y $need" in SETUP and "setup.ps1 from Windows" in SETUP
    assert 'SIM_VENV="${SIM_VENV:-$HOME/simvenv}"' in SETUP
    assert "python3 " not in SETUP.split("# 2c.")[1].split("# 3.")[0]
    ps1 = (ROOT / "setup.ps1").read_text()
    assert "[switch]$NoSim" in ps1 and "if ($NoSim) { $shArgs += '--no-sim' }" in ps1
    assert "wsl.exe -d $WslDistro -u root -e bash -c" in ps1 and "DEBIAN_FRONTEND=noninteractive apt-get update" in ps1
    assert "-replace '=.*$', ''" in ps1 and ps1.index("-u root") < ps1.index("echo $b64 | base64 -d | bash")


def test_sim_apt_missing_strips_versions(tmp_path):
    (tmp_path / "apt-sim.txt").write_text("# c\ncalculix-ccx=2.21-1\n\ngmsh=4.14\n")
    bin_ = tmp_path / "bin"; bin_.mkdir()
    (bin_ / "dpkg-query").write_text("#!/bin/sh\n[ \"$3\" = gmsh ] && echo 'install ok installed'; exit 0\n")
    (bin_ / "dpkg-query").chmod(0o755)
    script = _block("  sim_apt_missing() {", "  # end sim_apt_missing") + "\nsim_apt_missing\n"
    env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}")
    r = subprocess.run(["bash", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True, check=True)
    assert r.stdout.split() == ["calculix-ccx"]


def test_verify_fails_loudly_with_list(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "USER": "x"}
    r = subprocess.run(["bash", str(ROOT / "scripts" / "verify-install.sh")], env=env, capture_output=True, text=True)
    assert r.returncode == 1 and "FAILED" in r.stderr
    for s in ("CAD_HOME", "CAD_PY", "MODELS_DIR", "HBCAD_PARTS_HOME", "build123d", "sim venv"):
        assert s in r.stderr, s
    assert "verify-install.sh" in SETUP and "exit 1" in SETUP.split("# 8. verify")[1]


def test_env_file_loads_in_bash_lc(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    (home / ".profile").write_text("# existing\n")
    blk = _block("# 7. env file", "# end 7")
    pre = f"ROOT=/r; VENV=/v; MODELS=/m; PARTS=/p; SIM_VENV={home}/simvenv; PROFILE=1\n"
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    for _ in range(2):  # idempotent
        subprocess.run(["bash", "-c", "set -euo pipefail\n" + pre + blk], env=env, check=True, capture_output=True)
    assert (home / ".profile").read_text().count("handbuilt-cad setup") == 1
    assert (home / ".profile").read_text().count("export SIM_VENV=") == 1


def test_profile_keeps_existing_sim_venv_line(tmp_path):
    home = tmp_path / "home"; home.mkdir()
    (home / ".profile").write_text('export SIM_VENV="$HOME/simvenv"\n')
    blk = _block("# 7. env file", "# end 7")
    pre = f"ROOT=/r; VENV=/v; MODELS=/m; PARTS=/p; SIM_VENV={home}/simvenv; PROFILE=1\n"
    subprocess.run(["bash", "-c", "set -euo pipefail\n" + pre + blk], env={"HOME": str(home), "PATH": "/usr/bin:/bin"}, check=True, capture_output=True)
    assert (home / ".profile").read_text().count("export SIM_VENV=") == 1
    out = subprocess.run(["env", "-i", f"HOME={home}", "bash", "-lc", 'echo "$CAD_HOME $CAD_PY $MODELS_DIR $HBCAD_PARTS_HOME $SIM_VENV"'],
                         capture_output=True, text=True).stdout.strip()
    assert out == f"/r /v/bin/python /m /p {home}/simvenv"


def test_install_cmd_is_setup_ps1_wrapper_passthrough():
    """install.cmd runs setup.ps1 with default args and %*; it must not add flags."""
    cmd = (ROOT / "install.cmd").read_text()
    assert "@echo off" in cmd
    assert 'cd /d "%~dp0"' in cmd
    assert "powershell -NoProfile -ExecutionPolicy Bypass -File setup.ps1 %*" in cmd
    assert "Exit code:" in cmd and "pause" in cmd
    assert "-NoSim" not in cmd and "-LinkSkills" not in cmd and "-NoWsl" not in cmd
    assert "-NoPopup" not in cmd and "-Quiet" not in cmd
    readme = (ROOT / "README.md").read_text()
    assert "`pull.cmd`" in readme and "`install.cmd`" in readme


def test_ps1_skill_upload_popup_at_end():
    ps1 = (ROOT / "setup.ps1").read_text()
    pop = (ROOT / "scripts" / "skill-upload-popup.ps1").read_text()
    assert "[switch]$NoPopup" in ps1 and "[switch]$Quiet" in ps1
    assert r"scripts\skill-upload-popup.ps1" in ps1
    assert ps1.index("link-skills.ps1") < ps1.index("skill-upload-popup.ps1")
    assert ps1.index("skill-upload-popup.ps1") > ps1.index("Optional: setx MODELS_DIR")
    reminder = "Upload new or changed CAD skill zips to the Claude desktop app for each Claude account (Skills settings)."
    assert reminder in pop
    assert "System.Windows.Forms" in pop and "WScript.Shell" in pop
    assert "explorer.exe" in pop
    assert "Open this folder in Explorer?" in pop
    assert "-Filter '*.zip'" in pop and "'SKILL.md'" in pop
    assert "$NoPopup -or $Quiet" in pop
    assert "'CI', 'GITHUB_ACTIONS', 'TF_BUILD'" in pop
    assert "skills popup: skipped (-NoPopup/-Quiet/CI)" in pop
    assert "-NoPopup:$NoPopup -Quiet:$Quiet" in ps1
