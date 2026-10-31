"""HB BOM: count parts, fill fields from build.json or by hand, write them back, export CSV/Excel + a report."""
import os
import sys
import traceback

import adsk.core
import adsk.fusion

_HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(_HERE))
from hbcad_fusion_common import settings  # noqa: E402
from hbcad_fusion_common.names import safe_name  # noqa: E402
from . import bom_core as core  # noqa: E402
from . import bom_ops as ops  # noqa: E402

CMD_ID = 'hbcadBomCmd'
PANEL_IDS = ['SolidScriptsAddinsPanel', 'SolidMakePanel']
SETTINGS = 'bom'
_handlers = []
_state = {'rows': [], 'filled': [], 'tree': [], 'gen': 0}


def _ui():
    return adsk.core.Application.get().userInterface


def _cell(table, r, k):
    return table.commandInputs.itemById('c%d_%d_%s' % (_state['gen'], r, k))


def _columns(inputs):
    return core.pick_columns([k for k in core.KEYS if inputs.itemById('col_' + k).value])


def _style(inputs):
    name = inputs.itemById('style').selectedItem.name
    return next(k for k, n in core.STYLES if n == name)


def _build_table(inputs, rows, cols, thumbs=None):
    """(Re)build the BOM grid. thumbs: {component id: png} shown on top-level rows only (dialog only)."""
    _state['gen'] += 1
    g = _state['gen']
    old = inputs.itemById('bom')
    if old:
        old.deleteMe()
    show = (['thumb'] if thumbs is not None else []) + cols
    widths = {'thumb': 2, 'item': 1, 'qty': 1, 'part_number': 3, 'description': 4, 'name': 3, 'material': 3,
              'vendor': 2, 'vendor_pn': 3, 'notes': 3}
    table = inputs.addTableCommandInput('bom', 'BOM', len(show), ':'.join(str(widths[k]) for k in show))
    table.maximumVisibleRows = 15
    ci = table.commandInputs
    for c, k in enumerate(show):
        head = '' if k == 'thumb' else core.HEADERS[k]
        table.addCommandInput(ci.addTextBoxCommandInput('h%d_%d' % (g, c), '', '<b>%s</b>' % head, 1, True), 0, c)
    for r, row in enumerate(rows):
        for c, k in enumerate(show):
            iid = 'c%d_%d_%s' % (g, r, k)
            if k == 'thumb':
                path = (thumbs or {}).get(row['id']) if row.get('top') else None
                inp = ci.addImageCommandInput(iid, '', path) if path else ci.addTextBoxCommandInput(iid, '', '', 1, True)
            elif k in core.EDITABLE:
                inp = ci.addStringValueInput(iid, '', str(row.get(k, '')))
            else:
                val = str(row.get(k, ''))
                if k == 'name' and row.get('level'):
                    val = '&nbsp;' * 4 * row['level'] + val
                inp = ci.addTextBoxCommandInput(iid, '', val, 1, True)
            table.addCommandInput(inp, r + 1, c)
    return table


def _read_table(inputs):
    table = inputs.itemById('bom')
    for r, row in enumerate(_state['rows']):
        for k in core.EDITABLE:
            c = _cell(table, r, k)
            if c:
                row[k] = c.value.strip()
    return _state['rows']


def _write_table(inputs):
    table = inputs.itemById('bom')
    for r, row in enumerate(_state['rows']):
        for k in core.EDITABLE:
            c = _cell(table, r, k)
            if c:
                c.value = row.get(k, '')


