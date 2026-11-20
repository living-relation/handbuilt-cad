"""tools/rev.py: lettered version folders (A-Z skipping I, L, O, Q, then AA ...), clerical .NN, keep-two prune."""
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
    assert r1 == tmp_path / "bracket" / "revA"
    s = (r1 / "SUMMARY.md").read_text()
    assert "bracket / revA" in s and "brand-new model" in s and "No .f3d, STL" in s and "Mass / material" in s
    (r1 / "SUMMARY.md").write_text("mine")
    r2 = rev.create(tmp_path, "bracket", today=D)
    assert r2 == tmp_path / "bracket" / "revB" and (r1 / "SUMMARY.md").read_text() == "mine"


def test_existing_job_names_are_kept(tmp_path):
    mk(tmp_path / "audi-catch-can-firewall-revB", "revA", "revB")
    mk(tmp_path / "knuckle_1009", "revB")
    assert rev.create(tmp_path, "audi-catch-can-firewall", today=D) == tmp_path / "audi-catch-can-firewall-revB" / "revC"
    assert rev.create(tmp_path, "knuckle", today=D) == tmp_path / "knuckle_1009" / "revC"
    assert rev.create(tmp_path, "knuckle_1009", today=D) == tmp_path / "knuckle_1009" / "revD"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["audi-catch-can-firewall-revB", "knuckle_1009"]


def test_ambiguous_subject_needs_the_folder_name(tmp_path):
    mk(tmp_path / "knuckle-rev5", "rev5")
    mk(tmp_path / "knuckle_1009", "revB")
    with pytest.raises(rev.RevError, match="several"):
        rev.create(tmp_path, "knuckle", today=D)
    assert rev.create(tmp_path, "knuckle_1009", today=D).name == "revC"


@pytest.mark.parametrize("have,want", [("revH", "revJ"), ("revK", "revM"), ("revN", "revP"), ("revP", "revR"),
                                       ("revZ", "revAA"), ("revAH", "revAJ"), ("revAZ", "revBA")])
def test_skips_i_l_o_q_and_rolls_over(tmp_path, have, want):
    mk(tmp_path / "j", have)
    assert rev.next_rev(tmp_path / "j") == want


def test_highest_letter_wins_not_newest_folder(tmp_path):
    mk(tmp_path / "j", "revAB", "revZ", "revC.02", "notes")
    assert rev.next_rev(tmp_path / "j") == "revAC"


def test_clerical_decimals(tmp_path):
    mk(tmp_path / "plate", "revD")
    assert rev.create(tmp_path, "plate", clerical=True, today=D).name == "revD.01"
    c2 = rev.create(tmp_path, "plate", clerical=True, today=D)
    assert c2.name == "revD.02"
    s = (c2 / "SUMMARY.md").read_text()
    assert "no model file" in s and "not listed in REVLOG.md" in s
    assert rev.create(tmp_path, "plate", today=D).name == "revE"          # model change resets the decimal
    assert rev.create(tmp_path, "plate", clerical=True, today=D).name == "revE.01"


def test_clerical_needs_a_released_letter(tmp_path):
    with pytest.raises(rev.RevError, match="clerical"):
        rev.next_rev(tmp_path / "new", clerical=True)
    mk(tmp_path / "old", "rev3")
    with pytest.raises(rev.RevError):
        rev.next_rev(tmp_path / "old", clerical=True)


def test_numeric_only_is_never_converted(tmp_path):
    job = tmp_path / "knuckle-rev7"
    mk(job, "rev1", "rev4b", "rev7-best")
    with pytest.raises(rev.RevError, match="numeric"):
        rev.next_rev(job)
    assert rev.next_rev(job, releases=7) == "revH"                # 7 counted releases = G, next is H
    assert rev.next_rev(job, releases=0) == "revA"
    assert rev.next_rev(job, letter="h") == "revH"
    r = rev.create(tmp_path, "knuckle", releases=7, today=D)
    assert r == job / "revH" and "7 counted past release" in (r / "SUMMARY.md").read_text()


def test_lettered_folders_win_over_numeric(tmp_path):
    mk(tmp_path / "k", "rev12", "revC")
    assert rev.next_rev(tmp_path / "k") == "revD"


@pytest.mark.parametrize("bad", ["I", "O", "AQ", "3", ""])
def test_bad_letters_rejected(tmp_path, bad):
    with pytest.raises(rev.RevError):
        rev.next_rev(tmp_path / "x", letter=bad)


def test_never_reuse_or_go_back(tmp_path):
    mk(tmp_path / "x", "revD")
    for l in ("D", "C"):
        with pytest.raises(rev.RevError, match="never reuse"):
            rev.next_rev(tmp_path / "x", letter=l)
    with pytest.raises(rev.RevError):
        rev.next_rev(tmp_path / "x", letter="E", releases=4)


def test_never_overwrites(tmp_path, monkeypatch):
    r1 = rev.create(tmp_path, "x", today=D)
    monkeypatch.setattr(rev, "next_rev", lambda *a, **k: "revA")
    with pytest.raises(FileExistsError):
        rev.create(tmp_path, "x", today=D)
    assert (r1 / "SUMMARY.md").exists()


def test_cli_exit_codes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    assert rev.main(["bracket"]) == 0
    assert capsys.readouterr().out.strip().endswith(os.path.join("bracket", "revA"))
    mk(tmp_path / "old_1009", "rev2")
    assert rev.main(["old_1009"]) == 2
    assert "numeric" in capsys.readouterr().err
    assert rev.main(["bracket", "--apply"]) == 2


def test_prune_keeps_two_versions_and_scans(tmp_path):
    job = tmp_path / "bracket-revD"
    mk(job, "revB", "revC", "revC.01", "revB.01", "revD", "rev2")
    assert rev.prune_revs(job) == (["rev2", "revB", "revB.01"], [])
    (job / "revB" / "scan.ply").write_text("cloud")
    drop, scans = rev.prune_revs(job, apply=True)
    assert drop == ["rev2", "revB.01"] and scans == ["revB"]
    assert (job / "revB" / "scan.ply").is_file() and not (job / "rev2").exists()
    assert all((job / n).is_dir() for n in ("revC", "revC.01", "revD"))


def test_prune_numeric_versions_sort_by_number(tmp_path):
    job = tmp_path / "filament-cabinet-rev3f"
    mk(job, "rev2", "rev3", "rev3e", "rev3f", "rev10")
    assert rev.prune_revs(job)[0] == ["rev2", "rev3", "rev3e"]      # rev10 and rev3f newest
    mk(job, "revA")
    assert rev.prune_revs(job)[0] == ["rev2", "rev3", "rev3e", "rev3f"]   # letters come after numbers


def test_prune_cli_lists_then_applies(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    job = tmp_path / "spacer-revC"
    mk(job, "revA", "revB", "revC")
    assert rev.main(["spacer", "--prune"]) == 0
    assert "would drop" in capsys.readouterr().out and (job / "revA").is_dir()
    assert rev.main(["spacer-revC", "--prune", "--apply"]) == 0
    assert not (job / "revA").exists() and (job / "revB").is_dir()
