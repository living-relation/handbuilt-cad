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
    home = tmp_path / "home"; home.mkdir()
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


def test_ps1_reuses_existing_wsl_clone_no_duplicate():
    ps1 = (ROOT / "setup.ps1").read_text()
    assert "[string]$WslClone = ''" in ps1
    order = ["$WslClone, $lc, '~/projects/handbuilt-cad', '~/handbuilt-cad'"]
    assert order[0] in ps1
    assert "else { '~/projects/handbuilt-cad' }" in ps1
    assert "using existing clone" in ps1 and "no clone found, cloning into" in ps1
    assert ps1.index("using existing clone") < ps1.index("git clone $url")
    assert "wsl_clone" in ps1 and "$sec -eq 'paths'" in ps1
    inst = (ROOT / "docs" / "wiki" / "Install.md").read_text()
    assert "~/projects/handbuilt-cad" in inst and "in `~/handbuilt-cad`, cloned if missing" not in inst


def test_ps1_reports_wsl_clone_commit_and_warns():
    ps1 = (ROOT / "setup.ps1").read_text()
    assert "at commit" in ps1 and "WARNING: WSL clone is at" in ps1 and "git pull --ff-only)" in ps1
    assert "cd `\"`$c`\"" in ps1  # clone path quoted in bash
