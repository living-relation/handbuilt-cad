import re
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
    assert sum(l.startswith("added") for l in log) == 6
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
