"""Tests for tools/rev.py and tools/scan_helper.py (no Fairsolid install needed)."""
import datetime as dt
import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev  # noqa: E402
import scan_helper  # noqa: E402

D = dt.date(2026, 10, 15)


# rev folder tests (lettered revs) are in tests/test_rev_folders.py


def test_models_dir_required(tmp_path):
    with pytest.raises(SystemExit):
        rev.models_dir({})
    assert rev.models_dir({"MODELS_DIR": str(tmp_path)}) == tmp_path


def _fake_fairsolid(home: Path) -> Path:
    exe = home / ".venv" / "bin" / "fairsolid"
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/bin/sh\necho fake \"$@\"\n")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return exe


def test_scan_helper_needs_venv(tmp_path):
    with pytest.raises(scan_helper.FairsolidNotFound):
        scan_helper.fairsolid_exe({}, default=tmp_path / "none")
    with pytest.raises(scan_helper.FairsolidNotFound):
        scan_helper.fairsolid_exe({"FAIRSOLID_HOME": str(tmp_path)})


def test_scan_helper_falls_back_to_pipelines(tmp_path):
    assert scan_helper.default_home().parts[-2:] == ("pipelines", "fairsolid")
    exe = _fake_fairsolid(tmp_path)
    assert scan_helper.fairsolid_exe({}, default=tmp_path) == exe
    other = tmp_path / "other"
    exe2 = _fake_fairsolid(other)
    assert scan_helper.fairsolid_exe({"FAIRSOLID_HOME": str(other)}, default=tmp_path) == exe2


def test_scan_helper_builds_command(tmp_path):
    exe = _fake_fairsolid(tmp_path)
    env = {"FAIRSOLID_HOME": str(tmp_path)}
    cmd = scan_helper.build_cmd("prepare", "s.stl", str(tmp_path / "run"), ["--force"], env)
    assert cmd[0] == str(exe) and cmd[1] == "prepare-cmd" and cmd[-1] == "--force"
    assert scan_helper.build_cmd("fit", None, None, [], env)[1:] == ["fit"]
    with pytest.raises(ValueError):
        scan_helper.build_cmd("run", None, None, [], env)


@pytest.mark.skipif(sys.platform == "win32", reason="runs a POSIX shell-script fake of fairsolid; Linux/WSL only")
def test_scan_helper_main_runs_fake(tmp_path, monkeypatch, capfd):
    _fake_fairsolid(tmp_path)
    monkeypatch.setenv("FAIRSOLID_HOME", str(tmp_path))
    assert scan_helper.main(["fit", "--run", str(tmp_path / "r")]) == 0
    assert "fake fit --run" in capfd.readouterr().out
    monkeypatch.delenv("FAIRSOLID_HOME")
    monkeypatch.setattr(scan_helper, "default_home", lambda: tmp_path / "none")
    assert scan_helper.main(["check"]) == 2
