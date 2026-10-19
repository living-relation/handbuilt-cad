import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "drawing"))
import revs as R, dwg as D

LONG = "Lug machined integral with the flange (N6 option 2), M5 screws + dowels deleted; first drawing issued (#279)"

def _texts(sh): return [it[3] for it in sh.items if it[0] == "tx"]

def test_long_text_wraps_never_truncates():
    rows = [R.RevEntry("A", "Initial", "DG", "14/10/26"), R.RevEntry("G", LONG, "DG", "17/10/26")]
    sh = D.Sheet(); x0, y0, x1, y1 = D.revlog_table(sh, rows)
    tx = _texts(sh)
    assert not any("..." in t for t in tx)
    assert " ".join(tx).replace("  ", " ").count("dowels") == 1
    assert round(x1 - x0, 6) == sum(D.REVLOG_COLS) and x1 == D.PW - 10 and y1 == D.PH - 10
    assert (y1 - y0) > D.REVLOG_RH * 4          # the long row grew
    assert D.revlog_rect(rows) == (x0, y0, x1, y1)

def test_cap_counts_releases_and_font_shrinks_before_growing():
    rows = [R.RevEntry(l, LONG * 2, "DG", "17/10/26") for l in "BCDEFG"]
    cells, hts, (hd, ho), tot = D.revlog_layout(rows)
    assert len(cells) == 6
    assert hd < D.REVLOG_H[0]                    # shrank
    assert tot <= D.REVLOG_MAX_H or hd == D.REVLOG_HMIN

def test_short_rows_keep_old_height():
    rows = [R.RevEntry("A", "Initial", "DG", "17/10/26")]
    assert D.revlog_rect(rows)[1] == D.PH - 10 - 3 * D.REVLOG_RH
