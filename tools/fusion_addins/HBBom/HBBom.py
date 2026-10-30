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
_state = {'rows': [], 'filled': []}


def _ui():
    return adsk.core.Application.get().userInterface


def _cell(table, r, k):
    return table.commandInputs.itemById('c_%d_%s' % (r, k))


def _build_table(inputs, rows):
    table = inputs.addTableCommandInput('bom', 'BOM', len(core.COLUMNS), '3:1:3:4:3:2:3:3')
    table.maximumVisibleRows = 15
    ci = table.commandInputs
    for c, (_, head) in enumerate(core.COLUMNS):
        table.addCommandInput(ci.addTextBoxCommandInput('h_%d' % c, '', '<b>%s</b>' % head, 1, True), 0, c)
    for r, row in enumerate(rows):
        for c, k in enumerate(core.KEYS):
            iid = 'c_%d_%s' % (r, k)
            if k in core.EDITABLE:
                inp = ci.addStringValueInput(iid, '', str(row.get(k, '')))
            else:
                inp = ci.addTextBoxCommandInput(iid, '', str(row.get(k, '')), 1, True)
            table.addCommandInput(inp, r + 1, c)
    return table


def _read_table(inputs):
    table = inputs.itemById('bom')
    for r, row in enumerate(_state['rows']):
        for k in core.EDITABLE:
            row[k] = _cell(table, r, k).value.strip()
    return _state['rows']


def _write_table(inputs):
    table = inputs.itemById('bom')
    for r, row in enumerate(_state['rows']):
        for k in core.EDITABLE:
            _cell(table, r, k).value = row.get(k, '')


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
            _state['rows'] = ops.collect_rows(design)
            _state['filled'] = []
            pieces = sum(r['qty'] for r in _state['rows'])
            inputs.addTextBoxCommandInput('count', 'Part count',
                                          '%d unique parts, %d pieces' % (len(_state['rows']), pieces), 1, True)
            _build_table(inputs, _state['rows'])
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
            if inp.id == 'browse' and inp.value:
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
            rows = ops.collect_rows(design)  # re-read what Fusion actually holds
            for r, old in zip(rows, _state['rows']):  # keep typed text for fields Fusion refused
                for k in core.EDITABLE:
                    r[k] = r[k] or old.get(k, '')
            out = run_exports(folder, app.activeDocument.name, rows, blocked, _state['filled'],
                              inputs.itemById('csv').value, inputs.itemById('xlsx').value)
            settings.save(SETTINGS, {'folder': folder, 'build_json': inputs.itemById('bjson').value.strip()})
            emp = core.empty_cells(rows)
            _ui().messageBox('Written: %s\nBlocked: %d   Still empty: %d\nDetails in the report file.'
                             % (', '.join(os.path.basename(p) for p in out), len(blocked), len(emp)), 'HB BOM')
        except Exception:
            _ui().messageBox('HB BOM failed:\n' + traceback.format_exc())


def run_exports(folder, doc_name, rows, blocked, filled, csv=True, xlsx=True):
    os.makedirs(folder, exist_ok=True)
    base = os.path.join(folder, safe_name(doc_name) + '_BOM')
    out = []
    if csv:
        with open(base + '.csv', 'w', encoding='utf-8-sig', newline='') as f:
            f.write(core.to_csv(rows))
        out.append(base + '.csv')
    if xlsx:
        out.append(core.write_xlsx(base + '.xlsx', rows))
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
                ctl.isPromoted = pid == 'SolidScriptsAddinsPanel'
                ctl.isPromotedByDefault = ctl.isPromoted
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
