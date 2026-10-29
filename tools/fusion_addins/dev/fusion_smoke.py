"""In-Fusion smoke test for HB Export and HB BOM. Run from Fusion (Scripts and Add-Ins > run this file as a
script, or the AutodeskFusionMCP execute_python tool). Works only in a NEW scratch document that it closes
WITHOUT saving; your open documents are not touched. Output goes to %TEMP%/hbcad_fusion_smoke."""
import importlib
import json
import os
import sys
import tempfile

import adsk.core
import adsk.fusion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in globals() else os.environ['HBCAD_ADDINS']


def main():
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    for m in [m for m in sys.modules if m.split('.')[0] in ('HBExport', 'HBBom', 'hbcad_fusion_common')]:
        del sys.modules[m]
    eops = importlib.import_module('HBExport.export_ops')
    bops = importlib.import_module('HBBom.bom_ops')
    bcore = importlib.import_module('HBBom.bom_core')
    bmain = importlib.import_module('HBBom.HBBom')
    emain = importlib.import_module('HBExport.HBExport')
    app = adsk.core.Application.get()
    out_dir = os.path.join(tempfile.gettempdir(), 'hbcad_fusion_smoke')
    os.makedirs(out_dir, exist_ok=True)
    res = {}
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    try:
        des = adsk.fusion.Design.cast(app.activeProduct)
        root = des.rootComponent
        for i, (w, h) in enumerate(((2, 1), (1, 1))):
            sk = root.sketches.add(root.xYConstructionPlane)
            sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(i * 5, 0, 0),
                                                              adsk.core.Point3D.create(i * 5 + w, h, 0))
            root.features.extrudeFeatures.addSimple(sk.profiles.item(0), adsk.core.ValueInput.createByReal(1),
                                                    adsk.fusion.FeatureOperations.NewComponentFeatureOperation)
        root.occurrences.item(0).component.name = 'Plate'
        root.occurrences.item(1).component.name = 'Block'
        root.occurrences.addExistingComponent(root.occurrences.item(1).component, adsk.core.Matrix3D.create())
        occ = root.occurrences.item(0)
        body = occ.component.bRepBodies.item(0)
        face = max([body.faces.item(i) for i in range(body.faces.count)], key=lambda f: f.area)
        r1 = eops.export(des, ['step', 'f3d', 'stl', '3mf', 'iges', 'sat', 'dxf'], out_dir, 'smoke v2',
                         dxf_entity=face)
        r2 = eops.export(des, ['step', 'stl'], out_dir, 'smoke_occ', occ.component, occ)  # one component
        r3 = eops.export(des, ['step'], out_dir, 'smoke v3')  # same name again: overwrite in place
        res['export_all'] = {k: v[0] for k, v in r1.items()}
        res['export_errors'] = {k: v[1] for k, v in r1.items() if not v[0]}
        res['export_component'] = {k: v[0] for k, v in r2.items()}
        res['overwrite_same_path'] = r3['step'][1] == r1['step'][1] and r3['step'][0]
        rows = bops.collect_rows(des)
        res['counts'] = {r['name']: r['qty'] for r in rows}
        table = bcore.parse_build_json({'parts': [{'name': 'Plate', 'pn': 'SM-001', 'description': 'plate',
                                                   'material': 'Aluminum 6061', 'vendor': 'shop'},
                                                  {'name': 'Block', 'pn': 'SM-002', 'material': 'NoSuchMat'}]})
        res['filled'] = bcore.fill_from_build(rows, table)
        blocked = bops.apply_rows(des, rows)
        res['blocked'] = blocked
        back = {r['name']: r for r in bops.collect_rows(des)}
        res['written_plate'] = {k: back['Plate'][k] for k in ('part_number', 'description', 'material', 'vendor')}
        res['written_block_pn'] = back['Block']['part_number']
        files = bmain.run_exports(out_dir, 'smoke v2', list(back.values()), blocked, res['filled'])
        res['bom_files'] = [os.path.basename(f) for f in files]
        # add-in registration: start, check the buttons exist, stop (removes them again)
        ui = app.userInterface
        emain.run(None)
        bmain.run(None)
        res['buttons_registered'] = [bool(ui.commandDefinitions.itemById(i)) for i in (emain.CMD_ID, bmain.CMD_ID)]
        emain.stop(None)
        bmain.stop(None)
        res['buttons_removed'] = [not ui.commandDefinitions.itemById(i) for i in (emain.CMD_ID, bmain.CMD_ID)]
    finally:
        doc.close(False)
    res['files'] = sorted(os.listdir(out_dir))
    print(json.dumps(res, indent=1, default=str))
    return res


def run(context):
    try:
        res = main()
        adsk.core.Application.get().userInterface.messageBox(json.dumps(res, indent=1, default=str)[:3000])
    except Exception:
        import traceback
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


if __name__ == '__main__' and 'HBCAD_ADDINS' in os.environ:
    main()
