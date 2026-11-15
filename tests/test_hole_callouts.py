"""Hole and thread callouts: actual depths, THRU, 1.5D/2D as flags only."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'drawing'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build123d import *
import part as P

M4 = {3.3: ('M4x0.7', 0.7)}

def _box_hole(*, size_z, hole_d, hole_len, through):
    b = Box(20, 20, size_z, align=(Align.MIN, Align.MIN, Align.MIN))
    if through:
        cyl = Cylinder(hole_d/2, size_z+4, align=(Align.CENTER, Align.CENTER, Align.MIN))
        cyl = cyl.locate(Location((10, 10, -2)))
    else:
        cyl = Cylinder(hole_d/2, hole_len, align=(Align.CENTER, Align.CENTER, Align.MAX))
        cyl = cyl.locate(Location((10, 10, size_z)))
    return b - cyl

def _texts(groups):
    return [txt for (ax, txt) in groups]

def test_thread_major_mm():
    assert P._thread_major_mm('M4x0.7', 3.3, 3.3) == 4.0
    assert P._thread_major_mm('M6x1.0', 5.0, 5.0) == 6.0

def test_blind_tap_shallower_than_1_5D_actual_depth_flagged():
    # M4 major 4, 1.5xD=6; thread 4, hole 8 — call out both, flag in check only
    solid = _box_hole(size_z=20, hole_d=3.3, hole_len=8, through=False)
    spec = dict(threads=M4, thread_depth={3.3: 4.0})
    groups, rgroups, flags = P.hole_callouts(solid, 'machined', spec)
    texts = _texts(groups)
    assert len(texts) == 1
    t = texts[0]
    assert 'M4x0.7-6H ↧4' in t
    assert '⌀3.3 ↧8' in t
    assert 'THRU' not in t
    kinds = [f['kind'] for f in flags]
    assert 'thread_under_1_5D' in kinds

def test_blind_hole_deeper_than_thread_calls_out_both():
    # thread at the 1.5xD target (6), hole 8 — both depths, no engagement flag
    solid = _box_hole(size_z=20, hole_d=3.3, hole_len=8, through=False)
    spec = dict(threads=M4, thread_depth={3.3: 6.0})
    groups, rgroups, flags = P.hole_callouts(solid, 'machined', spec)
    t = _texts(groups)[0]
    assert 'M4x0.7-6H ↧6' in t
    assert '⌀3.3 ↧8' in t
    assert 'THRU' not in t
    assert not any(f['kind'] == 'thread_under_1_5D' for f in flags)

def test_through_tapped_is_thru_no_depth():
    solid = _box_hole(size_z=10, hole_d=3.3, hole_len=10, through=True)
    # thread_depth, if present, must not appear on a through callout
    spec = dict(threads=M4, thread_depth={3.3: 6.0})
    groups, rgroups, flags = P.hole_callouts(solid, 'machined', spec)
    t = _texts(groups)[0]
    assert 'M4x0.7-6H THRU' in t
    assert '↧' not in t

def test_through_plain_is_thru_no_depth():
    solid = _box_hole(size_z=10, hole_d=6.6, hole_len=10, through=True)
    spec = dict(threads={6.6: 'plain'})
    groups, rgroups, flags = P.hole_callouts(solid, 'machined', spec)
    t = _texts(groups)[0]
    assert '⌀6.6 THRU' in t
    assert '↧' not in t

def test_missing_thread_depth_not_invented():
    solid = _box_hole(size_z=20, hole_d=3.3, hole_len=8, through=False)
    spec = dict(threads=M4)
    groups, rgroups, flags = P.hole_callouts(solid, 'machined', spec)
    t = _texts(groups)[0]
    assert 'M4x0.7-6H' in t
    # must not invent the 1.5xD target of 6
    assert '↧6' not in t
    assert 'M4x0.7-6H ↧' not in t
    assert '⌀3.3 ↧8' in t
    assert any(f['kind'] == 'missing_thread_depth' for f in flags)

def test_over_2D_still_called_out_not_flagged():
    # 2xD=8; thread 10, hole 12 — actual depths on the drawing; never a flag
    solid = _box_hole(size_z=20, hole_d=3.3, hole_len=12, through=False)
    spec = dict(threads=M4, thread_depth={3.3: 10.0})
    groups, rgroups, flags = P.hole_callouts(solid, 'machined', spec)
    t = _texts(groups)[0]
    assert 'M4x0.7-6H ↧10' in t
    assert '⌀3.3 ↧12' in t
    kinds = [f['kind'] for f in flags]
    assert 'thread_over_2D' not in kinds
    assert 'thread_under_1_5D' not in kinds
