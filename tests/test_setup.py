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


def test_skills_not_linked_by_default(tmp_path):
    home, out = _run_step6(tmp_path, "0")
    assert not (home / ".claude").exists() and not (home / ".cursor").exists()
    assert "not linked" in out


def test_skills_linked_with_opt_in(tmp_path):
    home, _ = _run_step6(tmp_path, "1")
    for t in (".claude", ".cursor"):
        assert (home / t / "skills" / "demo").is_symlink()


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
    _, out = _run_step6(tmp_path, "1")
    for t in (".claude", ".cursor"):
        d = home / t / "skills"
        assert not (d / "gone").is_symlink() and not (d / "gone").exists()
        assert (d / "elsewhere").is_symlink() and (d / "keep").is_symlink() and (d / "real").is_dir()
        assert (d / "demo").is_symlink()
    assert "skill link pruned" in out


def test_ps1_link_skills_prunes_only_dead_links_into_from():
    ps1 = (ROOT / "scripts" / "link-skills.ps1").read_text()
    assert "[IO.Directory]::Delete($item.FullName, $false)" in ps1  # link only, never recursive
    assert "StartsWith($_, [StringComparison]::OrdinalIgnoreCase)" in ps1 and "'SKILL.md'" in ps1
    assert "'would-prune'" in ps1 and "Remove-Item" not in ps1


def test_setup_sh_flag_and_ps1_opt_in():
    assert "--link-skills) LINK_SKILLS=1" in SETUP and "NO_SKILLS" not in SETUP
    ps1 = (ROOT / "setup.ps1").read_text()
    assert "[switch]$LinkSkills" in ps1 and "if (-not $LinkSkills)" in ps1 and "NoSkills" not in ps1


def test_ps1_runs_wsl_half():
    ps1 = (ROOT / "setup.ps1").read_text()
    for s in ("[switch]$NoWsl", "wsl.exe -d $WslDistro", "bash setup.sh", "'--no-models'", "'--link-skills'",
              "wsl.exe not found", "not found (have:", "$LASTEXITCODE -ne 0"):
        assert s in ps1, s
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
    assert 'VENV="${UV_PROJECT_ENVIRONMENT:-$ROOT/.venv}"' in SETUP and 'export CAD_PY="$VENV/bin/python"' in SETUP
    assert "env -u UV_PROJECT_ENVIRONMENT" in SETUP

def test_ps1_wsl_command_survives_windows_powershell_51():
    """PS 5.1 mangles embedded double quotes in native args, so the bash script goes to wsl.exe base64-encoded."""
    ps1 = (ROOT / "setup.ps1").read_text()
    assert "bash -lc $cmd" not in ps1
    assert "[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(\"exec </dev/null; $cmd\"))" in ps1
    assert 'bash -lc "echo $b64 | base64 -d | bash"' in ps1
