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


# --- detection settings (snap, despike, sliver, graze, skin, allow boxes) ---

def _mesh(tmp_path, shape, name):
    bd = pytest.importorskip("build123d")
    import trimesh
    p = tmp_path / (name + ".stl")
    bd.export_stl(shape, str(p))
    return trimesh.load(p, force="mesh")


def test_detection_defaults_and_overrides():
    pytest.importorskip("trimesh"); pytest.importorskip("shapely")
    import check_printed_walls as CPW
    o = CPW.opts_from({})
    assert o["snap"] == 1e-4 and o["despike"] == 0.02 and o["sliver"] == 0.01 and o["graze"] == 4 and o["skin"] == 1.5
    o = CPW.opts_from({"skin": 0, "graze_sections": 0, "step": 1.0})
    assert o["skin"] == 0 and o["graze"] == 0 and o["step"] == 1.0
    assert "min_wall" not in o                                       # no wall default hides in the detection settings


def test_section_of_a_box_is_its_rectangle(tmp_path):
    pytest.importorskip("scipy")
    bd = pytest.importorskip("build123d")
    import check_printed_walls as CPW
    m = _mesh(tmp_path, bd.Pos(10, 5, 2) * bd.Box(20, 10, 4), "box")
    for snap, despike in ((1e-4, 0.02), (0, 0)):
        reg = CPW.section(m, 2, 2.0, snap, despike)
        assert abs(reg.area - 200.0) < 0.5


def test_allow_boxes_drop_spots_and_count_them(tmp_path):
    pytest.importorskip("scipy")
    bd = pytest.importorskip("build123d")
    import check_printed_walls as CPW
    # 30 x 20 plate, 1.0 mm thick: thin everywhere
    m = _mesh(tmp_path, bd.Pos(15, 10, 0.5) * bd.Box(30, 20, 1.0), "plate")
    assert CPW.walls(m, 1.95, 0.5)                                   # found
    assert CPW.walls(m, 1.95, opts={"step": 0.5}) == CPW.walls(m, 1.95, 0.5)   # opts['step'] is used when step isn't given
    seen = {}
    assert CPW.walls(m, 1.95, 0.5, allow=[("plate by design", [-1, 31, -1, 21, -1, 2])], seen=seen) == []
    assert seen.get("plate by design", 0) > 0


def test_skin_setting_separates_cantilevers_from_sloped_skin(tmp_path):
    pytest.importorskip("scipy"); pytest.importorskip("PIL")
    bd = pytest.importorskip("build123d")
    import check_printed_walls as CPW
    block = bd.Pos(5, 5, 5) * bd.Box(10, 10, 10)
    fin = bd.Pos(13, 5, 5) * bd.Box(6, 1.0, 6)                       # 1 mm fin standing 6 mm out of one face: a cantilever
    m = _mesh(tmp_path, block + fin, "fin")
    for skin in (0, 1.5):
        st = {}
        at = CPW.attachments(m, 3.0, 0.2, dict(skin=skin), st)
        assert any("cantilever" in a[0] and a[2] > 12 for a in at), (skin, at)
    stub = bd.Pos(10.5, 5, 5) * bd.Box(1.0, 1.0, 6)                  # 1 x 1 stub only ~0.5 mm proud: skin, not a cantilever
    m2 = _mesh(tmp_path, block + stub, "stub")
    st = {}
    at = CPW.attachments(m2, 3.0, 0.2, dict(skin=1.5), st)
    assert not any("cantilever" in a[0] for a in at) and st["skin"] >= 1
    at0 = CPW.attachments(m2, 3.0, 0.2, dict(skin=0), {})
    assert any("cantilever" in a[0] for a in at0)                    # skin = 0: the old behaviour lists it


# --- synthetic thin-wall case under every detection-flag combination ---
def _thin_and_thick(tmp_path, bd):
    """30 x 20 x 10 block (thick) with a 1.0 mm wall standing up from it (thin, 12 mm tall)."""
    block = bd.Pos(15, 10, 5) * bd.Box(30, 20, 10)
    wall = bd.Pos(15, 10, 16) * bd.Box(20, 1.0, 12)
    return _mesh(tmp_path, block + wall, "thinwall")


@pytest.mark.parametrize("snap", [0, 1e-4])
@pytest.mark.parametrize("despike", [0, 0.02])
@pytest.mark.parametrize("sliver", [0, 0.01])
@pytest.mark.parametrize("graze", [0, 4])
def test_thin_wall_found_under_every_flag_combination(tmp_path, snap, despike, sliver, graze):
    pytest.importorskip("scipy")
    bd = pytest.importorskip("build123d")
    import check_printed_walls as CPW
    m = _thin_and_thick(tmp_path, bd)
    o = dict(snap=snap, despike=despike, sliver=sliver, graze=graze)
    w = CPW.walls(m, 1.95, 0.5, opts=o)
    assert w, o                                                      # the 1.0 mm wall is found
    assert all(g[4] >= 9.0 for g in w), (o, w)                       # every spot is on the wall (z >= 10), none in the block
    assert any(g[2] <= 10 <= g[3] and g[5] >= 20 for g in w), (o, w)  # one spot spans the wall's height
    assert not CPW.walls(m, 0.9, 0.5, opts=o), o                     # a 1.0 mm wall passes a 0.9 mm minimum


def test_classify_resorts_the_report_without_detection(tmp_path, monkeypatch, capsys):
    pytest.importorskip("scipy")
    bd = pytest.importorskip("build123d")
    import check_printed_walls as CPW
    _thin_and_thick(tmp_path, bd)                                    # writes thinwall.stl next to the config
    conf = dict(min_wall=1.95, output="wc.json", parts=[dict(name="P", file="thinwall.stl")])
    p = tmp_path / "walls.json"
    p.write_text(json.dumps(conf))
    assert CPW.main(["--config", str(p)]) == 0                       # unplaced thin spot: flagged, not failed
    r = json.loads((tmp_path / "wc.json").read_text())["parts"]["P"]
    assert r["flag"] >= 1 and r["approved"] == 0
    conf["parts"][0]["exempt"] = [dict(why="thin by design", approved="2026-10-21", box=[-1, 31, -1, 21, 9, 23])]
    p.write_text(json.dumps(conf))
    monkeypatch.setattr(CPW, "walls", lambda *a, **k: pytest.fail("--classify must not re-run detection"))
    assert CPW.main(["--config", str(p), "--classify"]) == 0
    r2 = json.loads((tmp_path / "wc.json").read_text())["parts"]["P"]
    assert r2["approved"] == r["flag"] and r2["flag"] == 0
    conf["parts"].append(dict(name="Q", file="thinwall.stl"))         # a part the report doesn't have
    p.write_text(json.dumps(conf))
    capsys.readouterr()
    assert CPW.main(["--config", str(p), "--classify"]) == 0
    assert "Q is not in the report" in capsys.readouterr().err
    assert CPW.main(["--config", str(tmp_path / "missing.json"), "--classify"]) == 2
    (tmp_path / "wc.json").unlink()                                   # config fine, no report yet
    capsys.readouterr()
    assert CPW.main(["--config", str(p), "--classify"]) == 2
    assert "needs an existing report" in capsys.readouterr().err
