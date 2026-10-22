import sys
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


def test_run_dir_refuses_repo():
    with pytest.raises(SystemExit):
        paths.run_dir("j", "s", env={"HBCAD_PARTS_HOME": str(paths.ROOT / "x")}, create=False)
