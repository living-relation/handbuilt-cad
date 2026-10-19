"""Revision triangles: the rev letter inside a triangle, drawn next to every item that changed in a full-letter rev.

Rule (DRAWING-RULES 33): every full-letter revision puts a revision symbol next to each item on the drawing that changed; a changed
part number also gets one next to its BOM row. Clerical revs (C.01 ...) have none and are not in the rev log. Rev A (a new drawing)
has nothing that "changed", so it needs none.

Declaring what changed - `spec['rev_marks']` (a list) and/or `<part no>.REVMARKS.json` beside the rev log
(`{"accumulate": true, "marks": [...]}`; the file is where the history lives, so old marks survive later revs). One entry per place:

    {"rev": "C", "item": 5}                      the balloon of BOM item 5 (first one found; "all": true = every balloon)
    {"rev": "C", "bom": 5}                       the BOM row of item 5 (a changed part number)
    {"rev": "C", "note": 3}                      note 3 in the NOTES block
    {"rev": "C", "view": "front", "at": [x,y,z]} a model point (mm) as seen in that view (part drawings: front/top/right/iso;
                                                 assemblies: front/top/right/iso)
    {"rev": "C", "page": [x, y]}                 a page point (mm)
    optional on any: "sheet": 2 (default 1), "note_text": "free text for the record"

Old triangles accumulate by default (Dan N42 = B): when Rev C comes out the Rev B and older triangles stay on the sheet. Set
`spec['rev_marks_accumulate'] = False` (or `"accumulate": false` in the file) to show only the current letter's. Marks for a letter
newer than the drawing's rev are ignored.

Placement: the triangle goes in the nearest free spot round its anchor (preferred side first), where it touches no line, text, other
triangle, the frame or the title block. A mark that finds no free spot is reported in `unplaced`, never drawn on top of something.
`apply()` returns the report that goes into `<pdf>.checks.json`: `rev_marks` {letter: placed count}, `rev_marks_unplaced`,
`rev_marks_accumulate`.
"""
import json
import math
import os
import numpy as np
from shapely.geometry import LineString, Polygon, box as sbox
from shapely.strtree import STRtree

import revs as R

ACCUMULATE_DEFAULT = True      # Dan N42 = B (2026-10-19)
TRI = 6.4                      # triangle side, mm
GAP = 0.6                      # clear space round the triangle, mm
FRAME = (12.0, 12.0)           # keep this far inside the sheet edge
MARKS_SUFFIX = '.REVMARKS.json'
KEYS = ('item', 'bom', 'note', 'view', 'page')


def marks_path(revlog_path, pn):
    if not revlog_path or not os.path.isfile(revlog_path):
        return None
    return os.path.join(os.path.dirname(os.path.abspath(revlog_path)), f'{pn}{MARKS_SUFFIX}')


def load(spec, revlog_path=None):
    """(marks, accumulate): the file beside the rev log plus spec['rev_marks'], validated."""
    marks, acc = [], ACCUMULATE_DEFAULT
    p = marks_path(revlog_path, spec.get('pn'))
    if p and os.path.exists(p):
        d = json.load(open(p, encoding='utf-8'))
        marks += list(d.get('marks') or [])
        acc = bool(d.get('accumulate', acc))
    marks += list(spec.get('rev_marks') or [])
    acc = bool(spec.get('rev_marks_accumulate', acc))
    for m in marks:
        if not R.is_valid_letter(str(m.get('rev', ''))) or R.is_clerical(str(m['rev'])):
            raise ValueError(f"rev mark {m}: 'rev' must be a full rev letter (no clerical .NN)")
        if not any(k in m for k in KEYS):
            raise ValueError(f"rev mark {m}: needs one of {KEYS}")
    return marks, acc


def select(marks, rev, accumulate=ACCUMULATE_DEFAULT):
    """The marks to draw on a drawing at `rev`: this letter's and (accumulate) every older letter's; never a newer letter's."""
    cur = R.letter_to_index(R.base_letter(rev))
    out = []
    for m in marks:
        i = R.letter_to_index(str(m['rev']))
        if i == cur or (accumulate and i < cur):
            out.append(m)
    return out


def _text_poly(it):
    _, x, y, t, h, ha, va, rot, *_ = it
    w = max(len(l) for l in str(t).split('\n')) * h * 0.82
    H = (str(t).count('\n') + 1) * h * 1.6
    if rot == 90:
        w, H = H, w
        return sbox(x - w / 2, y if va == 'bottom' else y - H, x + w / 2, y + H if va == 'bottom' else y)
    x0 = {'left': x, 'right': x - w, 'center': x - w / 2}[ha]
    y0 = {'bottom': y, 'top': y - H, 'center': y - H / 2}[va]
    return sbox(x0, y0, x0 + w, y0 + H)


class _Obstacles:
    """Everything already on a sheet that a triangle must not touch: lines, text, arrowheads, the frame margin."""

    def __init__(self, sh, PW, PH):
        geoms = []
        for it in sh.items:
            if it[0] == 'pl':
                p = it[1]
                if len(p) >= 2:
                    pts = [tuple(q) for q in (np.vstack([p, p[:1]]) if it[3] else p)]
                    geoms.append(LineString(pts))
            elif it[0] == 'tx':
                geoms.append(_text_poly(it))
            elif it[0] == 'tri' and len(it[1]) >= 3:
                geoms.append(Polygon([tuple(q) for q in it[1]]))
        self.geoms = geoms
        self.tree = STRtree(geoms) if geoms else None
        self.placed = []
        self.PW, self.PH = PW, PH

    def free(self, poly):
        x0, y0, x1, y1 = poly.bounds
        if x0 < FRAME[0] or y0 < FRAME[1] or x1 > self.PW - FRAME[0] or y1 > self.PH - FRAME[1]:
            return False
        z = poly.buffer(GAP)
        if self.tree is not None:
            for i in self.tree.query(z):
                if z.intersects(self.geoms[int(i)]):
                    return False
        return not any(z.intersects(q) for q in self.placed)