def _refresh(inputs, new_rows=False, refresh_thumbs=False):
    """Rebuild rows for the chosen style (keeping typed edits) and redraw the grid."""
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if new_rows:
        merged = core.merge_edits(_read_table(inputs))
        _state['rows'] = core.spread_edits(core.build_rows(_state['tree'], _style(inputs)), merged)
        for r in _state['rows']:
            m = next((x for x in merged if x.get('id') == r['id']), None)
            if m:
                r['_orig'] = dict(m['_orig'])
    thumbs = None
    if inputs.itemById('thumbs').value:
        try:
            thumbs = ops.make_thumbnails(app, design, _state['rows'], refresh_thumbs)
        except Exception as e:
            thumbs = {}
            _ui().messageBox('Thumbnails failed: %s' % e, 'HB BOM')
    rows = _state['rows']
    pieces = sum(r['qty'] for r in rows if r.get('top'))
    inputs.itemById('count').formattedText = '%d rows, %d top-level pieces' % (len(rows), pieces)
    _build_table(inputs, rows, _columns(inputs), thumbs)


class _Created(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            if design is None:
                _ui().messageBox('Open a design first.')
                return
            cmd = args.command
            cmd.setDialogInitialSize(900, 600)
            cmd.okButtonText = 'Apply + export'
            inputs = cmd.commandInputs
            s = settings.load(SETTINGS, core.DEFAULTS)
            inputs.addStringValueInput('folder', 'Output folder', s.get('folder') or os.path.expanduser('~'))
            inputs.addBoolValueInput('browse', 'Choose folder...', False, '', False)
            inputs.addStringValueInput('bjson', 'build.json', s.get('build_json') or '')
            inputs.addBoolValueInput('fill', 'Fill from build.json...', False, '', False)
            inputs.addBoolValueInput('overwrite', 'build.json overwrites filled cells', True, '', False)
            inputs.addBoolValueInput('csv', 'Export CSV', True, '', True)
            inputs.addBoolValueInput('xlsx', 'Export Excel (.xlsx)', True, '', True)
            dd = inputs.addDropDownCommandInput('style', 'BOM style', adsk.core.DropDownStyles.TextListDropDownStyle)
            for k, n in core.STYLES:
                dd.listItems.add(n, k == s.get('style', 'top'))
            cols = core.pick_columns(s.get('columns'))
            grp = inputs.addGroupCommandInput('cols', 'Columns')
            grp.isExpanded = False
            for k, head in core.COLUMNS:
                grp.children.addBoolValueInput('col_' + k, head, True, '', k in cols)
            inputs.addBoolValueInput('thumbs', 'Thumbnails (top-level items, dialog only)', True, '',
                                     bool(s.get('thumbs')))
            inputs.addBoolValueInput('rethumb', 'Redo thumbnails', False, '', False)
            _state['tree'] = ops.collect_tree(design)
            _state['rows'] = core.build_rows(_state['tree'], _style(inputs))
            _state['filled'] = []
            inputs.addTextBoxCommandInput('count', 'Part count', '', 1, True)
            _refresh(inputs)
            inputs.addTextBoxCommandInput('note', '', 'Part number, description and material are written to the '
                                          'components. Vendor, vendor part number and notes are saved as attributes '
                                          '(custom properties need a commercial Fusion plan).', 2, True)
            for h, ev in ((_Changed(), cmd.inputChanged), (_Execute(), cmd.execute)):
                ev.add(h)
                _handlers.append(h)
        except Exception:
            _ui().messageBox('HB BOM failed to open:\n' + traceback.format_exc())


class _Changed(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            inp, inputs = args.input, args.inputs
            if inp.id == 'style' or inp.id.startswith('col_') or inp.id == 'thumbs':
                _read_table(inputs)
                _refresh(inputs, new_rows=inp.id == 'style')
            elif inp.id == 'rethumb' and inp.value:
                inp.value = False
                _read_table(inputs)
                if inputs.itemById('thumbs').value:
                    _refresh(inputs, refresh_thumbs=True)
            elif inp.id == 'browse' and inp.value:
                inp.value = False
                dlg = _ui().createFolderDialog()
                dlg.title = 'BOM output folder'
                if dlg.showDialog() == adsk.core.DialogResults.DialogOK:
                    inputs.itemById('folder').value = dlg.folder
            elif inp.id == 'fill' and inp.value:
                inp.value = False
                path = inputs.itemById('bjson').value.strip()
                if not os.path.isfile(path):
                    dlg = _ui().createFileDialog()
                    dlg.title = 'Pick build.json'
                    dlg.filter = 'JSON (*.json)'
                    if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
                        return
                    path = dlg.filename
                    inputs.itemById('bjson').value = path
                _read_table(inputs)
                table = core.load_build_json(path)
                got = core.fill_from_build(_state['rows'], table, inputs.itemById('overwrite').value)
                _state['filled'] += got
                _write_table(inputs)
                _ui().messageBox('Filled %d cells from build.json.' % len(got), 'HB BOM')
        except Exception:
            _ui().messageBox(traceback.format_exc())


class _Execute(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            inputs = args.command.commandInputs
            folder = inputs.itemById('folder').value.strip()
            rows = _read_table(inputs)
            blocked = ops.apply_rows(design, rows)
            style, cols = _style(inputs), _columns(inputs)
            typed = core.merge_edits(rows)
            rows = ops.collect_rows(design, style)  # re-read what Fusion actually holds
            for r in rows:  # keep typed text for fields Fusion refused
                old = next((t for t in typed if t.get('id') == r['id']), {})
                for k in core.EDITABLE:
                    r[k] = r[k] or old.get(k, '')
            out = run_exports(folder, app.activeDocument.name, rows, blocked, _state['filled'],
                              inputs.itemById('csv').value, inputs.itemById('xlsx').value, cols)
            settings.save(SETTINGS, {'folder': folder, 'build_json': inputs.itemById('bjson').value.strip(),
                                     'style': style, 'columns': cols, 'thumbs': inputs.itemById('thumbs').value})
            emp = core.empty_cells(rows)
            _ui().messageBox('Written: %s\nBlocked: %d   Still empty: %d\nDetails in the report file.'
                             % (', '.join(os.path.basename(p) for p in out), len(blocked), len(emp)), 'HB BOM')
        except Exception:
            _ui().messageBox('HB BOM failed:\n' + traceback.format_exc())


def run_exports(folder, doc_name, rows, blocked, filled, csv=True, xlsx=True, columns=None):
    os.makedirs(folder, exist_ok=True)
    base = os.path.join(folder, safe_name(doc_name) + '_BOM')
    out = []
    if csv:
        with open(base + '.csv', 'w', encoding='utf-8-sig', newline='') as f:
            f.write(core.to_csv(rows, columns))
        out.append(base + '.csv')
    if xlsx:
        out.append(core.write_xlsx(base + '.xlsx', rows, columns=columns))
    with open(base + '_report.txt', 'w', encoding='utf-8') as f:
        f.write(core.report(rows, blocked, filled))
    out.append(base + '_report.txt')
    return out


def run(context):
    try:
        ui = _ui()
        _remove_ui(ui)  # old buttons first: a button left behind points at a deleted command and does nothing
        cd = ui.commandDefinitions.addButtonDefinition(CMD_ID, 'HB BOM', 'Count parts, fill properties, export BOM',
                                                       os.path.join(_HERE, 'resources', 'icon'))
        h = _Created()
        cd.commandCreated.add(h)
        _handlers.append(h)
        for pid in PANEL_IDS:
            panel = ui.allToolbarPanels.itemById(pid)
            if panel:
                ctl = panel.controls.addCommand(cd)
                # Default pin only, set once on the new control; never isPromoted, so Fusion keeps the
                # user's own pin/unpin choice across restarts.
                ctl.isPromotedByDefault = pid == 'SolidScriptsAddinsPanel'
    except Exception:
        _ui().messageBox('HB BOM run failed:\n' + traceback.format_exc())


def _remove_ui(ui):
    for pid in PANEL_IDS:
        panel = ui.allToolbarPanels.itemById(pid)
        ctl = panel.controls.itemById(CMD_ID) if panel else None
        while ctl:
            ctl.deleteMe()
            ctl = panel.controls.itemById(CMD_ID)
    cd = ui.commandDefinitions.itemById(CMD_ID)
    if cd:
        cd.deleteMe()


def stop(context):
    try:
        _remove_ui(_ui())
        _handlers.clear()
    except Exception:
        pass
