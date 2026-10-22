import shutil, subprocess, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import paths


def test_env_wins(tmp_path):
    assert paths.parts_home({"HBCAD_PARTS_HOME": str(tmp_path)}) == tmp_path


def test_local_toml(tmp_path):
    t = tmp_path / "local.toml"
    t.write_text('[paths]\nparts_home = "%s"\n' % (tmp_path / "h"))
    assert paths.parts_home({}, toml=t) == tmp_path / "h"


def test_default(tmp_path):
    assert paths.parts_home({}, toml=tmp_path / "none.toml").name == "cad-parts"


def test_run_dir_created(tmp_path):
    env = {"HBCAD_PARTS_HOME": str(tmp_path / "home")}
    d = paths.run_dir("job_1021", "20261021-2000", env=env)
    assert d == tmp_path / "home" / "job_1021" / "runs" / "20261021-2000" and d.is_dir()
    assert paths.job_src("job_1021", env=env) == tmp_path / "home" / "job_1021" / "src"


def test_local_toml_only_paths_section(tmp_path):
    t = tmp_path / "local.toml"
    t.write_text('[other]\nparts_home = "/wrong"\n\n[paths]\nmodels_dir = "/m"\n')
    assert paths.parts_home({}, toml=t).name == "cad-parts"
    t.write_text('[other]\nparts_home = "/wrong"\n[paths]\nparts_home = "%s"\n' % (tmp_path / "h"))
    assert paths.parts_home({}, toml=t) == tmp_path / "h"


def test_run_dir_refuses_git_repo(tmp_path):
    if not shutil.which("git"):
        pytest.skip("git not installed")
    subprocess.run(["git", "init", "-q", str(tmp_path / "repo")], check=True)
    with pytest.raises(SystemExit):
        paths.run_dir("j", "s", env={"HBCAD_PARTS_HOME": str(tmp_path / "repo" / "x")}, create=False)


def test_in_git_without_git(tmp_path, monkeypatch):
    def no_git(*a, **k):
        raise FileNotFoundError("git")
    monkeypatch.setattr(paths.subprocess, "run", no_git)
    assert paths.in_git(tmp_path) is False
    (tmp_path / "r" / ".git").mkdir(parents=True)
    assert paths.in_git(tmp_path / "r" / "sub") is True
