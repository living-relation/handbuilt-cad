"""Pure BOM helpers for the HB BOM add-in (no adsk import, unit-tested in tests/test_fusion_addins.py)."""
import csv
import io
import json
import zipfile
from xml.sax.saxutils import escape

# Column key, header, in BOM order. Item is auto-numbered (1, 2 / 1.1, 1.2) and never editable.
# Fusion-writable: part_number, description, material (component); vendor/vendor_pn/notes are stored as
# attributes (group 'handbuiltcad') because Fusion custom properties need a Pro/commercial plan.
COLUMNS = [
    ('item', 'Item'),
    ('qty', 'QTY'),
    ('part_number', 'Part Number'),
    ('description', 'Part Description'),
    ('name', 'Component'),
    ('material', 'Material'),
    ('vendor', 'Vendor'),
    ('vendor_pn', 'Vendor part number'),
    ('notes', 'Notes'),
]
KEYS = [k for k, _ in COLUMNS]
HEADERS = dict(COLUMNS)
EDITABLE = ['part_number', 'description', 'material', 'vendor', 'vendor_pn', 'notes']
ATTR_KEYS = ['vendor', 'vendor_pn', 'notes']
REQUIRED = ['part_number', 'description', 'material']
DEFAULT_COLUMNS = ['item', 'qty', 'part_number', 'description', 'name', 'material']
STYLES = [('top', 'Top level'), ('indented', 'Indented (layered)'), ('parts', 'Parts only')]
DEFAULTS = {'folder': '', 'build_json': '', 'style': 'top', 'columns': DEFAULT_COLUMNS, 'thumbs': False}
NODE_FIELDS = ['id', 'name', 'part_number', 'description', 'material', 'vendor', 'vendor_pn', 'notes', '_soft']


def pick_columns(selected):
    """Selected column keys in BOM order (unknown keys dropped; never empty)."""
    sel = set(selected or [])
    out = [k for k in KEYS if k in sel]
    return out or list(DEFAULT_COLUMNS)


def _group(nodes):
    """[(first node, count)] grouping sibling occurrences by component id, first-seen order."""
    order, first, count = [], {}, {}
    for n in nodes:
        i = n['id']
        if i not in first:
            order.append(i)
            first[i] = n
            count[i] = 0
        count[i] += 1
    return [(first[i], count[i]) for i in order]


def _row(node, qty, item, level):
    r = {k: (list(node[k]) if k == '_soft' else node[k]) for k in NODE_FIELDS if k in node}
    r.update(item=item, qty=qty, level=level, top=level == 0, has_children=bool(node.get('children')))
    r['_orig'] = {k: r.get(k, '') for k in EDITABLE}
    return r


def build_rows(tree, style='top'):
    """tree: root's occurrences as nested dicts (NODE_FIELDS + 'children'). Styles:
    top = root's direct children only, qty per assembly; indented = every level, item 1, 1.1, 1.1.1,
    qty per one parent; parts = leaf parts only, total qty across the whole assembly."""
    rows = []
    if style == 'parts':
        totals, first, order = {}, {}, []

        def walk(nodes, mult):
            for n, c in _group(nodes):
                if n.get('children'):
                    walk(n['children'], mult * c)
                else:
                    if n['id'] not in first:
                        first[n['id']] = n
                        order.append(n['id'])
                        totals[n['id']] = 0
                    totals[n['id']] += mult * c
        walk(tree, 1)
        return [_row(first[i], totals[i], str(k), 0) for k, i in enumerate(order, 1)]

    def add(nodes, prefix, level):
        for k, (n, c) in enumerate(_group(nodes), 1):
            item = prefix + str(k)
            rows.append(_row(n, c, item, level))
            if style == 'indented' and n.get('children'):
                add(n['children'], item + '.', level + 1)
    add(tree, '', 0)
    return rows


def merge_edits(rows):
    """One row per component id with the edited values (a component can show on several indented rows;
    a cell that differs from its original value wins)."""
    out, order = {}, []
    for r in rows:
        i = r.get('id')
        if i not in out:
            order.append(i)
            out[i] = dict(r)
            out[i].update(r.get('_orig') or {})
        for k in EDITABLE:
            if r.get(k, '') != (r.get('_orig') or {}).get(k, ''):
                out[i][k] = r.get(k, '')
    return [out[i] for i in order]


def spread_edits(rows, merged):
    """Copy merged values back onto every row of the same component."""
    by = {m.get('id'): m for m in merged}
    for r in rows:
        m = by.get(r.get('id'))
        if m:
            for k in EDITABLE:
                r[k] = m.get(k, '')
    return rows


def thumb_rows(rows):
    """Rows that get a thumbnail: top-level items only, never children of an expanded subassembly."""
    return [r for r in rows if r.get('top')]


def cell(row, key):
    v = row.get(key, '')
    return v if v is not None else ''


_ALIASES = {
    'name': ['name', 'component', 'part', 'part_name'],
    'part_number': ['part_number', 'pn', 'partnumber', 'part_no', 'number'],
    'description': ['description', 'desc', 'title'],
    'material': ['material', 'mat'],
    'vendor': ['vendor', 'supplier', 'source'],
    'vendor_pn': ['vendor_pn', 'vendor_part_number', 'mcmaster', 'mcmaster_pn', 'supplier_pn'],
    'notes': ['notes', 'note', 'comment'],
    'qty': ['qty', 'quantity', 'count'],
}


