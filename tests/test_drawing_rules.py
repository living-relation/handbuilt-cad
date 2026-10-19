"""Drawing rules added 2026-10-18 (DRAWING-RULES 16a, 24-29): tangent edges in trimetric views, dotted exploded-view
lines, balloons only on clearly visible parts with no overlap or crowding, note labels next to balloons, wire labels,
and the <pdf>.checks.json report."""
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "drawing"))
from build123d import Box, Cylinder, Location, fillet, Axis  # noqa: E402
import dwg  # noqa: E402
import asm  # noqa: E402


def rounded_block():
    b = Box(40, 30, 10)
    return fillet(b.edges().filter_by(Axis.Z), 4)


def test_tangent_edges_only_in_pictorial_views():
    s = rounded_block()
    iso = dwg.View(s, "iso", 1.0)
    top = dwg.View(s, "top", 1.0)
    front = dwg.View(s, "front", 1.0)
    assert dwg.is_pictorial("iso") and not dwg.is_pictorial("top")
    assert len(iso.tan) >= 4             # the 4 vertical blends meet the flat sides: drawn in the trimetric
    assert top.tan == [] and front.tan == []
    # front view of a round-cornered block: the blend lines are not drawn as edges there either
    vis, _, _ = dwg.project(s, "front")
    assert len(vis) == len(front.vis)


def test_tangent_lines_drawn_thin():
    sh = dwg.Sheet()
    v = dwg.View(rounded_block(), "iso", 1.0).place(100, 100)
    v.draw(sh)
    stys = {it[2] for it in sh.items if it[0] == "pl"}
    assert {"vis", "tan"} <= stys
    assert dwg.STY["tan"][0] < dwg.STY["vis"][0]


def test_explode_lines_are_dotted():
    lw, dash = dwg.STY["expl"]
    assert dash is not None and dash[0] < 1.0   # short dots, not dashes
    assert dwg.DXF_LAYER["expl"][1] == "DOT"


def test_occluder_ray_test():
    front = Box(20, 2, 20).moved(Location((0, -20, 0)))   # between the camera (front = -Y) and the back block
    back = Box(10, 10, 10)
    occ = asm.Occluder([front, back])
    cam = np.array(dwg.VIEWDIR["front"][0], float)
    assert occ.hidden((0, -5, 0), cam)                      # front face of the back block: behind the plate
    assert not occ.hidden((0, -21.0, 0), cam)                # on the plate's own front face


def _items():
    base = Box(80, 60, 4).moved(Location((0, 0, 2)))
    cover = Box(80, 60, 20).moved(Location((0, 0, 14)))
    inner = Cylinder(4, 6).moved(Location((0, 0, 7)))        # fully inside the cover
    return [
        dict(item=1, qty=1, pn="P-1", desc="BASE", shapes=[base], primary=True),
        dict(item=2, qty=1, pn="P-2", desc="COVER", shapes=[cover], primary=True),
        dict(item=3, qty=1, pn="P-3", desc="INNER PART", shapes=[inner]),
    ]


def test_hidden_part_not_ballooned_and_reported(tmp_path):
    spec = dict(title="T", pn="T-100", items=_items(), notes=["ONE NOTE"], tol="DIMENSIONS ARE IN MILLIMETERS")
    out = str(tmp_path / "t.pdf")
    rep = asm.make_assembly(spec, out)
    assert os.path.exists(str(tmp_path / "t.checks.json"))
    d = json.load(open(tmp_path / "t.checks.json"))
    assert d["notes"] == ["ONE NOTE"] and d["tol_block"] == "DIMENSIONS ARE IN MILLIMETERS"
    assert d["not_ballooned"] == ["3"]        # inside the cover: never ballooned in the assembled view
    assert d["ok"] is False and rep["ok"] is False


def test_exploded_view_balloons_the_hidden_part(tmp_path):
    spec = dict(title="T", pn="T-101", items=_items(),
                exploded=dict(label="EXPLODED VIEW", move=[(2, (0, 0, 60)), (3, (0, 0, 35))]))
    rep = asm.make_assembly(spec, str(tmp_path / "t.pdf"))
    assert rep["not_ballooned"] == []
    assert rep["ok"] is True
    ex = [v for v in rep["balloon_views"] if v["view"] == "EXPLODED VIEW"][0]
    assert ex["placed"] >= 1 and ex["overlaps"] == 0


def test_primary_only_in_assembled_view():
    items = _items()
    sel = asm._iso_selection({}, items, "assembled")
    assert [it["item"] for it in sel] == [1, 2]
    sel = asm._iso_selection({"iso_balloons": {"assembled": [2]}}, items, "assembled")
    assert [it["item"] for it in sel] == [2]


