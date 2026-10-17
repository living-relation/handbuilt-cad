"""tools/rev.py: lettered rev folders (A-Z skipping I, L, O, Q, then AA ...), clerical .NN decimals, never convert revN."""
import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import rev  # noqa: E402

D = dt.date(2026, 10, 17)


def mk(root, *names):
    for n in names:
        (root / n).mkdir(parents=True)


def test_new_job_is_rev_a_then_b(tmp_path):
    r1 = rev.create(tmp_path, "bracket", today=D)
    assert r1 == tmp_path / "bracket_1017" / "revA"
    s = (r1 / "SUMMARY.md").read_text()
    assert "bracket_1017 / revA" in s and "brand-new model" in s and "STL only if a print job" in s
    (r1 / "SUMMARY.md").write_text("mine")
    r2 = rev.create(tmp_path, "bracket", today=D)
    assert r2.name == "revB" and (r1 / "SUMMARY.md").read_text() == "mine"


@pytest.mark.parametrize("have,want", [("revH", "revJ"), ("revK", "revM"), ("revN", "revP"), ("revP", "revR"),
                                       ("revZ", "revAA"), ("revAH", "revAJ"), ("revAZ", "revBA")])
def test_skips_i_l_o_q_and_rolls_over(tmp_path, have, want):
    mk(tmp_path / "j_1017", have)
    assert rev.next_rev(tmp_path / "j_1017") == want


def test_highest_letter_wins_not_newest_folder(tmp_path):
    mk(tmp_path / "j_1017", "revAB", "revZ", "revC.02", "notes")
    assert rev.next_rev(tmp_path / "j_1017") == "revAC"


def test_clerical_decimals(tmp_path):
    job = tmp_path / "plate_1017"
    mk(job, "revD")
    assert rev.create(tmp_path, "plate_1017", clerical=True, today=D).name == "revD.01"
    c2 = rev.create(tmp_path, "plate_1017", clerical=True, today=D)
    assert c2.name == "revD.02"
    s = (c2 / "SUMMARY.md").read_text()
    assert "no model file" in s and "not listed in REVLOG.md" in s
    assert rev.create(tmp_path, "plate_1017", today=D).name == "revE"          # model change resets the decimal
    assert rev.create(tmp_path, "plate_1017", clerical=True, today=D).name == "revE.01"


def test_clerical_needs_a_released_letter(tmp_path):
    with pytest.raises(rev.RevError, match="clerical"):
        rev.next_rev(tmp_path / "new_1017", clerical=True)
    mk(tmp_path / "old_1017", "rev3")
    with pytest.raises(rev.RevError):
        rev.next_rev(tmp_path / "old_1017", clerical=True)


def test_numeric_only_is_never_converted(tmp_path):
    job = tmp_path / "knuckle_1009"
    mk(job, "rev1", "rev4b", "rev7-best")
    with pytest.raises(rev.RevError, match="numeric"):
        rev.next_rev(job)
    assert rev.next_rev(job, releases=7) == "revH"                # 7 counted releases = G, next is H
    assert rev.next_rev(job, releases=0) == "revA"
    assert rev.next_rev(job, letter="h") == "revH"
    r = rev.create(tmp_path, "knuckle_1009", releases=7, today=D)
    assert "7 counted past release" in (r / "SUMMARY.md").read_text()
    assert sorted(p.name for p in job.iterdir()) == ["rev1", "rev4b", "rev7-best", "revH"]   # old folders untouched


def test_lettered_folders_win_over_numeric(tmp_path):
    mk(tmp_path / "k_1009", "rev12", "revC")
    assert rev.next_rev(tmp_path / "k_1009") == "revD"


@pytest.mark.parametrize("bad", ["I", "O", "AQ", "3", ""])
def test_bad_letters_rejected(tmp_path, bad):
    with pytest.raises(rev.RevError):
        rev.next_rev(tmp_path / "x_1017", letter=bad)


def test_never_reuse_or_go_back(tmp_path):
    mk(tmp_path / "x_1017", "revD")
    for l in ("D", "C"):
        with pytest.raises(rev.RevError, match="never reuse"):
            rev.next_rev(tmp_path / "x_1017", letter=l)
    with pytest.raises(rev.RevError):
        rev.next_rev(tmp_path / "x_1017", letter="E", releases=4)


def test_never_overwrites(tmp_path, monkeypatch):
    r1 = rev.create(tmp_path, "x", today=D)
    monkeypatch.setattr(rev, "next_rev", lambda *a, **k: "revA")
    with pytest.raises(FileExistsError):
        rev.create(tmp_path, "x", today=D)
    assert (r1 / "SUMMARY.md").exists()


def test_job_resolution(tmp_path):
    mk(tmp_path / "knuckle_1009", "revB")
    assert rev.create(tmp_path, "knuckle", today=D).parent.name == "knuckle_1009"
    assert rev.create(tmp_path, "pipe", date="1014", today=D).parent.name == "pipe_1014"


def test_cli_exit_codes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    assert rev.main(["bracket", "--date", "1017"]) == 0
    assert capsys.readouterr().out.strip().endswith(os.path.join("bracket_1017", "revA"))
    mk(tmp_path / "old_1009", "rev2")
    assert rev.main(["old_1009"]) == 2
    assert "numeric" in capsys.readouterr().err
