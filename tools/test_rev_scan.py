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


def test_new_job_and_next_rev(tmp_path):
    r1 = rev.create(tmp_path, "bracket", today=D)
    assert r1 == tmp_path / "bracket_1015" / "rev1"
    assert "bracket_1015 / rev1" in (r1 / "SUMMARY.md").read_text()
    (r1 / "SUMMARY.md").write_text("mine")
    r2 = rev.create(tmp_path, "bracket", today=D)
    assert r2.name == "rev2" and (r1 / "SUMMARY.md").read_text() == "mine"


def test_existing_job_variants_and_date(tmp_path):
    (tmp_path / "knuckle_1009" / "rev4b").mkdir(parents=True)
    (tmp_path / "knuckle_1009" / "rev1-best").mkdir()
    assert rev.create(tmp_path, "knuckle_1009", today=D).name == "rev5"
    assert rev.create(tmp_path, "knuckle", today=D).parent.name == "knuckle_1009"
    assert rev.create(tmp_path, "pipe", date="1014", today=D).parent.name == "pipe_1014"


def test_never_overwrites(tmp_path, monkeypatch):
    r1 = rev.create(tmp_path, "x", today=D)
    monkeypatch.setattr(rev, "next_rev", lambda d: 1)
    with pytest.raises(FileExistsError):
        rev.create(tmp_path, "x", today=D)
    assert (r1 / "SUMMARY.md").exists()


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


def test_scan_helper_needs_env(tmp_path):
    with pytest.raises(scan_helper.FairsolidNotFound):
        scan_helper.fairsolid_exe({})
    with pytest.raises(scan_helper.FairsolidNotFound):
        scan_helper.fairsolid_exe({"FAIRSOLID_HOME": str(tmp_path)})


def test_scan_helper_builds_command(tmp_path):
    exe = _fake_fairsolid(tmp_path)
    env = {"FAIRSOLID_HOME": str(tmp_path)}
    cmd = scan_helper.build_cmd("prepare", "s.stl", str(tmp_path / "run"), ["--force"], env)
    assert cmd[0] == str(exe) and cmd[1] == "prepare-cmd" and cmd[-1] == "--force"
    assert scan_helper.build_cmd("fit", None, None, [], env)[1:] == ["fit"]
    with pytest.raises(ValueError):
        scan_helper.build_cmd("run", None, None, [], env)


def test_scan_helper_main_runs_fake(tmp_path, monkeypatch, capfd):
    _fake_fairsolid(tmp_path)
    monkeypatch.setenv("FAIRSOLID_HOME", str(tmp_path))
    assert scan_helper.main(["fit", "--run", str(tmp_path / "r")]) == 0
    assert "fake fit --run" in capfd.readouterr().out
    monkeypatch.delenv("FAIRSOLID_HOME")
    assert scan_helper.main(["check"]) == 2