def test_balloons_never_overlap_when_crowded():
    sh = dwg.Sheet()
    v = dwg.View(Box(30, 30, 30), "iso", 1.0).place(200, 140)
    anchors = [(i, np.array([200 + 0.3 * i, 140.0])) for i in range(1, 40)]    # 39 tips on one spot
    log = asm.BalloonLog(); log.view("x")
    out = asm.place_balloons(sh, v, anchors, None, margin=9, log=log)
    C = np.array([c for _, c, _ in out])
    d = np.linalg.norm(C[:, None] - C[None], axis=2) + np.eye(len(C)) * 1e9
    assert d.min() >= 2 * 4.0                 # balloon radius 4: circles never touch
    assert log.views[0]["overlaps"] == 0


def test_choose_anchors_spreads_tips():
    c = {1: np.array([[0, 0], [10, 0], [20, 0.]]), 2: np.array([[0, 0.5], [20, 0.5]])}
    a = asm.choose_anchors(c)
    assert np.linalg.norm(a[1] - a[2]) >= asm.TIP_MIN_SEP


def test_label_sheet_notes_and_wire_labels(tmp_path):
    items = _items()
    fuse = Box(6, 3, 8).moved(Location((-20, 0, 8)))
    relay = Box(12, 12, 12).moved(Location((20, 10, 10)))
    items += [dict(item=4, qty=2, pn="F", desc="FUSE", shapes=[fuse, fuse.moved(Location((10, 0, 0)))]),
              dict(item=5, qty=1, pn="K", desc="RELAY", shapes=[relay])]
    spec = dict(title="T", pn="T-102", items=items, open_hide=[2],
                label_views=[dict(title="FUSE, RELAY AND WIRE LABELS", view="top", hide=[2],
                                  labels=[dict(item=4, index=0, text="F1 IGN 1"), dict(item=4, index=1, text="F2 FAN"),
                                          dict(item=5, index=0, text="K1 FUEL PUMP RELAY")],
                                  wires=[dict(at=(30, -20, 4), text="Fuel pump relay 87 - pump +12 V")])])
    out = str(tmp_path / "t.pdf")
    rep = asm.make_assembly(spec, out)
    lab = [v for v in rep["balloon_views"] if v["view"].startswith("LABELS")][0]
    assert lab["hidden"] == [] and lab["placed"] == 3 and lab["overlaps"] == 0


def test_part_drawing_with_step_sheet(tmp_path):
    """DRAWING-RULES 31: a part drawing keeps its shop sheet and gains install-step sheets (exploded, dotted lines, balloons + notes)."""
    import part
    from build123d import export_step
    plate = Box(40, 20, 3)
    step = str(tmp_path / 'p.step')
    export_step(plate, step)
    nut = Cylinder(3, 4).moved(Location((10, 0, 3.5)))
    items = [dict(item=1, desc='STRAP', shapes=[plate.moved(Location((0, 0, 1.5)))]), dict(item=2, desc='PEM NUT', shapes=[nut])]
    spec = dict(file=step, pn='T-117', title='T', material='C110', process='machined', notes=['ONE NOTE.'],
                stage_items=items, stage_notes={2: 'PRESS FROM THIS SIDE'},
                stage_sheets=[[dict(no=1, title='PRESS THE NUT IN', base=[1], move=[(2, (0, 0, 25))])]])
    out = str(tmp_path / 't.pdf')
    part.make_part(spec, out, None, str(tmp_path / 'pv'))
    assert os.path.exists(str(tmp_path / 'pv_sh2.png'))
    d = json.load(open(tmp_path / 't.checks.json'))
    assert d['not_ballooned'] == [] and d['ok'] is True
    assert [v['view'] for v in d['balloon_views']] == ['STEP 1']


def test_wire_label_anchored_on_its_terminal(tmp_path):
    items = _items()
    term = Box(3, 3, 6).moved(Location((25, 0, 3)))
    items[0]['shapes'] = [Box(80, 60, 4).moved(Location((0, 0, -2)))]
    items.append(dict(item=4, qty=1, pn='T', desc='TERMINAL', shapes=[term]))
    spec = dict(title='T', pn='T-103', items=items, open_hide=[2],
                label_views=[dict(view='top', hide=[2, 3], text_h=1.8,
                                  wires=[dict(item=4, at=(25, 0, 6), text='BUS2-12 > Bulkhead A pin 42 (DRB102, RH firewall) - EHPS pump logic enable (pump pin C1)')])])
    rep = asm.make_assembly(spec, str(tmp_path / 't.pdf'))
    lab = [v for v in rep['balloon_views'] if v['view'].startswith('LABELS')][0]
    assert lab['hidden'] == []
