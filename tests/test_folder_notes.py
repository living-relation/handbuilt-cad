import os, re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import folder_notes as fn


def layout(tmp_path):
    ph, md = tmp_path / "cad-parts", tmp_path / "models"
    for d in ("a_part_0101/src", "a_part_0101/runs", "_archive"):
        (ph / d).mkdir(parents=True)
    (ph / "AGENTS.md").write_text("owner")
    (md / "a_part_0101" / "revA").mkdir(parents=True)
    (md / "a_part_0101" / "revA" / "SUMMARY.md").write_text("# a_part_0101 revA: first cut\n")
    (md / "b_only_0202" / "revA").mkdir(parents=True)
    (md / "b_only_0202" / "revA" / "SUMMARY.md").write_text("# b_only_0202 / revA\n- What changed: thicker wall\n")
    (md / "README.md").write_text("models")
    return ph, md


def test_adds_every_note_then_idempotent(tmp_path):
    ph, md = layout(tmp_path)
    assert fn.missing(ph, md)
    log = fn.run(ph, md)
    assert sum(l.startswith("added") for l in log) == 7  # incl. the models-root AGENTS.md
    assert fn.missing(ph, md) == []
    before = {p: p.read_text() for p in tmp_path.rglob("README.md")}
    log2 = fn.run(ph, md)
    assert not any(l.startswith("added") for l in log2)
    assert before == {p: p.read_text() for p in tmp_path.rglob("README.md")}


def test_never_overwrites(tmp_path):
    ph, md = layout(tmp_path)
    (ph / "a_part_0101" / "src" / "README.md").write_text("mine")
    fn.run(ph, md)
    assert (ph / "a_part_0101" / "src" / "README.md").read_text() == "mine"


def test_models_note_content(tmp_path):
    ph, md = layout(tmp_path)
    fn.run(ph, md)
    a = (md / "a_part_0101" / "README.md").read_text()
    assert "`revA`: first cut" in a and fn.show(ph / "a_part_0101") in a and "publish-to-models" in a
    b = (md / "b_only_0202" / "README.md").read_text()
    assert "What changed: thicker wall" in b and "no parts-home folder" in b


def test_dry_run_and_check(tmp_path):
    ph, md = layout(tmp_path)
    fn.run(ph, md, dry=True)
    assert not (ph / "_archive" / "README.md").exists()
    assert (ph / "a_part_0101" / "runs") in fn.missing(ph, md)


def test_templates_generic():
    for t in (ROOT / "templates" / "notes").glob("*.md"):
        s = t.read_text()
        assert not re.search(r"/home/|/Users/|C:\\\\Users|OneDrive", s), t


def test_show_hides_personal_paths():
    import os
    assert fn.show(os.path.expanduser("~/cad-parts/x_0101")) == "~/cad-parts/x_0101"
    assert fn.show("/mnt/c/Users/someone/OneDrive/Desktop/models/x_0101") == "<Desktop>/models/x_0101"
    assert fn.rev_line.__doc__


def test_run_then_check_agree_models_root(tmp_path):
    ph, md = layout(tmp_path)
    (md / "README.md").unlink(); (ph / "AGENTS.md").unlink()
    fn.run(ph, md, clone=Path("/clone"))
    assert fn.missing(ph, md) == []
    assert "/clone" in (md / "AGENTS.md").read_text() and (ph / "AGENTS.md").exists()


def test_wsl_only_no_models(tmp_path):
    ph = tmp_path / "cad-parts"; (ph / "j_0101" / "src").mkdir(parents=True)
    fn.run(ph, None)
    assert fn.missing(ph, None) == []


def test_non_job_folders_warn(tmp_path):
    ph, md = layout(tmp_path)
    (ph / "scratchpad").mkdir(); (md / "loose").mkdir(); (ph / "_private").mkdir()
    warns = []
    fn.run(ph, md, warn=warns.append)
    assert any("scratchpad" in w for w in warns) and any("loose" in w for w in warns)
    assert not any("_private" in w for w in warns)
    assert not (ph / "scratchpad" / "README.md").exists()


def test_templates_mode_644():
    import stat
    for t in (ROOT / "templates").rglob("*.md"):
        assert not t.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), t


def _setup_5d():
    s = (ROOT / "setup.sh").read_text()
    return s[s.index("# 5d."):s.index("# end 5d")]


def _run_5d(tmp_path, python, models):
    import subprocess
    ph = tmp_path / "parts home"; ph.mkdir()
    block = "set -euo pipefail\n" + _setup_5d().replace(".venv/bin/python", python)
    env = dict(os.environ, PARTS=str(ph), MODELS=str(models), ROOT=str(tmp_path / "my clone"), NO_MODELS="0")
    return ph, subprocess.run(["bash", "-c", block], cwd=ROOT, env=env, capture_output=True, text=True)


def test_setup_5d_models_path_with_space(tmp_path):
    md = tmp_path / "Desktop" / "3D Models"; (md / "x_0101").mkdir(parents=True)
    ph, r = _run_5d(tmp_path, sys.executable, md)
    assert r.returncode == 0, r.stderr
    assert (md / "README.md").exists() and (md / "x_0101" / "README.md").exists()
    assert (ph / "AGENTS.md").exists() and "my clone" in (md / "AGENTS.md").read_text()


def test_setup_5d_failure_propagates(tmp_path):
    md = tmp_path / "m"; md.mkdir()
    _, r = _run_5d(tmp_path, "sh -c 'exit 3' x", md)
    assert r.returncode == 3
