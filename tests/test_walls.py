"""Structural-only minimum wall: config-driven classes and exemptions (wall_classes) and the config-driven checker."""
import json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "checks"))
import wall_classes as WC

PART = dict(name="P", features=[dict(**{"class": "structural"}, why="mount ear", box=[0, 10, 0, 10, 0, 10]),
                                dict(**{"class": "non-structural"}, why="cable rib", box=[40, 44, 10, 30, 0, 12])],
            exempt=[dict(why="snap barb by design", approved="2026-10-17", box=[70, 74, 20, 24, 10, 14])])


def cfg(**kw):
    c = dict(min_wall=2.0, attach_min=3.0, parts=[PART], classes=dict(outer_band=4.5))
    c.update(kw)
    return WC.normalise(c)


BOUNDS = [0, 100, 0, 60, 0, 20]


def test_min_wall_required():
    with pytest.raises(WC.ConfigError, match="min_wall"):
        WC.normalise(dict(parts=[PART]))
    with pytest.raises(WC.ConfigError):
        WC.normalise(dict(min_wall=0, parts=[PART]))


def test_structural_box_fails():
    c, why = WC.classify([2, 4, 2, 4, 2, 4], "W", PART, cfg(), BOUNDS)
    assert c == "structural" and WC.verdict(c, cfg()) == "fail" and "mount ear" in why


def test_non_structural_box_is_flagged_not_failed():
    c, _ = WC.classify([41, 43, 15, 20, 2, 4], "W", PART, cfg(), BOUNDS)
    assert c == "non-structural" and WC.verdict(c, cfg()) == "flag"


def test_unplaced_spot_is_questionable_flag():
    c, why = WC.classify([50, 52, 28, 30, 5, 6], "W", PART, cfg(), BOUNDS)
    assert c == "questionable" and WC.verdict(c, cfg()) == "flag" and "approve" in why


def test_outer_band_is_structural_and_optional():
    spot = [50, 52, 1, 2, 5, 6]                                      # 1 mm from the y = 0 edge
    assert WC.classify(spot, "W", PART, cfg(), BOUNDS)[0] == "structural"
    nob = cfg(classes=dict(outer_band=None))
    assert WC.classify(spot, "W", PART, nob, BOUNDS)[0] == "questionable"


def test_attachment_uses_attach_class():
    c, _ = WC.classify([50, 52, 28, 30, 5, 6], "A", PART, cfg(), BOUNDS)
    assert c == "structural"
    c2, _ = WC.classify([50, 52, 28, 30, 5, 6], "A", PART, cfg(classes=dict(attach_class="questionable")), BOUNDS)
    assert c2 == "questionable"


def test_exemption_wins_and_is_not_reflagged():
    c, why = WC.classify([71, 73, 21, 23, 11, 13], "W", PART, cfg(), BOUNDS)
    assert c == WC.APPROVED and WC.verdict(c, cfg()) == "approved" and "2026-10-17" in why
    # a spot that grows past the approved box is classified normally again (geometry changed -> re-check)
    assert WC.classify([69, 75, 21, 23, 11, 13], "W", PART, cfg(), BOUNDS)[0] != WC.APPROVED


def test_custom_classes_and_validation():
    c = cfg(classes=dict(fail=["structural", "critical", "sealing"], flag=["non-structural", "cosmetic", "questionable"]))
    assert WC.verdict("sealing", c) == "fail" and WC.verdict("cosmetic", c) == "flag"
    bad = dict(PART, features=[dict(**{"class": "made-up"}, box=[0, 1, 0, 1, 0, 1])])
    with pytest.raises(WC.ConfigError, match="made-up"):
        WC.normalise(dict(min_wall=2.0, parts=[bad]))
    with pytest.raises(WC.ConfigError, match="both"):
        WC.normalise(dict(min_wall=2.0, parts=[PART], classes=dict(fail=["x"], flag=["x"], attach_class="x", default="x")))
    with pytest.raises(WC.ConfigError, match="why"):
        WC.normalise(dict(min_wall=2.0, parts=[dict(name="Q", exempt=[dict(box=[0, 1, 0, 1, 0, 1])])]))


def test_example_config_loads():
    c = WC.load_config(os.path.join(os.path.dirname(__file__), "..", "tools", "checks", "walls.example.toml"))
    assert c["min_wall"] == 2.0 and len(c["parts"]) == 2 and c["classes"]["fail"] == ["structural", "critical"]


def test_checker_end_to_end(tmp_path):
    pytest.importorskip("trimesh"); pytest.importorskip("shapely"); pytest.importorskip("scipy"); pytest.importorskip("PIL")
    bd = pytest.importorskip("build123d")
    import check_printed_walls as CPW
    # 40 x 30 x 10 tray: 3 mm outer walls and floor, plus a 1.2 mm internal rib across the middle (x = 20)
    tray = bd.Pos(20, 15, 5) * bd.Box(40, 30, 10) - bd.Pos(20, 15, 8) * bd.Box(34, 24, 10)
    tray = tray + bd.Pos(20, 15, 6.5) * bd.Box(1.2, 24, 7)
    bd.export_stl(tray, str(tmp_path / "tray.stl"))
    conf = tmp_path / "walls.toml"
    conf.write_text('min_wall = 2.0\noutput = "out.json"\nflags_md = "FLAGS.md"\n'
                    '[classes]\nouter_band = 1.0\n'
                    '[[parts]]\nname = "Tray"\nfile = "tray.stl"\n')
    assert CPW.main(["--config", str(conf)]) == 0                    # rib is not placed -> flagged, not failed
    r = json.load(open(tmp_path / "out.json"))["parts"]["Tray"]
    assert r["fail"] == 0 and r["flag"] >= 1
    assert "questionable" in (tmp_path / "FLAGS.md").read_text().lower()
    # the user marks the rib structural -> it fails
    conf.write_text(conf.read_text() + '[[parts.features]]\nclass = "structural"\nwhy = "load rib"\nbox = [19, 21, 0, 30, 0, 10]\n')
    assert CPW.main(["--config", str(conf)]) == 1
    # the user approves it instead -> approved, no fail, no flag
    conf.write_text('min_wall = 2.0\noutput = "out.json"\n[classes]\nouter_band = 1.0\n[[parts]]\nname = "Tray"\nfile = "tray.stl"\n'
                    '[[parts.exempt]]\nwhy = "rib OK at 1.2"\napproved = "2026-10-17"\nbox = [18, 22, -1, 31, -1, 11]\n')
    assert CPW.main(["--config", str(conf)]) == 0
    r = json.load(open(tmp_path / "out.json"))["parts"]["Tray"]
    assert r["fail"] == 0 and r["flag"] == 0 and r["approved"] >= 1


def test_missing_config_value_exit_2(tmp_path):
    pytest.importorskip("trimesh"); pytest.importorskip("shapely")
    import check_printed_walls as CPW
    conf = tmp_path / "w.toml"
    conf.write_text('[[parts]]\nname = "X"\n')
    assert CPW.main(["--config", str(conf)]) == 2
