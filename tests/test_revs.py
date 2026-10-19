import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "drawing"))
import revs as R

def test_letters_skip_ILOQ():
    seq = [R.index_to_letter(i) for i in range(22)]
    assert seq == list("ABCDEFGHJKMNPRSTUVWXYZ")
    for bad in "ILOQ": assert bad not in seq

def test_rollover_past_Z():
    assert R.next_letter("Z") == "AA"
    assert R.next_letter("AA") == "AB"
    assert R.next_letter("AH") == "AJ"      # skips AI
    assert R.next_letter("AK") == "AM"      # skips AL
    assert R.next_letter("AN") == "AP"      # skips AO
    assert R.next_letter("AP") == "AR"      # skips AQ
    assert R.next_letter("AZ") == "BA"
    assert R.next_letter("ZZ") == "AAA"

def test_roundtrip():
    for i in range(0, 3000):
        assert R.letter_to_index(R.index_to_letter(i)) == i

def test_invalid_letters():
    for bad in ("I", "O", "AQ", "L", "", "1"):
        with pytest.raises(ValueError): R.letter_to_index(bad)

def test_release_count():
    assert R.letter_from_release_count(1) == "A"
    assert R.letter_from_release_count(7) == "G"
    assert R.letter_from_release_count(9) == "J"     # I skipped
    assert R.letter_from_release_count(23) == "AA"

def test_clerical_and_model_bumps():
    assert R.bump_clerical("C") == "C.01"
    assert R.bump_clerical("C.01") == "C.02"
    assert R.bump_model("C.02") == "D"
    assert R.bump_model("H") == "J"
    assert R.bump_model("Z.03") == "AA"
    assert R.is_clerical("C.01") and not R.is_clerical("C")
    assert R.parse_rev("ab.2") == ("AB", 2)

def test_dates():
    import datetime
    assert R.to_ddmmyy("2026-10-17") == "17/10/26"
    assert R.to_ddmmyy("7/3/2026") == "07/03/26"
    assert R.to_ddmmyy(datetime.date(2026, 1, 2)) == "02/01/26"
    with pytest.raises(ValueError): R.to_ddmmyy("Oct 17")

def test_table_rows(tmp_path):
    p = tmp_path / "REVLOG.md"
    p.write_text("| Rev | Description | By | Date |\n|---|---|---|---|\n"
                 "| A | first cut | DG | 2026-10-01 |\n| B | b | DG | 02/10/26 |\n| B.01 | note typo | DG | 03/10/26 |\n"
                 "| C | c | DG | 04/10/26 |\n| D | d | DG | 05/10/26 |\n| E | e | DG | 06/10/26 |\n| F | f | DG | 07/10/26 |\n"
                 "| G | g1 | DG | 08/10/26 |\n| G | g final | JD | 09/10/26 |\n")
    e = R.read_revlog(str(p))
    rows = R.table_rows(e, max_rows=100)
    assert [r.rev for r in rows] == list("ABCDEFG")          # clerical dropped, one row per letter
    assert rows[0].desc == "Initial" and rows[0].date == "01/10/26"
    assert rows[-1].desc == "g final" and rows[-1].by == "JD"
    rows6 = R.table_rows(e, max_rows=6)
    assert [r.rev for r in rows6] == list("BCDEFG")          # oldest dropped first
    R.check_letter_matches("G.02", rows6)
    with pytest.raises(ValueError): R.check_letter_matches("H", rows6)

def test_add_release(tmp_path):
    p = str(tmp_path / "REVLOG.md")
    R.add_release(p, "A", "whatever", "DG", "2026-10-14", title="TEST")
    R.add_release(p, "B", "first edit", "DG", "2026-10-15")
    R.add_release(p, "B", "first edit + second edit, same PR", "DG", "2026-10-15")   # same release: updated, not added
    with pytest.raises(ValueError): R.add_release(p, "B.01", "clerical", "DG")
    with pytest.raises(ValueError): R.add_release(p, "A", "going backwards", "DG")
    e = R.read_revlog(p)
    assert [(x.rev, x.desc) for x in e] == [("A", "Initial"), ("B", "first edit + second edit, same PR")]

def test_find_revlog(tmp_path):
    a = tmp_path / "multi"; a.mkdir()
    (a / "foot.step").write_text("x"); (a / "strut.step").write_text("x")
    (a / "REVLOG.md").write_text("| A | Initial | DG | 01/10/26 |\n")
    assert R.find_revlog(str(a / "foot.step")) is None             # shared folder: plain REVLOG.md is ambiguous
    (a / "foot.REVLOG.md").write_text("| A | Initial | DG | 01/10/26 |\n")
    assert R.find_revlog(str(a / "foot.step")).endswith("foot.REVLOG.md")
    (a / "PN-103.REVLOG.md").write_text("| A | Initial | DG | 01/10/26 |\n")
    assert R.find_revlog(str(a / "strut.step"), pn="PN-103").endswith("PN-103.REVLOG.md")
    b = tmp_path / "single"; b.mkdir(); (b / "base.step").write_text("x"); (b / "REVLOG.md").write_text("")
    assert R.find_revlog(str(b / "base.step")).endswith("REVLOG.md")