def count_parts(component_names):
    """Ordered {component name: count} from the list of every occurrence's component name."""
    counts = {}
    for n in component_names:
        counts[n] = counts.get(n, 0) + 1
    return counts


def _norm(rec):
    low = {str(k).strip().lower(): v for k, v in rec.items()}
    out = {}
    for key, names in _ALIASES.items():
        for n in names:
            if n in low and low[n] not in (None, ''):
                out[key] = str(low[n])
                break
    return out


def parse_build_json(data):
    """Accepts {"parts": [...]}, {"bom": [...]}, a plain list, or {name: {fields}}.
    Returns {lookup key: fields}; each part is reachable by name and by part number (lowercase)."""
    if isinstance(data, dict):
        for k in ('parts', 'bom', 'components', 'items'):
            if isinstance(data.get(k), (list, dict)):
                data = data[k]
                break
    recs = []
    if isinstance(data, list):
        recs = [_norm(r) for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        for name, v in data.items():
            if isinstance(v, dict):
                r = _norm(v)
                r.setdefault('name', str(name))
                recs.append(r)
    table = {}
    for r in recs:
        for key in (r.get('name'), r.get('part_number')):
            if key:
                table.setdefault(key.strip().lower(), r)
    return table


def load_build_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return parse_build_json(json.load(f))


def fill_from_build(rows, table, overwrite=False):
    """Fill empty cells from build.json. Returns list of (row name, field) filled."""
    filled = []
    for row in rows:
        src = table.get(row['name'].strip().lower()) or table.get((row.get('part_number') or '').strip().lower())
        if not src:
            continue
        for k in EDITABLE:
            soft = k in row.get('_soft', ())  # Fusion's own default (part number = name, default material)
            if src.get(k) and (overwrite or soft or not row.get(k)):
                if row.get(k) != src[k]:
                    row[k] = src[k]
                    filled.append((row['name'], k))
                if soft:
                    row['_soft'] = [f for f in row['_soft'] if f != k]
    return filled


def empty_cells(rows, required=REQUIRED):
    return [(r['name'], k) for r in rows for k in required if not str(r.get(k) or '').strip()]


def to_csv(rows, columns=None):
    cols = pick_columns(columns or KEYS)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow([HEADERS[k] for k in cols])
    for r in rows:
        w.writerow([cell(r, k) for k in cols])
    return buf.getvalue()


def _col(i):
    s = ''
    i += 1
    while i:
        i, rem = divmod(i - 1, 26)
        s = chr(65 + rem) + s
    return s


def write_xlsx(path, rows, sheet='BOM', columns=None):
    """Minimal standard .xlsx (stdlib only; Fusion's Python has no openpyxl). Item is written as text."""
    cols = pick_columns(columns or KEYS)
    table = [[HEADERS[k] for k in cols]] + [[cell(r, k) for k in cols] for r in rows]
    xml_rows = []
    for ri, vals in enumerate(table, 1):
        cells = []
        for ci, v in enumerate(vals):
            ref = _col(ci) + str(ri)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cells.append('<c r="%s"><v>%s</v></c>' % (ref, v))
            else:
                cells.append('<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                             % (ref, escape(str(v))))
        xml_rows.append('<row r="%d">%s</row>' % (ri, ''.join(cells)))
    ns = 'http://schemas.openxmlformats.org/'
    files = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="%spackage/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>' % ns,
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="%spackage/2006/relationships"><Relationship Id="rId1" Type="%sofficeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>' % (ns, ns),
        'xl/workbook.xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="%sspreadsheetml/2006/main" xmlns:r="%sofficeDocument/2006/relationships"><sheets><sheet name="%s" sheetId="1" r:id="rId1"/></sheets></workbook>' % (ns, ns, escape(sheet)),
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="%spackage/2006/relationships"><Relationship Id="rId1" Type="%sofficeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>' % (ns, ns),
        'xl/worksheets/sheet1.xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="%sspreadsheetml/2006/main"><sheetData>%s</sheetData></worksheet>' % (ns, ''.join(xml_rows)),
    }
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, body in files.items():
            z.writestr(n, body)
    return path


def report(rows, blocked, filled):
    """blocked: list of (row name, field, reason)."""
    lines = ['HB BOM report', '', 'Parts: %d rows, %d pieces' % (len(rows), sum(int(r.get('qty') or 0) for r in rows))]
    rows = merge_edits(rows) if any('id' in r for r in rows) else rows
    if filled:
        lines += ['', 'Filled from build.json (%d):' % len(filled)] + ['  %s: %s' % f for f in filled]
    lines += ['', 'Blocked (%d):' % len(blocked)] + ['  %s: %s - %s' % b for b in blocked]
    emp = empty_cells(rows)
    lines += ['', 'Still empty (%d):' % len(emp)] + ['  %s: %s' % e for e in emp]
    return '\n'.join(lines) + '\n'
