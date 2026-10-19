"""Revision triangles (DRAWING-RULES 33): declared per rev, accumulate by default, placed on free spots, counted in the checks report."""
import json
import os
import sys

import pytest
from build123d import Box, Location

_d = os.path.join(os.path.dirname(__file__), '..', 'drawing')
sys.path.insert(0, _d)
import asm  # noqa: E402
import dwg  # noqa: E402
import revmarks as RM  # noqa: E402


def M(rev, **k):
    return dict(rev=rev, **k)


def test_accumulate_default_keeps_old_letters():
    marks = [M('B', item=1), M('C', item=2), M('D', item=3)]
    assert RM.ACCUMULATE_DEFAULT is True
    assert [m['rev'] for m in RM.select(marks, 'C')] == ['B', 'C']            # D is newer than the drawing: ignored
    assert [m['rev'] for m in RM.select(marks, 'C.01')] == ['B', 'C']         # a clerical rev draws its letter's marks
    assert [m['rev'] for m in RM.select(marks, 'C', accumulate=False)] == ['C']


def test_load_file_and_spec_and_setting(tmp_path):
    log = tmp_path / 'T-1.REVLOG.md'
    log.write_text('| Rev | Description | By | Date |\n|---|---|---|---|\n| A | Initial | DG | 19/10/26 |\n')
    (tmp_path / 'T-1.REVMARKS.json').write_text(json.dumps({'accumulate': False, 'marks': [M('B', item=1)]}))
    marks, acc = RM.load(dict(pn='T-1', rev_marks=[M('C', bom=2)]), str(log))
    assert [m['rev'] for m in marks] == ['B', 'C'] and acc is False
    _, acc = RM.load(dict(pn='T-1', rev_marks_accumulate=True), str(log))
    assert acc is True                                                          # the spec overrides the file
    _, acc = RM.load(dict(pn='T-2'), None)
    assert acc is True                                                          # default
    with pytest.raises(ValueError):
        RM.load(dict(pn='T-1', rev_marks=[M('C.01', item=1)]), None)            # clerical revs never get a triangle
    with pytest.raises(ValueError):
        RM.load(dict(pn='T-1', rev_marks=[M('C')]), None)                       # nothing to point at


def _sheet():
    sh = dwg.Sheet()
    sh.pl([(100, 100), (200, 100), (200, 160), (100, 160)], 'vis', closed=True)          # a part outline
    sh.circle((150, 175), 4.0, 'tb')
    sh.txt(150, 175, '5', h=3.2)
    sh.anch['balloon'][5] = [((150, 175), 4.0)]
    sh.anch['bom'][5] = (300, 200, 400, 208)
    sh.pl([(300, 200), (400, 200), (400, 208), (300, 208)], 'thin', closed=True)
    sh.anch['note'][2] = (20, 60, 100, 66)
    return sh


def _clear(sh, rect, polys):
    from shapely.geometry import Polygon
    return True


def test_triangle_is_near_its_anchor_and_touches_nothing():
    sh = _sheet()
    n0 = len(sh.items)
    rep = RM.apply(dict(pn='T', rev_marks=[M('B', item=5), M('B', bom=5), M('B', note=2), M('B', page=[150, 130])]), [sh], 'B')
    assert rep['rev_marks'] == {'B': 4} and rep['rev_marks_unplaced'] == []
    assert len(sh.items) > n0
    obs = RM._Obstacles(dwg.Sheet(), dwg.PW, dwg.PH)
    # every drawn triangle (a closed 'dim' polygon with 3 corners) stays clear of the part outline and the balloon ring
    from shapely.geometry import LineString, Polygon
    tris = [Polygon(map(tuple, it[1])) for it in sh.items if it[0] == 'pl' and it[2] == 'dim' and it[3] and len(it[1]) == 3]
    assert len(tris) == 4
    outline = LineString([(100, 100), (200, 100), (200, 160), (100, 160), (100, 100)])
    ring = LineString([(150 + 4 * __import__('math').cos(t / 10), 175 + 4 * __import__('math').sin(t / 10)) for t in range(64)])
    for t in tris:
        assert not t.intersects(outline) and not t.intersects(ring)
    assert not tris[0].intersects(tris[1]) and obs is not None
    # the balloon one sits within a short distance of the balloon, the BOM one left of the BOM row
    assert tris[0].distance(ring) < 12
    assert tris[1].centroid.x < 300


