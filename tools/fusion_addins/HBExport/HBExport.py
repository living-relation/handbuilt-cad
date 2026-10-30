"""HB Export: one toolbar button, a checkbox per file type, a remembered folder. Files overwrite in place."""
import os
import sys
import traceback

import adsk.core
import adsk.fusion

_HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(_HERE))
from hbcad_fusion_common import settings  # noqa: E402
from . import export_core as core  # noqa: E402
from . import export_ops as ops  # noqa: E402

CMD_ID = 'hbcadExportCmd'
PANEL_IDS = ['SolidScriptsAddinsPanel', 'SolidMakePanel']
SETTINGS = 'export'
_handlers = []


def _ui():
    return adsk.core.Application.get().userInterface


class _Created(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            cmd = args.command
            cmd.setDialogInitialSize(420, 420)
            inputs = cmd.commandInputs
            s = settings.load(SETTINGS, core.DEFAULTS)
            base = s.get('base_name') or (app.activeDocument.name if app.activeDocument else 'export')
            inputs.addStringValueInput('base', 'File name', core.safe_name(base))
            inputs.addStringValueInput('folder', 'Folder', s.get('folder') or os.path.expanduser('~'))
            inputs.addBoolValueInput('browse', 'Choose folder...', False, '', False)
            grp = inputs.addGroupCommandInput('types', 'File types').children
            for k, label, _ in core.FORMATS:
                grp.addBoolValueInput('t_' + k, label, True, '', k in s.get('checked', []))
            sel = inputs.addSelectionInput('target', 'Component (optional)', 'Leave empty to export the whole design')
            sel.addSelectionFilter('Occurrences')
            sel.setSelectionLimits(0, 1)
            dsel = inputs.addSelectionInput('dxfsrc', 'DXF source', 'A sketch or a flat face (only for DXF)')
            dsel.addSelectionFilter('Sketches')
            dsel.addSelectionFilter('PlanarFaces')
            dsel.setSelectionLimits(0, 1)
            inputs.addTextBoxCommandInput('note', '', 'IGES and SAT may be blocked on non-commercial Fusion plans; '
                                          'the result list says so if they are.', 2, True)
            for h, ev in ((_Changed(), cmd.inputChanged), (_Execute(), cmd.execute)):
                ev.add(h)
                _handlers.append(h)
            if design is None:
                _ui().messageBox('Open a design first.')
        except Exception:
            _ui().messageBox('HB Export failed to open:\n' + traceback.format_exc())


class _Changed(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            if args.input.id != 'browse':
                return
            inputs = args.inputs
            dlg = _ui().createFolderDialog()
            dlg.title = 'Export folder'
            cur = inputs.itemById('folder').value
            if cur and os.path.isdir(cur):
                dlg.initialDirectory = cur
            if dlg.showDialog() == adsk.core.DialogResults.DialogOK:
                inputs.itemById('folder').value = dlg.folder
            args.input.value = False
        except Exception:
            _ui().messageBox(traceback.format_exc())


class _Execute(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            app = adsk.core.Application.get()
            design = adsk.fusion.Design.cast(app.activeProduct)
            inputs = args.command.commandInputs
            folder = inputs.itemById('folder').value.strip()
            base = inputs.itemById('base').value
            keys = [k for k in core.FORMAT_KEYS if inputs.itemById('t_' + k).value]
            if not folder:
                _ui().messageBox('Pick a folder first.')
                return
            occ = comp = None
            t = inputs.itemById('target')
            if t.selectionCount:
                occ = adsk.fusion.Occurrence.cast(t.selection(0).entity)
                comp = occ.component
            d = inputs.itemById('dxfsrc')
            dxf_ent = d.selection(0).entity if d.selectionCount else None
            res = ops.export(design, keys, folder, base, comp, occ, dxf_ent)
            settings.save(SETTINGS, {'folder': folder, 'checked': keys, 'base_name': ''})
            _ui().messageBox(core.summarize(res), 'HB Export')
        except Exception:
            _ui().messageBox('HB Export failed:\n' + traceback.format_exc())


def run(context):
    try:
        ui = _ui()
        _remove_ui(ui)  # old buttons first: a button left behind points at a deleted command and does nothing
        cd = ui.commandDefinitions.addButtonDefinition(CMD_ID, 'HB Export', 'Export checked file types to one folder',
                                                       '')
        h = _Created()
        cd.commandCreated.add(h)
        _handlers.append(h)
        for pid in PANEL_IDS:
            panel = ui.allToolbarPanels.itemById(pid)
            if panel:
                ctl = panel.controls.addCommand(cd)
                ctl.isPromoted = pid == 'SolidScriptsAddinsPanel'
    except Exception:
        _ui().messageBox('HB Export run failed:\n' + traceback.format_exc())


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
