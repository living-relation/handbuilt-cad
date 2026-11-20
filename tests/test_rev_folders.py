"""tools/rev.py: per-part rev letters (skip I, L, O, Q), clerical decimals, never convert revN."""
import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import rev  # noqa: E402

D = dt.date(2026, 10, 17)


def card(job, name, text="x"):
    job.mkdir(parents=True, exist_ok=True)
    (job / name).write_text(text)


def test_new_job_is_rev_a_then_b(tmp_path):
    r1 = rev.create(tmp_path, "bracket", today=D)
    assert r1 == tmp_path / "bracket_1017" / "bracket-revA.md"
    s = r1.read_text()
    assert "bracket / revA" in s and "brand-new model" in s and "AP242 STEP only" in s
    r1.write_text("mine")
    r2 = rev.create(tmp_path, "bracket", today=D)
    assert r2.name == "bracket-revB.md" and r1.read_text() == "mine"
    assert r1.parent == r2.parent


@pytest.mark.parametrize("have,want", [("revH", "revJ"), ("revK", "revM"), ("revN", "revP"), ("revP", "revR"),
                                       ("revZ", "revAA"), ("revAH", "revAJ"), ("revAZ", "revBA")])
def test_skips_i_l_o_q_and_rolls_over(tmp_path, have, want):
    job = tmp_path / "j_1017"
    card(job, f"j-{have}.md")
    assert rev.next_rev(job, "j") == want


def test_highest_letter_wins_not_newest_file(tmp_path):
    job = tmp_path / "j_1017"
    for name in ("j-revAB.md", "j-revZ.md", "j-revC.02.md"):
        card(job, name)
    assert rev.next_rev(job, "j") == "revAC"


def test_other_part_does_not_move_this_letter(tmp_path):
    job = tmp_path / "rover_1017"
    card(job, "gear-revC.md")
    card(job, "leg-revA.md")
    assert rev.next_rev(job, "leg") == "revB"
    assert rev.create(tmp_path, "rover_1017", part="leg", today=D).name == "leg-revB.md"
    assert (job / "gear-revC.md").is_file()


def test_clerical_decimals(tmp_path):
    job = tmp_path / "plate_1017"
    card(job, "plate-revD.md", "model")
    assert rev.create(tmp_path, "plate_1017", clerical=True, today=D).name == "plate-revD.01.md"
    c2 = rev.create(tmp_path, "plate_1017", clerical=True, today=D)
    assert c2.name == "plate-revD.02.md"
    s = c2.read_text()
    assert "no model file" in s and "not listed in REVLOG.md" in s
    assert (job / "plate-revD.md").read_text() == "model"
    assert rev.create(tmp_path, "plate_1017", today=D).name == "plate-revE.md"
    assert rev.create(tmp_path, "plate_1017", clerical=True, today=D).name == "plate-revE.01.md"


def test_clerical_needs_a_released_letter(tmp_path):
    with pytest.raises(rev.RevError, match="clerical"):
        rev.next_rev(tmp_path / "new_1017", "new", clerical=True)
    job = tmp_path / "old_1017"
    job.mkdir()
    (job / "rev3").mkdir()
    with pytest.raises(rev.RevError):
        rev.next_rev(job, "old", clerical=True)


def test_numeric_only_is_never_converted(tmp_path):
    job = tmp_path / "knuckle_1009"
    job.mkdir()
    for name in ("rev1", "rev4b", "rev7-best"):
        (job / name).mkdir()
    with pytest.raises(rev.RevError, match="numeric"):
        rev.next_rev(job, "knuckle")
    assert rev.next_rev(job, "knuckle", releases=7) == "revH"
    assert rev.next_rev(job, "knuckle", releases=0) == "revA"
    assert rev.next_rev(job, "knuckle", letter="h") == "revH"
    r = rev.create(tmp_path, "knuckle_1009", releases=7, today=D)
    assert r == job / "knuckle-revH.md"
    assert "7 counted past release" in r.read_text()
    assert (job / "rev1").is_dir() and (job / "rev7-best").is_dir()


def test_lettered_file_wins_over_numeric_folder(tmp_path):
    job = tmp_path / "k_1009"
    card(job, "k-revC.md")
    (job / "rev12").mkdir()
    assert rev.next_rev(job, "k") == "revD"


@pytest.mark.parametrize("bad", ["I", "O", "AQ", "3", ""])
def test_bad_letters_rejected(tmp_path, bad):
    job = tmp_path / "x_1017"
    job.mkdir()
    with pytest.raises(rev.RevError):
        rev.next_rev(job, "x", letter=bad)


def test_never_reuse_or_go_back(tmp_path):
    job = tmp_path / "x_1017"
    card(job, "x-revD.md")
    for letter in ("D", "C"):
        with pytest.raises(rev.RevError, match="never reuse"):
            rev.next_rev(job, "x", letter=letter)
    with pytest.raises(rev.RevError):
        rev.next_rev(job, "x", letter="E", releases=4)


def test_never_overwrites(tmp_path, monkeypatch):
    r1 = rev.create(tmp_path, "x", today=D)
    monkeypatch.setattr(rev, "next_rev", lambda *a, **k: "revA")
    with pytest.raises(FileExistsError):
        rev.create(tmp_path, "x", today=D)
    assert r1.read_text()


def test_job_resolution(tmp_path):
    job = tmp_path / "knuckle_1009"
    card(job, "knuckle-revB.md", "old")
    r = rev.create(tmp_path, "knuckle", today=D)
    assert r == job / "knuckle-revC.md" and (job / "knuckle-revB.md").read_text() == "old"
    assert rev.create(tmp_path, "pipe", date="1014", today=D).parent.name == "pipe_1014"


def test_cli_exit_codes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    assert rev.main(["bracket", "--date", "1017"]) == 0
    assert capsys.readouterr().out.strip().endswith(os.path.join("bracket_1017", "bracket-revA.md"))
    old = tmp_path / "old_1009"
    old.mkdir()
    (old / "rev2").mkdir()
    assert rev.main(["old_1009"]) == 2
    assert "numeric" in capsys.readouterr().err


def test_prune_is_per_part_and_leaves_reference(tmp_path):
    job = tmp_path / "bracket_1017"
    for name in ("bracket-revA.step", "bracket-revB.step", "bracket-revC.step", "bracket-revB.01.md",
                 "leg-revA.step", "leg-revB.step"):
        card(job, name, "m")
    (job / "reference").mkdir()
    (job / "reference" / "hinge.step").write_text("maker")
    (job / "README.md").write_text("note")
    drop = rev.prune_revs(job, apply=True)
    assert [p.name for p in drop] == ["bracket-revA.step"]
    assert not (job / "bracket-revA.step").exists()
    assert (job / "bracket-revB.step").is_file() and (job / "bracket-revC.step").is_file()
    assert (job / "bracket-revB.01.md").is_file()
    assert (job / "leg-revA.step").is_file() and (job / "leg-revB.step").is_file()
    assert (job / "reference" / "hinge.step").is_file() and (job / "README.md").is_file()
    assert job.is_dir()
