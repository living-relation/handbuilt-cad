"""Tests for the pure (no adsk) parts of the Fusion add-ins in tools/fusion_addins."""
import csv
import io
import json
import os
import sys
import zipfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools', 'fusion_addins')
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'HBExport'))
sys.path.insert(0, os.path.join(ROOT, 'HBBom'))

import bom_core  # noqa: E402
import export_core  # noqa: E402
from hbcad_fusion_common import settings  # noqa: E402
from hbcad_fusion_common.names import safe_name  # noqa: E402


def test_safe_name_strips_version_and_bad_chars():
    assert safe_name('Filament Cabinet v12') == 'Filament Cabinet'
    assert safe_name('a/b:c*?') == 'a_b_c__'
    assert safe_name('  ') == 'export'


def test_target_paths_order_and_overwrite_names(tmp_path):
    p = export_core.target_paths(str(tmp_path), 'Part v3', ['dxf', 'step', 'stl'])
    assert list(p) == ['step', 'stl', 'dxf']
    assert p['step'].endswith('Part.step')
    assert export_core.target_paths(str(tmp_path), 'Part v4', ['step']) == {'step': p['step']}


def test_summarize_marks_failures():
    txt = export_core.summarize({'iges': (False, 'blocked'), 'step': (True, 'x.step')})
    assert txt.splitlines() == ['OK      STEP: x.step', 'FAILED  IGES: blocked']


def test_settings_roundtrip_ignores_unknown_and_bad(tmp_path):
    settings.save('export', {'folder': 'C:/x', 'junk': 1}, str(tmp_path))
    got = settings.load('export', export_core.DEFAULTS, str(tmp_path))
    assert got['folder'] == 'C:/x' and 'junk' not in got
    (tmp_path / 'bad.json').write_text('{oops')
    assert settings.load('bad', {'a': 1}, str(tmp_path)) == {'a': 1}


def test_count_parts():
    assert bom_core.count_parts(['a', 'b', 'a']) == {'a': 2, 'b': 1}


@pytest.mark.parametrize('data', [
    {'parts': [{'Name': 'Leg', 'PN': 'FC5-1', 'Material': 'Aluminum 6061', 'McMaster': '91290A'}]},
    [{'component': 'Leg', 'part_number': 'FC5-1', 'material': 'Aluminum 6061', 'vendor_pn': '91290A'}],
    {'Leg': {'pn': 'FC5-1', 'mat': 'Aluminum 6061', 'mcmaster_pn': '91290A'}},
])
def test_parse_build_json_shapes(data):
    t = bom_core.parse_build_json(data)
    assert t['leg']['part_number'] == 'FC5-1'
    assert t['fc5-1']['material'] == 'Aluminum 6061'
    assert t['leg']['vendor_pn'] == '91290A'


def test_fill_from_build_respects_overwrite():
    rows = [{'name': 'Leg', 'qty': 4, 'part_number': 'KEEP', 'description': ''},
            {'name': 'Other', 'qty': 1}]
    t = bom_core.parse_build_json({'Leg': {'pn': 'NEW', 'description': 'leg'}})
    got = bom_core.fill_from_build(rows, t)
    assert rows[0]['part_number'] == 'KEEP' and rows[0]['description'] == 'leg'
    assert got == [('Leg', 'description')]
    bom_core.fill_from_build(rows, t, overwrite=True)
    assert rows[0]['part_number'] == 'NEW'


def test_fill_replaces_fusion_defaults():
    rows = [{'name': 'Leg', 'part_number': 'Leg', 'material': 'Steel', '_soft': ['part_number', 'material']}]
    t = bom_core.parse_build_json({'Leg': {'pn': 'FC5-1', 'material': 'Aluminum 6061'}})
    assert sorted(f for _, f in bom_core.fill_from_build(rows, t)) == ['material', 'part_number']
    assert rows[0]['part_number'] == 'FC5-1' and rows[0]['_soft'] == []


def test_empty_and_report():
    rows = [{'name': 'Leg', 'qty': 2, 'part_number': 'P', 'description': '', 'material': 'Steel'}]
    assert bom_core.empty_cells(rows) == [('Leg', 'description')]
    rep = bom_core.report(rows, [('Leg', 'material', 'no material')], [])
    assert '2 pieces' in rep and 'Leg: material - no material' in rep and 'Leg: description' in rep


def test_csv_and_xlsx(tmp_path):
    rows = [{'name': 'A & <B>', 'qty': 3, 'part_number': 'P1'}]
    out = list(csv.reader(io.StringIO(bom_core.to_csv(rows))))
    assert out[0][0] == 'Component' and out[1][:3] == ['A & <B>', '3', 'P1']
    p = bom_core.write_xlsx(str(tmp_path / 'b.xlsx'), rows)
    with zipfile.ZipFile(p) as z:
        sheet = z.read('xl/worksheets/sheet1.xml').decode()
        assert 'A &amp; &lt;B&gt;' in sheet and '<v>3</v>' in sheet
        assert '[Content_Types].xml' in z.namelist()
    try:
        import openpyxl
    except ImportError:
        return
    ws = openpyxl.load_workbook(p).active
    assert ws['A2'].value == 'A & <B>' and ws['B2'].value == 3


def test_col_letters():
    assert [bom_core._col(i) for i in (0, 25, 26, 27)] == ['A', 'Z', 'AA', 'AB']


def test_manifests_valid():
    for name in ('HBExport', 'HBBom'):
        with open(os.path.join(ROOT, name, name + '.manifest'), encoding='utf-8') as f:
            m = json.load(f)
        assert m['type'] == 'addin' and m['autodeskProduct'] == 'Fusion'