def _tri_poly(cx, cy, side=TRI):
    """Equilateral, apex up, centred on its centroid."""
    h = side * math.sqrt(3) / 2
    return Polygon([(cx - side / 2, cy - h / 3), (cx + side / 2, cy - h / 3), (cx, cy + 2 * h / 3)])


def _dirs(pref):
    base = {'E': 0, 'NE': 45, 'N': 90, 'NW': 135, 'W': 180, 'SW': 225, 'S': 270, 'SE': 315}
    order = ['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']
    start = base.get(pref, 45)
    out = [start]                                   # the preferred side exactly, then fanning out either way
    for k in range(1, 9):
        out += [(start + 22 * k) % 360, (start - 22 * k) % 360]
    return out + [(start + 180) % 360]


def _find_spot(obs, anchor_rect, pref):
    """anchor_rect = (x0, y0, x1, y1) of the thing marked (a point is a zero-size rect). Nearest free triangle position."""
    x0, y0, x1, y1 = anchor_rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
    for d in np.arange(0.0, 40.0, 1.0):
        for a in _dirs(pref):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            # leave the anchor's own box, then walk d further out along the direction
            t = min(rx / abs(ca) if abs(ca) > 1e-9 else 1e9, ry / abs(sa) if abs(sa) > 1e-9 else 1e9)
            t = 0.0 if t > 1e8 else t
            r = t + TRI * 0.58 + GAP + d
            px, py = cx + ca * r, cy + sa * r
            poly = _tri_poly(px, py)
            if obs.free(poly):
                return px, py, poly
    return None


def _anchor(sh, m, views):
    """(anchor_rect, preferred side) of a mark on a sheet, or None when the item is not there."""
    an = getattr(sh, 'anch', {})
    if 'item' in m:
        found = an.get('balloon', {}).get(m['item']) or an.get('balloon', {}).get(str(m['item']))
        if not found:
            return None
        c, r = found[0]
        return (c[0] - r, c[1] - r, c[0] + r, c[1] + r), 'NE'
    if 'bom' in m:
        rc = an.get('bom', {}).get(m['bom']) or an.get('bom', {}).get(str(m['bom']))
        return (rc, 'W') if rc else None
    if 'note' in m:
        rc = an.get('note', {}).get(int(m['note']))
        return (rc, 'E') if rc else None
    if 'view' in m:
        v = views.get(m['view'])
        if v is None:
            return None
        p = v.P(m['at'])
        return (p[0], p[1], p[0], p[1]), 'NE'
    if 'page' in m:
        return (m['page'][0], m['page'][1], m['page'][0], m['page'][1]), 'NE'
    return None


def _draw(sh, poly, letter):
    pts = [tuple(q) for q in list(poly.exterior.coords)[:-1]]
    sh.pl(pts, 'dim', closed=True)
    c = poly.centroid
    sh.txt(c.x, c.y - 0.2, letter, h=2.4 if len(letter) == 1 else 1.9, bold=True)


def apply(spec, sheets, rev, revlog_path=None, PW=420.0, PH=297.0):
    """Draw the triangles for `rev` on `sheets`; returns the checks.json fields (see the module docstring)."""
    marks, acc = load(spec, revlog_path)
    rep = dict(rev_marks={}, rev_marks_unplaced=[], rev_marks_accumulate=acc)
    if not marks or not rev or rev in ('-', ''):
        return rep
    views_by_sheet = {}
    for i, sh in enumerate(sheets):
        views_by_sheet[i] = getattr(sh, 'anch', {}).get('view', {})
    obs = {}
    for m in select(marks, rev, acc):
        si = int(m.get('sheet', 1)) - 1
        if si >= len(sheets):
            rep['rev_marks_unplaced'].append(dict(m, why='no such sheet'))
            continue
        sh = sheets[si]
        ob = obs.get(si) or obs.setdefault(si, _Obstacles(sh, PW, PH))
        a = _anchor(sh, m, views_by_sheet[si])
        if a is None:
            rep['rev_marks_unplaced'].append(dict(m, why='anchor not on the sheet'))
            continue
        spot = _find_spot(ob, *a)
        if spot is None:
            rep['rev_marks_unplaced'].append(dict(m, why='no free spot'))
            continue
        _draw(sh, spot[2], str(m['rev']).upper())
        ob.placed.append(spot[2])
        rep['rev_marks'][str(m['rev']).upper()] = rep['rev_marks'].get(str(m['rev']).upper(), 0) + 1
    return rep


def warn_if_missing(spec, rev, rep):
    """Print a warning when a full-letter rev (not Rev A, not exempt) has no triangle at all."""
    if not rev or rev in ('-', ''):
        return
    L = R.base_letter(rev)
    if L == 'A':
        return
    ex = spec.get('rev_marks_exempt_through')
    if ex and R.letter_to_index(L) <= R.letter_to_index(ex):
        return
    if not rep['rev_marks'].get(L):
        print(f"WARNING: {spec.get('pn')}: rev {L} has no revision triangle (DRAWING-RULES 33): add rev_marks for what changed in {L}")
