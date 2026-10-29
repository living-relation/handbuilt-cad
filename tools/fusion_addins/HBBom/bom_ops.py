"""Fusion-side BOM work: read components, count them, write fields back. Separate from the UI for testing."""
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


def collect_rows(design):
    rows = []
    root_mat = design.rootComponent.material.name if design.rootComponent.material else ''
    for comp, n in components_in_order(design):
        soft = []
        if (comp.partNumber or '') == comp.name:
            soft.append('part_number')
        if comp.material and comp.material.name == root_mat:
            soft.append('material')
        rows.append({
            '_soft': soft,
            'id': comp.id,
            'name': comp.name,
            'qty': n,
            'part_number': comp.partNumber or '',
            'description': comp.description or '',
            'material': comp.material.name if comp.material else '',
            'vendor': _attr(comp, 'vendor'),
            'vendor_pn': _attr(comp, 'vendor_pn'),
            'notes': _attr(comp, 'notes'),
        })
    return rows


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
    for r in rows:
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