def test_no_free_spot_is_reported_not_drawn_on_top():
    sh = dwg.Sheet()
    for y in range(14, 284, 2):                                  # a sheet full of lines: nowhere to put a 6 mm triangle
        sh.pl([(13, y), (407, y)], 'vis')
    rep = RM.apply(dict(pn='T', rev_marks=[M('B', page=[200, 150])]), [sh], 'B')
    assert rep['rev_marks'] == {} and rep['rev_marks_unplaced'][0]['why'] == 'no free spot'


def test_missing_anchor_is_unplaced():
    sh = _sheet()
    rep = RM.apply(dict(pn='T', rev_marks=[M('B', item=99), M('B', bom=99), M('B', view='nope', at=[0, 0, 0])]), [sh], 'B')
    assert len(rep['rev_marks_unplaced']) == 3 and rep['rev_marks'] == {}


def test_clerical_rev_draws_current_letters_marks_only_for_that_letter():
    sh = _sheet()
    rep = RM.apply(dict(pn='T', rev_marks=[M('B', item=5)]), [sh], 'B.01')
    assert rep['rev_marks'] == {'B': 1}


def test_warning_for_a_full_letter_without_triangles(capsys):
    RM.warn_if_missing(dict(pn='T'), 'C', dict(rev_marks={}))
    assert 'rev C has no revision triangle' in capsys.readouterr().out
    RM.warn_if_missing(dict(pn='T'), 'A', dict(rev_marks={}))                              # a new drawing: nothing changed
    RM.warn_if_missing(dict(pn='T'), 'C.01', dict(rev_marks={'C': 1}))
    RM.warn_if_missing(dict(pn='T', rev_marks_exempt_through='C'), 'C', dict(rev_marks={}))   # before the rule
    RM.warn_if_missing(dict(pn='T', rev_marks_exempt_through='C'), 'D.01', dict(rev_marks={}))
    out = capsys.readouterr().out
    assert out.count('has no revision triangle') == 1 and 'rev D' in out


def test_assembly_drawing_gets_triangles_and_report(tmp_path):
    """End to end: balloon, BOM row and note marks land on sheet 1 and are counted in the checks report."""
    base = Box(80, 60, 4).moved(Location((0, 0, 2)))
    cover = Box(80, 60, 20).moved(Location((0, 0, 14)))
    items = [dict(item=1, qty=1, pn='P-1', desc='BASE', shapes=[base], primary=True),
             dict(item=2, qty=1, pn='P-2', desc='COVER', shapes=[cover], primary=True)]
    spec = dict(title='T', pn='T-300', items=items, notes=['ONE NOTE', 'TWO NOTE'], rev='C', rev_marks_exempt_through='C',
                revs=[('A', 'Initial', '2026-10-19', 'DG'), ('B', 'cover taller', '2026-10-19', 'DG'), ('C', 'base added', '2026-10-19', 'DG')],
                rev_marks=[M('B', item=2), M('C', item=1), M('C', bom=1), M('C', note=2)])
    out = str(tmp_path / 't.pdf')
    asm.make_assembly(spec, out)
    d = json.load(open(tmp_path / 't.checks.json'))
    assert d['rev_marks'] == {'B': 1, 'C': 3} and d['rev_marks_unplaced'] == [] and d['rev_marks_accumulate'] is True
    spec2 = dict(spec, pn='T-301', rev_marks_accumulate=False)
    asm.make_assembly(spec2, str(tmp_path / 't2.pdf'))
    d2 = json.load(open(tmp_path / 't2.checks.json'))
    assert d2['rev_marks'] == {'C': 3} and d2['rev_marks_accumulate'] is False
