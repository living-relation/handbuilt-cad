"""Fusion-side BOM work: read components, count them, write fields back. Separate from the UI for testing."""
import os
import tempfile

import adsk.core
import adsk.fusion

from . import bom_core as core

ATTR_GROUP = 'handbuiltcad'


def _attr(obj, name):
    a = obj.attributes.itemByName(ATTR_GROUP, name)
    return a.value if a else ''


def components_in_order(design):
    """[(component, count)] for every component used by an occurrence, in browser order."""
    names, comps = [], {}
    for occ in design.rootComponent.allOccurrences:
        c = occ.component
        comps.setdefault(c.id, c)
        names.append(c.id)
    counts = core.count_parts(names)
    return [(comps[cid], n) for cid, n in counts.items()]


def _fields(comp, root_mat):
    soft = []
    if (comp.partNumber or '') == comp.name:
        soft.append('part_number')
    if comp.material and comp.material.name == root_mat:
        soft.append('material')
    return {
        '_soft': soft,
        'id': comp.id,
        'name': comp.name,
        'part_number': comp.partNumber or '',
        'description': comp.description or '',
        'material': comp.material.name if comp.material else '',
        'vendor': _attr(comp, 'vendor'),
        'vendor_pn': _attr(comp, 'vendor_pn'),
        'notes': _attr(comp, 'notes'),
    }


def collect_tree(design):
    """Root's occurrences as nested dicts for bom_core.build_rows (read-only)."""
    root_mat = design.rootComponent.material.name if design.rootComponent.material else ''
    cache = {}

    def walk(occs):
        out = []
        for i in range(occs.count):
            occ = occs.item(i)
            c = occ.component
            if c.id not in cache:
                cache[c.id] = _fields(c, root_mat)
            node = dict(cache[c.id])
            node['children'] = walk(occ.childOccurrences)
            out.append(node)
        return out
    return walk(design.rootComponent.occurrences)


def collect_rows(design, style='parts'):
    return core.build_rows(collect_tree(design), style)


THUMB_DIR = os.path.join(tempfile.gettempdir(), 'HandbuiltCAD', 'hbbom_thumbs')


def _thumb_path(doc_name, comp_id):
    safe = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in comp_id)
    d = os.path.join(THUMB_DIR, ''.join(ch if ch.isalnum() else '_' for ch in doc_name))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, safe + '.png')


def make_thumbnails(app, design, rows, refresh=False, size=96):
    """{component id: png path} for top-level rows. Cached per document + component. To render, every other
    top-level occurrence is hidden briefly, the view is fitted and saved, then visibility and the camera are put
    back exactly as they were."""
    doc = app.activeDocument.name
    want = {r['id']: _thumb_path(doc, r['id']) for r in core.thumb_rows(rows)}
    todo = {i: p for i, p in want.items() if refresh or not os.path.isfile(p)}
    if todo:
        vp = app.activeViewport
        cam = vp.camera
        occs = design.rootComponent.occurrences
        saved = [(occs.item(i), occs.item(i).isLightBulbOn) for i in range(occs.count)]
        try:
            for cid, path in todo.items():
                for o, _ in saved:
                    on = o.component.id == cid
                    if o.isLightBulbOn != on:
                        o.isLightBulbOn = on
                vp.fit()
                vp.saveAsImageFile(path, size, size)
        finally:
            for o, was in saved:
                if o.isLightBulbOn != was:
                    o.isLightBulbOn = was
            vp.camera = cam
            vp.refresh()
    return {i: p for i, p in want.items() if os.path.isfile(p)}


def find_material(app, design, name):
    want = name.strip().lower()
    for i in range(design.materials.count):
        m = design.materials.item(i)
        if m.name.lower() == want:
            return m
    for li in range(app.materialLibraries.count):
        lib = app.materialLibraries.item(li)
        try:
            mats = lib.materials
        except Exception:
            continue
        for i in range(mats.count):
            m = mats.item(i)
            if m.name.lower() == want:
                return m
    return None


def apply_rows(design, rows):
    """Write edited rows back. Returns [(name, field, reason)] for anything that could not be written."""
    app = adsk.core.Application.get()
    by_id = {c.id: c for c, _ in components_in_order(design)}
    linked = {o.component.id for o in design.rootComponent.allOccurrences if o.isReferencedComponent}
    blocked = []
    for r in core.merge_edits(rows):
        comp = by_id.get(r.get('id'))
        if comp is None:
            blocked.append((r['name'], 'all', 'component not found'))
            continue
        if comp.id in linked:
            blocked.append((r['name'], 'all', 'linked (external) component - edit it in its own design'))
            continue
        for k, attr in (('part_number', 'partNumber'), ('description', 'description')):
            val = (r.get(k) or '').strip()
            if val and val != (getattr(comp, attr) or ''):
                try:
                    setattr(comp, attr, val)
                except Exception as e:
                    blocked.append((r['name'], k, str(e).splitlines()[0]))
        mat = (r.get('material') or '').strip()
        if mat and (not comp.material or comp.material.name != mat):
            m = find_material(app, design, mat)
            if m is None:
                blocked.append((r['name'], 'material', 'no material named "%s" in your libraries' % mat))
            else:
                try:
                    comp.material = m
                except Exception as e:
                    blocked.append((r['name'], 'material', str(e).splitlines()[0]))
        for k in core.ATTR_KEYS:
            val = (r.get(k) or '').strip()
            try:
                a = comp.attributes.itemByName(ATTR_GROUP, k)
                if val:
                    comp.attributes.add(ATTR_GROUP, k, val)
                elif a:
                    a.deleteMe()
            except Exception as e:
                blocked.append((r['name'], k, str(e).splitlines()[0]))
    return blocked
